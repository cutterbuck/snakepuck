//! Game Report: one player's game, and the rink frames for one of their shifts.

use std::sync::Arc;

use axum::Json;
use axum::extract::{Path, Query, State};

use super::{ApiError, AppState, TeamRef, not_found};
use crate::server::data::{Game, PlayerGame, Store};
use crate::server::games::GameFiles;
use crate::types::{Frame, GameHeader, GameReport, ShiftDetail, SituationQuery};

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

fn game_header(store: &Store, game: &Game) -> GameHeader {
    GameHeader {
        game_id: game.game_id.clone(),
        game_date: game.game_date.clone(),
        season: game.season.clone(),
        home: TeamRef::new(store, &game.home_team_abbr).info(),
        away: TeamRef::new(store, &game.away_team_abbr).info(),
        home_score: game.home_score,
        away_score: game.away_score,
    }
}

/// The player's stat line, shifts and stints for one game.
pub async fn report(
    store: &AppState,
    game_id: &str,
    player_id: &str,
    q: SituationQuery,
) -> Result<GameReport, ApiError> {
    let (index, files) = load(store, game_id, player_id).await?;
    let pg: &PlayerGame = &store.player_games[index];
    let player = store.players.get(player_id);

    let shifts: Vec<_> = files
        .shifts
        .iter()
        .filter(|s| s.player_id == player_id)
        .cloned()
        .collect();
    let mut periods: Vec<_> = shifts.iter().map(|s| s.period).collect();
    periods.dedup(); // shifts are in order, so periods already are
    let stints = files
        .stints
        .iter()
        .filter(|st| st.player_id == player_id && st.shift.is_some())
        .cloned()
        .collect();

    let r = &pg.row;
    Ok(GameReport {
        game: game_header(store, &store.games[game_id]),
        player_id: player_id.to_string(),
        full_name: player.map_or(String::new(), |p| p.full_name.clone()),
        position: player.map_or(String::new(), |p| p.primary_position.clone()),
        team_abbr: r.team_abbr.clone(),
        is_home: r.is_home,
        result: r.result.clone(),
        team_score: r.team_score,
        opp_score: r.opp_score,
        penalties: r.penalties,
        penalties_drawn: r.penalties_drawn,
        situation: q.situation,
        stats: pg.stats(q.situation).clone(),
        has_tracking: !files.tracking.is_empty(),
        periods,
        shifts,
        stints,
    })
}

pub async fn report_handler(
    State(store): State<AppState>,
    Path((game_id, player_id)): Path<(String, String)>,
    Query(q): Query<SituationQuery>,
) -> Result<Json<GameReport>, ApiError> {
    Ok(Json(report(&store, &game_id, &player_id, q).await?))
}

/// The rink for one shift: the stints it spans, and a frame per event in its window.
pub async fn shift(
    store: &AppState,
    game_id: &str,
    player_id: &str,
    shift: i64,
) -> Result<ShiftDetail, ApiError> {
    let (_, files) = load(store, game_id, player_id).await?;
    let s = files
        .shifts
        .iter()
        .find(|s| s.player_id == player_id && s.shift == shift)
        .ok_or_else(|| not_found(format!("shift {shift} for player {player_id}")))?;

    let stints = files
        .stints
        .iter()
        .filter(|st| st.player_id == player_id && st.shift == Some(shift))
        .cloned()
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
            event: event.clone(),
            skaters: files.snapshots(event.sl_event_id).to_vec(),
        })
        .collect();

    Ok(ShiftDetail {
        shift: s.clone(),
        stints,
        frames,
    })
}

pub async fn shift_handler(
    State(store): State<AppState>,
    Path((game_id, player_id, n)): Path<(String, String, i64)>,
) -> Result<Json<ShiftDetail>, ApiError> {
    Ok(Json(shift(&store, &game_id, &player_id, n).await?))
}
