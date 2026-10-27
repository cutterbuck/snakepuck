//! Serving data: the dbt marts, read from the Parquet files that
//! `infra/export_serving.py` writes (`<data_dir>/marts/<table>/*.parquet`).
//!
//! Small marts are loaded once at startup into typed rows plus indexes. Each row
//! type declares only the columns the API serves, and only those are read.

use std::collections::{BTreeSet, HashMap};
use std::fs::File;
use std::path::Path;

use anyhow::{Context, Result};
use arrow::datatypes::FieldRef;
use parquet::arrow::ProjectionMask;
use parquet::arrow::arrow_reader::ParquetRecordBatchReaderBuilder;
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use serde_arrow::schema::{SchemaLike, TracingOptions};

/// `dim_teams`
#[derive(Debug, Clone, Deserialize)]
pub struct Team {
    pub team_abbr: String,
    pub team_name: String,
    pub division: String,
    pub league: String,
    pub logo_url: String,
}

/// `fct_team_season_stats`
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct TeamSeason {
    pub team_abbr: String,
    pub season: String,
    pub games_played: i64,
    pub wins: i64,
    pub losses: i64,
    pub ot_losses: i64,
    pub points: i64,
    pub points_percentage: f64,
    pub regulation_wins: i64,
    pub regulation_or_ot_wins: i64,
    pub goals_forward: i64,
    pub goals_against: i64,
    pub goal_diff: i64,
    pub so_record: String,
}

/// `dim_games`
#[derive(Debug, Clone, Deserialize)]
pub struct Game {
    pub league: String,
    pub season: String,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize)]
pub struct Season {
    pub league: String,
    pub season: String,
}

pub struct Store {
    pub teams: HashMap<String, Team>,
    /// Newest season first.
    pub seasons: Vec<Season>,
    /// Keyed by (league, season).
    pub team_seasons: HashMap<(String, String), Vec<TeamSeason>>,
}

impl Store {
    pub fn load(data_dir: &Path) -> Result<Self> {
        let marts = data_dir.join("marts");
        Ok(Self::new(
            read_dir(&marts.join("dim_teams"))?,
            read_dir(&marts.join("dim_games"))?,
            read_dir(&marts.join("fct_team_season_stats"))?,
        ))
    }

    pub fn new(teams: Vec<Team>, games: Vec<Game>, team_seasons: Vec<TeamSeason>) -> Self {
        let teams: HashMap<_, _> = teams
            .into_iter()
            .map(|t| (t.team_abbr.clone(), t))
            .collect();

        let seasons: BTreeSet<_> = games
            .into_iter()
            .map(|g| Season {
                league: g.league,
                season: g.season,
            })
            .collect();

        let mut by_league_season: HashMap<_, Vec<_>> = HashMap::new();
        for ts in team_seasons {
            let league = teams
                .get(&ts.team_abbr)
                .map_or("", |t| &t.league)
                .to_string();
            by_league_season
                .entry((league, ts.season.clone()))
                .or_default()
                .push(ts);
        }

        Self {
            teams,
            seasons: seasons.into_iter().rev().collect(),
            team_seasons: by_league_season,
        }
    }
}

/// Read every Parquet file in `dir` into rows of `T`, reading only the columns `T` declares.
pub fn read_dir<T: DeserializeOwned>(dir: &Path) -> Result<Vec<T>> {
    let fields = Vec::<FieldRef>::from_type::<T>(TracingOptions::default())?;
    let columns: Vec<&str> = fields.iter().map(|f| f.name().as_str()).collect();

    let mut paths: Vec<_> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .map(|entry| entry.map(|e| e.path()))
        .collect::<Result<_, _>>()?;
    paths.retain(|p| p.extension().is_some_and(|ext| ext == "parquet"));
    paths.sort();

    let mut rows = Vec::new();
    for path in &paths {
        read_file(path, &columns, &mut rows)
            .with_context(|| format!("reading {}", path.display()))?;
    }
    Ok(rows)
}

fn read_file<T: DeserializeOwned>(path: &Path, columns: &[&str], rows: &mut Vec<T>) -> Result<()> {
    let builder = ParquetRecordBatchReaderBuilder::try_new(File::open(path)?)?;
    let mask = ProjectionMask::columns(builder.parquet_schema(), columns.iter().copied());
    for batch in builder.with_projection(mask).build()? {
        rows.extend(serde_arrow::from_record_batch::<Vec<T>>(&batch?)?);
    }
    Ok(())
}
