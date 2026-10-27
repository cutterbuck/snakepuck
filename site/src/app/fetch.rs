//! Page data. Each function is one API endpoint: during server rendering it calls the
//! endpoint's function directly (no HTTP); in the browser it fetches `/api/...`.
//! Either way the page gets the same response type from `crate::types`.

use crate::types::{PageError, Post, PostSummary};

pub async fn blog_posts() -> Result<Vec<PostSummary>, PageError> {
    #[cfg(feature = "ssr")]
    {
        Ok(crate::server::api::blog::list(&store()))
    }
    #[cfg(not(feature = "ssr"))]
    {
        get("/api/blog").await
    }
}

pub async fn blog_post(slug: String) -> Result<Post, PageError> {
    #[cfg(feature = "ssr")]
    {
        Ok(crate::server::api::blog::post(&store(), &slug)?)
    }
    #[cfg(not(feature = "ssr"))]
    {
        get(&format!("/api/blog/{}", encode(&slug))).await
    }
}

#[cfg(feature = "ssr")]
fn store() -> std::sync::Arc<crate::server::data::Store> {
    leptos::prelude::expect_context()
}

/// GET a JSON endpoint. The API answers errors as `{"error": "..."}`.
///
/// Browser futures aren't `Send`, which `Resource` requires; the browser is
/// single-threaded, so `SendWrapper` is safe here.
#[cfg(feature = "hydrate")]
async fn get<T: serde::de::DeserializeOwned>(path: &str) -> Result<T, PageError> {
    send_wrapper::SendWrapper::new(fetch_json(path)).await
}

#[cfg(feature = "hydrate")]
async fn fetch_json<T: serde::de::DeserializeOwned>(path: &str) -> Result<T, PageError> {
    let failed = |e: gloo_net::Error| PageError::Failed(e.to_string());
    let response = gloo_net::http::Request::get(path)
        .send()
        .await
        .map_err(failed)?;
    if response.ok() {
        return response.json().await.map_err(failed);
    }
    let message = match response.json::<serde_json::Value>().await {
        Ok(body) => body["error"].as_str().unwrap_or_default().to_string(),
        Err(_) => format!("HTTP {}", response.status()),
    };
    Err(match response.status() {
        404 => PageError::NotFound(message),
        _ => PageError::Failed(message),
    })
}

#[cfg(not(any(feature = "ssr", feature = "hydrate")))]
async fn get<T>(_path: &str) -> Result<T, PageError> {
    unreachable!("built with neither ssr nor hydrate")
}

/// Percent-encode a path segment.
#[cfg(not(feature = "ssr"))]
fn encode(segment: &str) -> String {
    serde_urlencoded::to_string([("", segment)]).unwrap_or_default()[1..].to_string()
}
