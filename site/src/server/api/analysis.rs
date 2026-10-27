//! Player Analysis: the defensemen loose-puck-recovery (LPR) table.

use std::cmp::Ordering;

use axum::Json;
use axum::extract::{Query, State};

use super::AppState;
use crate::server::data::{DefenseLpr, Store};
use crate::types::{Dir, LprQuery, LprRow, LprSortField, LprTable, LprTotals, LprView};

/// The page's minimums for a defenseman to be listed.
pub const MIN_GAMES_PLAYED: i64 = 20;
pub const MIN_LPRS: i64 = 15;

fn view_name(view: LprView) -> &'static str {
    match view {
        LprView::Low => "low",
        LprView::High => "high",
        LprView::HighNextSuccess => "high_next_success",
        LprView::HighNextFailure => "high_next_failure",
        LprView::HighNextRate => "high_next_rate",
    }
}

fn sort_value(field: LprSortField, r: &DefenseLpr) -> Option<f64> {
    match field {
        LprSortField::AvgOiXgf => r.avg_oi_xgf,
        LprSortField::AvgOiXga => r.avg_oi_xga,
        LprSortField::TotalOiXgf => r.total_oi_xgf,
        LprSortField::TotalOiXga => r.total_oi_xga,
        LprSortField::XgPct => r.xg_pct,
        LprSortField::Successes => r.successes.map(|v| v as f64),
        LprSortField::Failures => r.failures.map(|v| v as f64),
        LprSortField::SuccessRate => r.success_rate,
    }
}

/// The page's Total row: counts and xG summed, averages and percentages averaged
/// over the listed defensemen.
fn totals(rows: &[&DefenseLpr]) -> LprTotals {
    let sum =
        |f: fn(&DefenseLpr) -> Option<f64>| -> Option<f64> { rows.iter().map(|r| f(r)).sum() };
    let mean = |f: fn(&DefenseLpr) -> Option<f64>| sum(f).map(|s| s / rows.len() as f64);
    let count =
        |f: fn(&DefenseLpr) -> Option<i64>| -> Option<i64> { rows.iter().map(|r| f(r)).sum() };
    if rows.is_empty() {
        return LprTotals::default();
    }
    LprTotals {
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

/// The table for one view: defensemen meeting the minimums, sorted, with totals.
pub fn defense_lpr(store: &Store, q: LprQuery) -> LprTable {
    let mut rows: Vec<&DefenseLpr> = store
        .defense_lpr
        .get(view_name(q.view))
        .into_iter()
        .flatten()
        .filter(|r| r.games_played >= MIN_GAMES_PLAYED && r.lpr_count >= MIN_LPRS)
        .collect();

    let sort = q.sort.unwrap_or(match q.view {
        LprView::HighNextRate => LprSortField::SuccessRate,
        _ => LprSortField::XgPct,
    });
    let name = |r: &DefenseLpr| store.players.get(&r.player_id).map_or("", |p| &p.full_name);
    rows.sort_by(|a, b| {
        let by_field = match (sort_value(sort, a), sort_value(sort, b)) {
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

    LprTable {
        view: q.view,
        sort,
        dir: q.dir,
        min_games_played: MIN_GAMES_PLAYED,
        min_lprs: MIN_LPRS,
        totals: totals(&rows),
        rows: rows
            .iter()
            .map(|&stats| LprRow {
                full_name: name(stats).to_string(),
                stats: stats.clone(),
            })
            .collect(),
    }
}

pub async fn defense_lpr_handler(
    State(store): State<AppState>,
    Query(q): Query<LprQuery>,
) -> Json<LprTable> {
    Json(defense_lpr(&store, q))
}
