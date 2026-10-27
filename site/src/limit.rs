//! Per-client rate limiting: page views stay well under the limit, but walking the
//! whole dataset endpoint by endpoint takes hours rather than minutes.
//!
//! Limits are per instance (in memory), so with N instances a client could get up to
//! N times the rate. Cloud Run's max-instances keeps N small.

use std::net::{IpAddr, SocketAddr};
use std::sync::Arc;
use std::time::Duration;

use axum::Router;
use axum::extract::ConnectInfo;
use axum::http::Request;
use tower_governor::GovernorLayer;
use tower_governor::errors::GovernorError;
use tower_governor::governor::GovernorConfigBuilder;
use tower_governor::key_extractor::KeyExtractor;

pub struct RateLimit {
    /// One request is restored every `replenish`.
    pub replenish: Duration,
    /// Requests a client can make at once before waiting.
    pub burst: u32,
    /// Proxies that append to X-Forwarded-For after the client's own address (see [`ClientIp`]).
    pub trusted_hops: usize,
}

impl RateLimit {
    /// 5 requests a second sustained, bursts of 50 (a Game Report page plus a few
    /// shifts of rink playback).
    pub fn from_env() -> Self {
        let hops = std::env::var("TRUSTED_PROXY_HOPS")
            .ok()
            .and_then(|v| v.parse().ok());
        Self {
            replenish: Duration::from_millis(200),
            burst: 50,
            trusted_hops: hops.unwrap_or(0),
        }
    }

    pub fn apply(&self, router: Router) -> Router {
        let config = GovernorConfigBuilder::default()
            .period(self.replenish)
            .burst_size(self.burst)
            .key_extractor(ClientIp {
                trusted_hops: self.trusted_hops,
            })
            .finish()
            .expect("non-zero period and burst");
        let config = Arc::new(config);

        // Forget clients that have refilled their quota, so memory doesn't grow with
        // every address ever seen.
        let limiter = config.limiter().clone();
        tokio::spawn(async move {
            let mut every = tokio::time::interval(Duration::from_secs(60));
            loop {
                every.tick().await;
                limiter.retain_recent();
            }
        });

        router.layer(GovernorLayer::new(config))
    }
}

/// Rate-limit key: the client's IP address.
///
/// Behind a proxy that's in X-Forwarded-For, but only the entries the proxies appended
/// can be trusted: a client can send the header pre-filled with anything. So the key is
/// the entry `trusted_hops` from the end. Without the header (local runs), it's the
/// connection's peer address.
#[derive(Clone)]
pub struct ClientIp {
    trusted_hops: usize,
}

impl KeyExtractor for ClientIp {
    type Key = IpAddr;

    fn extract<T>(&self, req: &Request<T>) -> Result<IpAddr, GovernorError> {
        let forwarded = req
            .headers()
            .get("x-forwarded-for")
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.rsplit(',').nth(self.trusted_hops))
            .and_then(|ip| ip.trim().parse().ok());
        let peer = || {
            req.extensions()
                .get::<ConnectInfo<SocketAddr>>()
                .map(|c| c.0.ip())
        };
        forwarded
            .or_else(peer)
            .ok_or(GovernorError::UnableToExtractKey)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::StatusCode;
    use axum::routing::get;
    use tower::ServiceExt;

    fn app(trusted_hops: usize) -> Router {
        let limit = RateLimit {
            replenish: Duration::from_secs(60),
            burst: 2,
            trusted_hops,
        };
        limit.apply(Router::new().route("/", get(|| async { "ok" })))
    }

    async fn status(app: &Router, forwarded_for: &str) -> StatusCode {
        let request = Request::get("/").header("x-forwarded-for", forwarded_for);
        let response = app
            .clone()
            .oneshot(request.body(Body::empty()).unwrap())
            .await
            .unwrap();
        response.status()
    }

    #[tokio::test]
    async fn limits_each_client_separately() {
        let app = app(0);
        assert_eq!(status(&app, "1.1.1.1").await, StatusCode::OK);
        assert_eq!(status(&app, "1.1.1.1").await, StatusCode::OK);
        assert_eq!(status(&app, "1.1.1.1").await, StatusCode::TOO_MANY_REQUESTS);
        assert_eq!(status(&app, "2.2.2.2").await, StatusCode::OK);
    }

    #[tokio::test]
    async fn forged_forwarded_for_entries_dont_change_the_key() {
        // The proxy appends the real address last; the client controls what comes before.
        let app = app(0);
        assert_eq!(status(&app, "9.9.9.1, 1.1.1.1").await, StatusCode::OK);
        assert_eq!(status(&app, "9.9.9.2, 1.1.1.1").await, StatusCode::OK);
        assert_eq!(
            status(&app, "9.9.9.3, 1.1.1.1").await,
            StatusCode::TOO_MANY_REQUESTS
        );
    }

    #[tokio::test]
    async fn trusted_hops_skips_proxy_addresses() {
        // Client, then one proxy of our own (e.g. a load balancer) appending its address.
        let app = app(1);
        assert_eq!(status(&app, "1.1.1.1, 10.0.0.1").await, StatusCode::OK);
        assert_eq!(status(&app, "1.1.1.1, 10.0.0.1").await, StatusCode::OK);
        assert_eq!(status(&app, "2.2.2.2, 10.0.0.1").await, StatusCode::OK);
        assert_eq!(
            status(&app, "1.1.1.1, 10.0.0.1").await,
            StatusCode::TOO_MANY_REQUESTS
        );
    }
}
