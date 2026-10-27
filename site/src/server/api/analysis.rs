//! Player Analysis: the defensemen loose-puck-recovery (LPR) table.

use std::cmp::Ordering;

use axum::Json;
use axum::extract::{Query, State};
use axum::response::{IntoResponse, Response};
use serde::{Deserialize, Serialize};

use super::stats::Dir;
use super::{ApiError, AppState};
use crate::server::data::DefenseLpr;

/// The page's minimums for a defenseman to be listed.
pub const MIN_GAMES_PLAYED: i64 = 20;
pub const MIN_LPRS: i64 = 15;

#[derive(Debug, Clone, Copy, Default, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum View {
    Low,
    #[default]
    High,
    HighNextSuccess,
    HighNextFailure,
    HighNextRate,
}

impl View {
    fn name(self) -> &'static str {
        match self {
            Self::Low => "low",
            Self::High => "high",
            Self::HighNextSuccess => "high_next_success",
            Self::HighNextFailure => "high_next_failure",
            Self::HighNextRate => "high_next_rate",
        }
    }
}

#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SortField {
    AvgOiXgf,
    AvgOiXga,
    TotalOiXgf,
    TotalOiXga,
    XgPct,
    Successes,
    Failures,
    SuccessRate,
}

impl SortField {
    fn value(self, r: &DefenseLpr) -> Option<f64> {
        match self {
            Self::AvgOiXgf => r.avg_oi_xgf,
            Self::AvgOiXga => r.avg_oi_xga,
            Self::TotalOiXgf => r.total_oi_xgf,
            Self::TotalOiXga => r.total_oi_xga,
            Self::XgPct => r.xg_pct,
            Self::Successes => r.successes.map(|v| v as f64),
            Self::Failures => r.failures.map(|v| v as f64),
            Self::SuccessRate => r.success_rate,
        }
    }
}

#[derive(Deserialize)]
pub struct LprQuery {
    #[serde(default)]
    view: View,
    /// Default: xG% for the xG views, success rate for the rate view (as on the page).
    sort: Option<SortField>,
    #[serde(default)]
    dir: Dir,
}

#[derive(Serialize)]
struct Row<'a> {
    full_name: &'a str,
    #[serde(flatten)]
    stats: &'a DefenseLpr,
}

/// The page's Total row: counts and xG summed, averages and percentages averaged
/// over the listed defensemen.
#[derive(Serialize, Default)]
struct Totals {
    lpr_count: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    avg_oi_xgf: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    avg_oi_xga: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    total_oi_xgf: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    total_oi_xga: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    xg_pct: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    successes: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    failures: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    success_rate: Option<f64>,
}

impl Totals {
    fn new(rows: &[&DefenseLpr]) -> Self {
        let sum =
            |f: fn(&DefenseLpr) -> Option<f64>| -> Option<f64> { rows.iter().map(|r| f(r)).sum() };
        let mean = |f: fn(&DefenseLpr) -> Option<f64>| sum(f).map(|s| s / rows.len() as f64);
        let count =
            |f: fn(&DefenseLpr) -> Option<i64>| -> Option<i64> { rows.iter().map(|r| f(r)).sum() };
        if rows.is_empty() {
            return Self::default();
        }
        Self {
            lpr_count: rows.iter().map(|r| r.lpr_count).sum(),
            avg_oi_xgf: mean(|r| r.avg_oi_xgf),
            avg_oi_xga: mean(|r| r.avg_oi_xga),
            total_oi_xgf: sum(|r| r.total_oi_xgf),
            total_oi_xga: sum(|r| r.total_oi_xga),
            xg_pct: mean(|r| r.xg_pct),
            successes: count(|r| r.successes),
            failures: count(|r| r.failures),
            success_rate: mean(|r| r.success_rate),
        }
    }
}

#[derive(Serialize)]
struct LprTable<'a> {
    view: View,
    min_games_played: i64,
    min_lprs: i64,
    totals: Totals,
    rows: Vec<Row<'a>>,
}

/// The table for one view: defensemen meeting the minimums, sorted, with totals.
pub async fn defense_lpr(
    State(store): State<AppState>,
    Query(q): Query<LprQuery>,
) -> Result<Response, ApiError> {
    let mut rows: Vec<&DefenseLpr> = store
        .defense_lpr
        .get(q.view.name())
        .into_iter()
        .flatten()
        .filter(|r| r.games_played >= MIN_GAMES_PLAYED && r.lpr_count >= MIN_LPRS)
        .collect();

    let default_sort = match q.view {
        View::HighNextRate => SortField::SuccessRate,
        _ => SortField::XgPct,
    };
    let sort = q.sort.unwrap_or(default_sort);
    let name = |r: &DefenseLpr| store.players.get(&r.player_id).map_or("", |p| &p.full_name);
    rows.sort_by(|a, b| {
        let by_field = match (sort.value(a), sort.value(b)) {
            (Some(x), Some(y)) => match q.dir {
                Dir::Asc => x.total_cmp(&y),
                Dir::Desc => y.total_cmp(&x),
            },
            (Some(_), None) => Ordering::Less,
            (None, Some(_)) => Ordering::Greater,
            (None, None) => Ordering::Equal,
        };
        by_field.then_with(|| name(a).cmp(name(b)))
    });

    let body = LprTable {
        view: q.view,
        min_games_played: MIN_GAMES_PLAYED,
        min_lprs: MIN_LPRS,
        totals: Totals::new(&rows),
        rows: rows
            .iter()
            .map(|&stats| Row {
                full_name: name(stats),
                stats,
            })
            .collect(),
    };
    Ok(Json(body).into_response())
}
