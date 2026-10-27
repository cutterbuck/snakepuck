//! Per-game marts (`<data_dir>/games/<table>/<game_id>.parquet`): too large to hold
//! in memory whole, so each game's files are loaded the first time it's asked for and
//! kept in a small cache.

use std::path::PathBuf;
use std::sync::Arc;

use anyhow::Result;
use quick_cache::sync::Cache;
use serde::{Deserialize, Serialize};

use crate::data::read_files;

/// Games held in memory at once. A game's files take roughly 10 MB as rows.
const CACHED_GAMES: usize = 16;

/// `fct_shifts`
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct Shift {
    #[serde(skip_serializing)]
    pub player_id: String,
    pub shift: i64,
    pub period: i64,
    pub period_time_start: f64,
    pub period_time_end: f64,
    pub toi: f64,
    pub n_home_skaters: i64,
    pub n_away_skaters: i64,
    pub is_home_net_empty: bool,
    pub is_away_net_empty: bool,
    pub home_score: i64,
    pub away_score: i64,
    pub i_xg: f64,
    pub oi_xgf: f64,
    pub oi_xga: f64,
}

/// `fct_stints`, all-situations stats only. Goalies have no shift.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct Stint {
    #[serde(skip_serializing)]
    pub player_id: String,
    #[serde(skip_serializing)]
    pub shift: Option<i64>,
    pub game_stint: i64,
    pub period: i64,
    pub period_time_start: f64,
    pub period_time_end: f64,
    pub n_home_skaters: i64,
    pub n_away_skaters: i64,
    pub is_home_net_empty: bool,
    pub is_away_net_empty: bool,
    pub home_score: i64,
    pub away_score: i64,
    #[serde(rename(serialize = "toi"))]
    pub tot_toi: f64,
    #[serde(rename(serialize = "i_xg"))]
    pub tot_i_xg: f64,
    #[serde(rename(serialize = "oi_xgf"))]
    pub tot_oi_xgf: f64,
    #[serde(rename(serialize = "oi_xga"))]
    pub tot_oi_xga: f64,
}

/// `fct_game_events`. Events with no player (stoppages, period ends) have no team or location.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct Event {
    pub sl_event_id: i64,
    #[serde(skip_serializing)]
    pub period: i64,
    pub period_time: f64,
    pub player_id: Option<String>,
    pub team_abbr: Option<String>,
    pub event_type: String,
    pub outcome: Option<String>,
    pub description: String,
    pub detail: String,
    pub flags: Option<String>,
    pub x: Option<f64>,
    pub y: Option<f64>,
}

/// `fct_tracking_snapshots`: one skater's position at one event. Skaters HALO couldn't
/// identify have no player_id.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct Snapshot {
    #[serde(skip_serializing)]
    pub sl_event_id: i64,
    pub team_abbr: String,
    pub player_id: Option<String>,
    pub last_name: Option<String>,
    pub display_name: String,
    pub tracking_x: f64,
    pub tracking_y: f64,
}

/// One game's per-game marts. Rows are in the order the export sorts them:
/// shifts by (player, shift), stints by stint, events and tracking by event id.
#[derive(Debug, Default)]
pub struct GameFiles {
    pub shifts: Vec<Shift>,
    pub stints: Vec<Stint>,
    pub events: Vec<Event>,
    /// Empty for games HALO has no tracking for.
    pub tracking: Vec<Snapshot>,
}

impl GameFiles {
    /// Tracking rows for one event.
    pub fn snapshots(&self, sl_event_id: i64) -> &[Snapshot] {
        let start = self
            .tracking
            .partition_point(|s| s.sl_event_id < sl_event_id);
        let end = self
            .tracking
            .partition_point(|s| s.sl_event_id <= sl_event_id);
        &self.tracking[start..end]
    }
}

pub struct GameCache {
    dir: PathBuf,
    cache: Cache<String, Arc<GameFiles>>,
}

impl GameCache {
    pub fn new(data_dir: PathBuf) -> Self {
        Self {
            dir: data_dir.join("games"),
            cache: Cache::new(CACHED_GAMES),
        }
    }

    /// Load (or fetch from cache) one game's files. Blocking. `game_id` becomes part of a
    /// file path, so callers must check it's a known game first.
    pub fn get(&self, game_id: &str) -> Result<Arc<GameFiles>> {
        self.cache
            .get_or_insert_with(game_id, || self.load(game_id).map(Arc::new))
    }

    /// Reads the four files in parallel: over the Cloud Storage mount each read is a
    /// network round trip, so this takes about as long as the slowest one.
    fn load(&self, game_id: &str) -> Result<GameFiles> {
        let path = |table: &str| self.dir.join(table).join(format!("{game_id}.parquet"));
        let tracking = path("fct_tracking_snapshots");
        std::thread::scope(|s| {
            let shifts = s.spawn(|| read_files(&[path("fct_shifts")], ""));
            let stints = s.spawn(|| read_files(&[path("fct_stints")], ""));
            let events = s.spawn(|| read_files(&[path("fct_game_events")], ""));
            let tracking = s.spawn(|| match tracking.exists() {
                true => read_files(&[tracking], ""),
                false => Ok(Vec::new()),
            });
            let panicked = |_| anyhow::anyhow!("reading game {game_id} panicked");
            Ok(GameFiles {
                shifts: shifts.join().map_err(panicked)??,
                stints: stints.join().map_err(panicked)??,
                events: events.join().map_err(panicked)??,
                tracking: tracking.join().map_err(panicked)??,
            })
        })
    }

    #[cfg(test)]
    pub fn insert(&self, game_id: &str, files: GameFiles) {
        self.cache.insert(game_id.to_string(), Arc::new(files));
    }
}
