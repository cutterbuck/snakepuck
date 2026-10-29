//! SnakePuck server: the JSON API and the server-rendered site, in one process.
//!
//! Environment:
//!   DATA_DIR  serving files from infra/export_serving.py (default: data/serving)
//!   CONTENT_DIR  blog posts (default: ../content/blog); SHOW_DRAFTS=1 to include drafts
//!   PORT      listen port (Cloud Run sets it); otherwise the Leptos site address
//!   TRUSTED_PROXY_HOPS  proxies appending to X-Forwarded-For after the client (default: 0)
//!   RATE_LIMIT_PER_SECOND, RATE_LIMIT_BURST  per-client limit (default: 5/s, bursts of 50)
//!   LEPTOS_*  site settings; cargo-leptos sets them in development, the Dockerfile in
//!             production (defaults are in Cargo.toml under [package.metadata.leptos])
//!
//! Local run, from site/ (data/ is git-ignored; the data is licensed):
//!   gcloud storage rsync -r gs://snakepuck-data/serving/dev data/serving
//!   cargo leptos watch   # http://localhost:3000, rebuilds and reloads on save

use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

use anyhow::Result;
use axum::Router;
use axum::extract::Request;
use axum::http::{HeaderValue, header};
use axum::middleware::Next;
use axum::response::Response;
use leptos::prelude::*;
use leptos_axum::{LeptosRoutes, generate_route_list};
use snakepuck::app::{App, shell};
use snakepuck::server::{api, blog, data, limit};
use tower_http::compression::CompressionLayer;
use tower_http::trace::TraceLayer;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| "info,tower_http=info".into()),
        )
        .init();

    let data_dir =
        PathBuf::from(std::env::var("DATA_DIR").unwrap_or_else(|_| "data/serving".into()));
    let started = Instant::now();
    let mut store = data::Store::load(&data_dir)?;
    let content_dir =
        PathBuf::from(std::env::var("CONTENT_DIR").unwrap_or_else(|_| "../content/blog".into()));
    let show_drafts = std::env::var("SHOW_DRAFTS").is_ok_and(|v| v == "1");
    store.blog = blog::Blog::load(&content_dir, show_drafts)?;
    let store = Arc::new(store);
    tracing::info!(
        players = store.players.len(),
        games = store.games.len(),
        player_seasons = store.player_seasons.len(),
        player_games = store.player_games.len(),
        elapsed_ms = started.elapsed().as_millis() as u64,
        "loaded marts from {}",
        data_dir.display()
    );

    let mut options = get_configuration(None)?.leptos_options;
    if let Ok(port) = std::env::var("PORT") {
        options.site_addr = SocketAddr::from(([0, 0, 0, 0], port.parse()?));
    }
    let addr = options.site_addr;

    // Pages render with the same in-memory store the API uses.
    let pages = Router::new()
        .leptos_routes_with_context(
            &options,
            generate_route_list(App),
            {
                let store = store.clone();
                move || provide_context(store.clone())
            },
            {
                let options = options.clone();
                move || shell(options.clone())
            },
        )
        .fallback(leptos_axum::file_and_error_handler(shell))
        .with_state(options);

    let app = limit::RateLimit::from_env()
        .apply(api::router(store).merge(pages))
        .layer(axum::middleware::from_fn(cache_static))
        .layer(CompressionLayer::new())
        .layer(TraceLayer::new_for_http());

    let listener = tokio::net::TcpListener::bind(addr).await?;
    tracing::info!("listening on {}", listener.local_addr()?);
    axum::serve(
        listener,
        app.into_make_service_with_connect_info::<SocketAddr>(),
    )
    .await?;
    Ok(())
}

/// Browser and CDN caching for static files. `/pkg` holds the browser bundle and CSS under
/// content-hashed names (`hash-files` in Cargo.toml), so a new build gets new URLs and the
/// old ones can be cached for a year. Other static files (images, the favicon) keep their
/// names, so a day. Pages and the API aren't cached: they're rendered per request.
async fn cache_static(req: Request, next: Next) -> Response {
    let path = req.uri().path();
    let policy = if path.starts_with("/pkg/") {
        Some("public, max-age=31536000, immutable")
    } else if path.starts_with("/assets/") || path == "/favicon.ico" {
        Some("public, max-age=86400")
    } else {
        None
    };
    let mut response = next.run(req).await;
    if let Some(policy) = policy.filter(|_| response.status().is_success()) {
        response
            .headers_mut()
            .insert(header::CACHE_CONTROL, HeaderValue::from_static(policy));
    }
    response
}
