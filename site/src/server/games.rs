//! Per-game marts (`<data_dir>/games/<table>/<game_id>.parquet`): too large to hold
//! in memory whole, so each game's files are loaded the first time it's asked for and
//! kept in a small cache.

use std::path::PathBuf;
use std::sync::Arc;

use serde::Deserialize;

use crate::server::data::read_files;
pub use crate::types::{Event, Shift, Snapshot, Stint};

/// A `fct_stints` row as stored; served as a `Stint`, without the `tot_` prefixes.
#[derive(Deserialize)]
struct StintRow {
    player_id: String,
    shift: Option<i64>,
    game_stint: i64,
    period: i64,
    period_time_start: f64,
    period_time_end: f64,
    n_home_skaters: i64,
    n_away_skaters: i64,
    is_home_net_empty: bool,
    is_away_net_empty: bool,
    home_score: i64,
    away_score: i64,
    tot_toi: f64,
    tot_i_xg: f64,
    tot_oi_xgf: f64,
    tot_oi_xga: f64,
}

impl From<StintRow> for Stint {
    fn from(r: StintRow) -> Self {
        Self {
            player_id: r.player_id,
            shift: r.shift,
            game_stint: r.game_stint,
            period: r.period,
            period_time_start: r.period_time_start,
            period_time_end: r.period_time_end,
            n_home_skaters: r.n_home_skaters,
            n_away_skaters: r.n_away_skaters,
            is_home_net_empty: r.is_home_net_empty,
            is_away_net_empty: r.is_away_net_empty,
            home_score: r.home_score,
            away_score: r.away_score,
            toi: r.tot_toi,
            i_xg: r.tot_i_xg,
            oi_xgf: r.tot_oi_xgf,
            oi_xga: r.tot_oi_xga,
        }
    }
}
use anyhow::Result;
use quick_cache::sync::Cache;

/// Games held in memory at once. A game's files take roughly 10 MB as rows.
const CACHED_GAMES: usize = 16;

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
            let stints = s.spawn(|| read_files::<StintRow>(&[path("fct_stints")], ""));
            let events = s.spawn(|| read_files(&[path("fct_game_events")], ""));
            let tracking = s.spawn(|| match tracking.exists() {
                true => read_files(&[tracking], ""),
                false => Ok(Vec::new()),
            });
            let panicked = |_| anyhow::anyhow!("reading game {game_id} panicked");
            Ok(GameFiles {
                shifts: shifts.join().map_err(panicked)??,
                stints: stints
                    .join()
                    .map_err(panicked)??
                    .into_iter()
                    .map(Stint::from)
                    .collect(),
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

#[cfg(test)]
mod tests {
    use super::*;

    /// The loader reads the columns a row type names, found by tracing the type. A type
    /// that can't be traced (say, a serde alias naming a column twice) fails every game at
    /// runtime, which tests that build `GameFiles` directly wouldn't notice.
    #[test]
    fn every_game_file_row_type_can_be_read() {
        read_files::<Shift>(&[], "").unwrap();
        read_files::<StintRow>(&[], "").unwrap();
        read_files::<Event>(&[], "").unwrap();
        read_files::<Snapshot>(&[], "").unwrap();
    }
}
