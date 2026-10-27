//! Sample Data: a fixed 100-row sample of each table, written by the export.

use axum::extract::{Path, State};
use axum::http::header;
use axum::response::{IntoResponse, Response};

use super::{ApiError, AppState, not_found};

use crate::server::data::Store;
use crate::types::SampleRows;

/// Rows of one sample (players, games, stints, events, tracking), already JSON.
fn json<'a>(store: &'a Store, name: &str) -> Result<&'a axum::body::Bytes, ApiError> {
    store
        .samples
        .get(name)
        .ok_or_else(|| not_found(format!("sample {name}")))
}

/// For server rendering: the rows, parsed.
pub fn sample(store: &Store, name: &str) -> Result<SampleRows, ApiError> {
    Ok(serde_json::from_slice(json(store, name)?).map_err(anyhow::Error::from)?)
}

pub async fn sample_handler(
    State(store): State<AppState>,
    Path(name): Path<String>,
) -> Result<Response, ApiError> {
    let json = json(&store, &name)?.clone();
    Ok(([(header::CONTENT_TYPE, "application/json")], json).into_response())
}
