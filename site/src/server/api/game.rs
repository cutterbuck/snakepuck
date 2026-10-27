//! Game Report: one player's game, and the rink frames for one of their shifts.

use std::sync::Arc;

use axum::Json;
use axum::extract::{Path, Query, State};
use axum::response::{IntoResponse, Response};
use serde::Serialize;

use super::stats::SituationQuery;
use super::{ApiError, AppState, TeamRef, not_found};
use crate::server::data::{Game, GameStats, PlayerGame};
use crate::server::games::{Event, GameFiles, Shift, Snapshot, Stint};

/// Check the game and player-game exist, then load the game's files (blocking I/O,
/// so off the async threads). The game_id check also keeps it from being used as an
/// arbitrary path.
async fn load(
    store: &AppState,
    game_id: &str,
    player_id: &str,
) -> Result<(usize, Arc<GameFiles>), ApiError> {
    let key = (game_id.to_string(), player_id.to_string());
    let index = match (
        store.games.contains_key(game_id),
        store.player_game.get(&key),
    ) {
        (true, Some(&i)) => i,
        _ => return Err(not_found(format!("game {game_id} for player {player_id}"))),
    };
    let (store, game_id) = (store.clone(), game_id.to_string());
    let files = tokio::task::spawn_blocking(move || store.game_files.get(&game_id))
        .await
        .map_err(anyhow::Error::from)??;
    Ok((index, files))
}

#[derive(Serialize)]
struct GameHeader<'a> {
    game_id: &'a str,
    game_date: &'a str,
    season: &'a str,
    home: TeamRef<'a>,
    away: TeamRef<'a>,
    home_score: i64,
    away_score: i64,
}

impl<'a> GameHeader<'a> {
    fn new(store: &'a crate::server::data::Store, game: &'a Game) -> Self {
        Self {
            game_id: &game.game_id,
            game_date: &game.game_date,
            season: &game.season,
            home: TeamRef::new(store, &game.home_team_abbr),
            away: TeamRef::new(store, &game.away_team_abbr),
            home_score: game.home_score,
            away_score: game.away_score,
        }
    }
}

#[derive(Serialize)]
struct Report<'a> {
    game: GameHeader<'a>,
    player_id: &'a str,
    full_name: &'a str,
    position: &'a str,
    team_abbr: &'a str,
    is_home: bool,
    result: &'a str,
    team_score: i64,
    opp_score: i64,
    penalties: i64,
    penalties_drawn: i64,
    stats: &'a GameStats,
    has_tracking: bool,
    /// Periods the player had a shift in.
    periods: Vec<i64>,
    shifts: Vec<&'a Shift>,
}

/// The player's stat line and shift list for one game.
pub async fn report(
    State(store): State<AppState>,
    Path((game_id, player_id)): Path<(String, String)>,
    Query(q): Query<SituationQuery>,
) -> Result<Response, ApiError> {
    let (index, files) = load(&store, &game_id, &player_id).await?;
    let pg: &PlayerGame = &store.player_games[index];
    let player = store.players.get(&player_id);

    let shifts: Vec<_> = files
        .shifts
        .iter()
        .filter(|s| s.player_id == player_id)
        .collect();
    let mut periods: Vec<_> = shifts.iter().map(|s| s.period).collect();
    periods.dedup(); // shifts are in order, so periods already are

    let r = &pg.row;
    let body = Report {
        game: GameHeader::new(&store, &store.games[&game_id]),
        player_id: &player_id,
        full_name: player.map_or("", |p| &p.full_name),
        position: player.map_or("", |p| &p.primary_position),
        team_abbr: &r.team_abbr,
        is_home: r.is_home,
        result: &r.result,
        team_score: r.team_score,
        opp_score: r.opp_score,
        penalties: r.penalties,
        penalties_drawn: r.penalties_drawn,
        stats: pg.stats(q.situation),
        has_tracking: !files.tracking.is_empty(),
        periods,
        shifts,
    };
    Ok(Json(body).into_response())
}

/// One event and every tracked skater's position at that moment.
#[derive(Serialize)]
struct Frame<'a> {
    #[serde(flatten)]
    event: &'a Event,
    skaters: &'a [Snapshot],
}

#[derive(Serialize)]
struct ShiftDetail<'a> {
    shift: &'a Shift,
    stints: Vec<&'a Stint>,
    /// Every event in the shift's time window, in time order.
    frames: Vec<Frame<'a>>,
}

/// The rink for one shift: the stints it spans, and a frame per event in its window.
pub async fn shift(
    State(store): State<AppState>,
    Path((game_id, player_id, shift)): Path<(String, String, i64)>,
) -> Result<Response, ApiError> {
    let (_, files) = load(&store, &game_id, &player_id).await?;
    let s = files
        .shifts
        .iter()
        .find(|s| s.player_id == player_id && s.shift == shift)
        .ok_or_else(|| not_found(format!("shift {shift} for player {player_id}")))?;

    let stints = files
        .stints
        .iter()
        .filter(|st| st.player_id == player_id && st.shift == Some(shift))
        .collect();

    let mut events: Vec<_> = files
        .events
        .iter()
        .filter(|e| {
            e.period == s.period
                && (s.period_time_start..=s.period_time_end).contains(&e.period_time)
        })
        .collect();
    events.sort_by(|a, b| a.period_time.total_cmp(&b.period_time));
    let frames = events
        .into_iter()
        .map(|event| Frame {
            event,
            skaters: files.snapshots(event.sl_event_id),
        })
        .collect();

    Ok(Json(ShiftDetail {
        shift: s,
        stints,
        frames,
    })
    .into_response())
}
