//! Sample Data: a fixed 100-row sample of each table, written by the export.

use axum::extract::{Path, State};
use axum::http::header;
use axum::response::{IntoResponse, Response};

use super::{ApiError, AppState, not_found};

/// Rows of one sample (players, games, stints, events, tracking), already JSON.
pub async fn sample(
    State(store): State<AppState>,
    Path(name): Path<String>,
) -> Result<Response, ApiError> {
    let json = store
        .samples
        .get(&name)
        .ok_or_else(|| not_found(format!("sample {name}")))?;
    Ok(([(header::CONTENT_TYPE, "application/json")], json.clone()).into_response())
}
