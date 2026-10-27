//! JSON endpoints, one per page view. Each returns only what its page draws.

use std::sync::Arc;

use axum::extract::{Query, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use axum::{Json, Router};
use serde::{Deserialize, Serialize};

use crate::data::{Season, Store, TeamSeason};

type AppState = Arc<Store>;

pub fn router(store: Store) -> Router {
    Router::new()
        .route("/api/health", get(|| async { "ok" }))
        .route("/api/seasons", get(seasons))
        .route("/api/standings", get(standings))
        .with_state(Arc::new(store))
}

pub enum ApiError {
    NotFound(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            ApiError::NotFound(m) => (StatusCode::NOT_FOUND, m),
        };
        (status, Json(serde_json::json!({ "error": message }))).into_response()
    }
}

async fn seasons(State(store): State<AppState>) -> Json<Vec<Season>> {
    Json(store.seasons.clone())
}

#[derive(Deserialize)]
struct LeagueSeason {
    league: String,
    season: String,
}

#[derive(Serialize)]
struct StandingsRow<'a> {
    team_name: &'a str,
    logo_url: &'a str,
    division: &'a str,
    #[serde(flatten)]
    stats: &'a TeamSeason,
}

/// Standings for one league-season, ordered by points, then RW, ROW and W
/// (the tiebreakers the Dash page uses).
async fn standings(
    State(store): State<AppState>,
    Query(q): Query<LeagueSeason>,
) -> Result<Response, ApiError> {
    let rows = store
        .team_seasons
        .get(&(q.league.clone(), q.season.clone()))
        .ok_or_else(|| ApiError::NotFound(format!("no standings for {} {}", q.league, q.season)))?;

    let mut rows: Vec<_> = rows
        .iter()
        .map(|ts| {
            let team = &store.teams[&ts.team_abbr];
            StandingsRow {
                team_name: &team.team_name,
                logo_url: &team.logo_url,
                division: &team.division,
                stats: ts,
            }
        })
        .collect();
    rows.sort_by_key(|r| {
        let s = r.stats;
        std::cmp::Reverse((s.points, s.regulation_wins, s.regulation_or_ot_wins, s.wins))
    });
    Ok(Json(rows).into_response())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::{Game, Team};
    use axum::body::Body;
    use axum::http::Request;
    use http_body_util::BodyExt;
    use tower::ServiceExt;

    fn team(abbr: &str) -> Team {
        Team {
            team_abbr: abbr.into(),
            team_name: format!("{abbr} Team"),
            division: "Pacific".into(),
            league: "AHL".into(),
            logo_url: format!("https://logos/{abbr}.png"),
        }
    }

    fn team_season(abbr: &str, points: i64, regulation_wins: i64) -> TeamSeason {
        TeamSeason {
            team_abbr: abbr.into(),
            season: "2023-24".into(),
            games_played: 72,
            wins: 40,
            losses: 25,
            ot_losses: 7,
            points,
            points_percentage: 0.6,
            regulation_wins,
            regulation_or_ot_wins: 35,
            goals_forward: 230,
            goals_against: 200,
            goal_diff: 30,
            so_record: "3-2".into(),
        }
    }

    fn store() -> Store {
        let game = |season: &str| Game {
            league: "AHL".into(),
            season: season.into(),
        };
        Store::new(
            vec![team("ABB"), team("BAK"), team("CGY")],
            vec![game("2022-23"), game("2023-24"), game("2023-24")],
            vec![
                team_season("ABB", 90, 30),
                team_season("BAK", 95, 28),
                team_season("CGY", 90, 33),
            ],
        )
    }

    async fn get_json(uri: &str) -> (StatusCode, serde_json::Value) {
        let response = router(store())
            .oneshot(Request::get(uri).body(Body::empty()).unwrap())
            .await
            .unwrap();
        let status = response.status();
        let body = response.into_body().collect().await.unwrap().to_bytes();
        (status, serde_json::from_slice(&body).unwrap())
    }

    #[tokio::test]
    async fn seasons_newest_first() {
        let (status, body) = get_json("/api/seasons").await;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body[0]["season"], "2023-24");
        assert_eq!(body[1]["season"], "2022-23");
    }

    #[tokio::test]
    async fn standings_sorted_by_points_then_regulation_wins() {
        let (status, body) = get_json("/api/standings?league=AHL&season=2023-24").await;
        assert_eq!(status, StatusCode::OK);
        let order: Vec<_> = body
            .as_array()
            .unwrap()
            .iter()
            .map(|r| r["team_abbr"].as_str().unwrap())
            .collect();
        assert_eq!(order, ["BAK", "CGY", "ABB"]);
        assert_eq!(body[0]["team_name"], "BAK Team");
        assert_eq!(body[0]["points"], 95);
    }

    #[tokio::test]
    async fn standings_unknown_season_is_404() {
        let (status, body) = get_json("/api/standings?league=AHL&season=1999-00").await;
        assert_eq!(status, StatusCode::NOT_FOUND);
        assert!(body["error"].as_str().unwrap().contains("1999-00"));
    }
}
