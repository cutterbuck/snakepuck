//! Blog posts: the listing and one post.

use axum::Json;
use axum::extract::{Path, State};

use super::{ApiError, AppState, not_found};
use crate::server::data::Store;
use crate::types::{Post, PostSummary};

pub fn list(store: &Store) -> Vec<PostSummary> {
    store.blog.list()
}

pub fn post(store: &Store, slug: &str) -> Result<Post, ApiError> {
    store
        .blog
        .get(slug)
        .ok_or_else(|| not_found(format!("post {slug}")))
}

pub async fn list_handler(State(store): State<AppState>) -> Json<Vec<PostSummary>> {
    Json(list(&store))
}

pub async fn post_handler(
    State(store): State<AppState>,
    Path(slug): Path<String>,
) -> Result<Json<Post>, ApiError> {
    Ok(Json(post(&store, &slug)?))
}
