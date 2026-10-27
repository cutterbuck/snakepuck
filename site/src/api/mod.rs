//! JSON endpoints, one per page view. Each returns only what its page draws:
//! one situation's stats, one page of a table, one shift of a game.

mod game;
mod sample;
mod stats;
#[cfg(test)]
mod tests;

use std::sync::Arc;

use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use axum::{Json, Router};
use serde::Serialize;

use crate::data::{Store, Team};

type AppState = Arc<Store>;

pub fn router(store: Store) -> Router {
    Router::new()
        .route("/api/health", get(|| async { "ok" }))
        .route("/api/seasons", get(stats::seasons))
        .route("/api/standings", get(stats::standings))
        .route("/api/player-stats", get(stats::player_stats))
        .route("/api/teams/{team_abbr}/{season}", get(stats::team))
        .route("/api/players/{player_id}", get(stats::player))
        .route(
            "/api/games/{game_id}/players/{player_id}",
            get(game::report),
        )
        .route(
            "/api/games/{game_id}/players/{player_id}/shifts/{shift}",
            get(game::shift),
        )
        .route("/api/sample/{name}", get(sample::sample))
        .with_state(Arc::new(store))
}

pub enum ApiError {
    NotFound(String),
    Internal(anyhow::Error),
}

impl From<anyhow::Error> for ApiError {
    fn from(e: anyhow::Error) -> Self {
        Self::Internal(e)
    }
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            Self::NotFound(m) => (StatusCode::NOT_FOUND, m),
            Self::Internal(e) => {
                tracing::error!("{e:#}");
                (StatusCode::INTERNAL_SERVER_ERROR, "internal error".into())
            }
        };
        (status, Json(serde_json::json!({ "error": message }))).into_response()
    }
}

fn not_found(what: impl std::fmt::Display) -> ApiError {
    ApiError::NotFound(format!("no {what}"))
}

/// A team as other responses reference it.
#[derive(Serialize)]
struct TeamRef<'a> {
    team_abbr: &'a str,
    team_name: &'a str,
    logo_url: &'a str,
}

impl<'a> TeamRef<'a> {
    fn new(store: &'a Store, team_abbr: &'a str) -> Self {
        let team = store.teams.get(team_abbr);
        Self {
            team_abbr,
            team_name: team.map_or("", |t: &Team| &t.team_name),
            logo_url: team.map_or("", |t| &t.logo_url),
        }
    }
}
