//! Team Standings: one league-season, by division or as one league table.
//!
//! The league and season are in the URL (`?league=AHL&season=2023-24`), so the server
//! renders the chosen table and links can be shared. The view and the sort are local:
//! the whole table is already loaded. Changing league or season resets the sort.

use leptos::prelude::*;
use leptos_meta::Title;
use leptos_router::hooks::{use_navigate, use_query_map};

use super::fetch;
use super::layout::PageMessage;
use crate::types::{Standings, StandingsRow, TeamSeason};

/// Division order on the page; any others follow, as the data has them.
const DIVISIONS: [&str; 4] = ["Atlantic", "North", "Central", "Pacific"];

#[derive(Clone, Copy, PartialEq)]
enum View {
    Division,
    League,
}

#[derive(Clone, Copy, PartialEq)]
enum Column {
    Gp,
    W,
    L,
    Otl,
    Pts,
    PtsPct,
    Rw,
    Row,
    Gf,
    Ga,
    Diff,
}

impl Column {
    const ALL: [Self; 11] = [
        Self::Gp,
        Self::W,
        Self::L,
        Self::Otl,
        Self::Pts,
        Self::PtsPct,
        Self::Rw,
        Self::Row,
        Self::Gf,
        Self::Ga,
        Self::Diff,
    ];

    fn label(self) -> &'static str {
        match self {
            Self::Gp => "GP",
            Self::W => "W",
            Self::L => "L",
            Self::Otl => "OTL",
            Self::Pts => "PTS",
            Self::PtsPct => "P%",
            Self::Rw => "RW",
            Self::Row => "ROW",
            Self::Gf => "GF",
            Self::Ga => "GA",
            Self::Diff => "DIFF",
        }
    }

    fn value(self, s: &TeamSeason) -> f64 {
        match self {
            Self::Gp => s.games_played as f64,
            Self::W => s.wins as f64,
            Self::L => s.losses as f64,
            Self::Otl => s.ot_losses as f64,
            Self::Pts => s.points as f64,
            Self::PtsPct => s.points_percentage,
            Self::Rw => s.regulation_wins as f64,
            Self::Row => s.regulation_or_ot_wins as f64,
            Self::Gf => s.goals_forward as f64,
            Self::Ga => s.goals_against as f64,
            Self::Diff => s.goal_diff as f64,
        }
    }

    fn cell(self, s: &TeamSeason) -> String {
        match self {
            Self::PtsPct => format!("{:.3}", s.points_percentage),
            _ => self.value(s).to_string(),
        }
    }
}

#[derive(Clone, Copy, PartialEq)]
struct Sort {
    column: Column,
    descending: bool,
}

const DEFAULT_SORT: Sort = Sort {
    column: Column::Pts,
    descending: true,
};

#[component]
pub fn StandingsPage() -> impl IntoView {
    let query = use_query_map();
    let standings = Resource::new(
        move || {
            let q = query.read();
            (q.get("league"), q.get("season"))
        },
        |(league, season)| fetch::standings(league, season),
    );
    let view = RwSignal::new(View::Division);

    view! {
        <Title text="HALO Project - Team Standings" />
        <div class="container-fluid">
            <h2 class="mb-3">"Team Standings"</h2>
            // Transition, not Suspense: keep the current table up while the next loads.
            <Transition fallback=|| ()>
                {move || Suspend::new(async move {
                    match standings.await {
                        Ok(s) => view! { <Loaded standings=s view /> }.into_any(),
                        Err(e) => view! { <PageMessage error=e /> }.into_any(),
                    }
                })}
            </Transition>
        </div>
    }
}

/// The controls and the table, for one loaded league-season.
#[component]
fn Loaded(standings: Standings, view: RwSignal<View>) -> impl IntoView {
    let Standings {
        league,
        season,
        seasons,
        rows,
    } = standings;
    let sort = RwSignal::new(DEFAULT_SORT);

    let mut leagues: Vec<String> = Vec::new();
    for s in &seasons {
        if !leagues.contains(&s.league) {
            leagues.push(s.league.clone());
        }
    }
    let league_seasons: Vec<String> = seasons
        .iter()
        .filter(|s| s.league == league)
        .map(|s| s.season.clone())
        .collect();

    let navigate = use_navigate();
    let go = move |league: &str, season: Option<&str>| {
        let query = fetch::query(&[("league", Some(league)), ("season", season)]);
        navigate(&format!("/team-standings{query}"), Default::default());
    };
    let on_league = {
        let go = go.clone();
        move |ev| go(&event_target_value(&ev), None)
    };
    let on_season = {
        let league = league.clone();
        move |ev| go(&league, Some(&event_target_value(&ev)))
    };

    view! {
        <div class="row mb-3">
            <div class="col-auto" style="width: 270px">
                <label class="fw-bold mb-1">"League"</label>
                <select class="form-select" on:change=on_league>
                    {options(leagues, &league)}
                </select>
            </div>
            <div class="col-auto" style="min-width: 130px">
                <label class="fw-bold mb-1">"Season"</label>
                <select class="form-select" on:change=on_season>
                    {options(league_seasons, &season)}
                </select>
            </div>
            <div class="col-auto">
                <label class="fw-bold mb-1 d-block">"View"</label>
                <div class="btn-group" role="group">
                    <ViewButton label="Division" this=View::Division view />
                    <ViewButton label="League" this=View::League view />
                </div>
            </div>
        </div>
        <Table rows season sort view />
    }
}

fn options(values: Vec<String>, selected: &str) -> impl IntoView + use<> {
    values
        .into_iter()
        .map(|v| {
            let is_selected = v == selected;
            let label = v.clone();
            view! { <option value=v selected=is_selected>{label}</option> }
        })
        .collect_view()
}

#[component]
fn ViewButton(label: &'static str, this: View, view: RwSignal<View>) -> impl IntoView {
    view! {
        <button
            type="button"
            class="btn"
            class:btn-info=move || view.get() == this
            class:btn-outline-info=move || view.get() != this
            on:click=move |_| view.set(this)
        >
            {label}
        </button>
    }
}

#[component]
fn Table(
    rows: Vec<StandingsRow>,
    season: String,
    sort: RwSignal<Sort>,
    view: RwSignal<View>,
) -> impl IntoView {
    let body = move || {
        let Sort { column, descending } = sort.get();
        let mut rows = rows.clone();
        // Stable, so ties keep the server's order (points, then RW, ROW and W).
        rows.sort_by(|a, b| {
            let order = column.value(&a.stats).total_cmp(&column.value(&b.stats));
            if descending { order.reverse() } else { order }
        });
        match view.get() {
            View::League => rows
                .iter()
                .enumerate()
                .map(|(i, r)| team_row(r, i, &season, column))
                .collect_view()
                .into_any(),
            View::Division => by_division(rows)
                .into_iter()
                .map(|(division, rows)| {
                    view! {
                        <tr>
                            <td class="standings-division" colspan=Column::ALL.len() + 2>
                                {format!("{division} Division")}
                            </td>
                        </tr>
                        {rows
                            .iter()
                            .enumerate()
                            .map(|(i, r)| team_row(r, i, &season, column))
                            .collect_view()}
                    }
                })
                .collect_view()
                .into_any(),
        }
    };

    view! {
        <table class="standings-table">
            <colgroup>
                <col style="width: 260px" />
                {Column::ALL.iter().map(|_| view! { <col style="width: 60px" /> }).collect_view()}
                <col style="width: 60px" />
            </colgroup>
            <thead>
                <tr>
                    <th>"Team"</th>
                    {Column::ALL.iter().map(|&c| view! { <SortHeader column=c sort /> }).collect_view()}
                    <th>"SO"</th>
                </tr>
            </thead>
            <tbody>{body}</tbody>
        </table>
    }
}

/// Click to sort by this column, descending; click again to flip it.
#[component]
fn SortHeader(column: Column, sort: RwSignal<Sort>) -> impl IntoView {
    let active = move || sort.get().column == column;
    let label = move || match sort.get() {
        Sort {
            column: c,
            descending,
        } if c == column => {
            format!("{} {}", column.label(), if descending { "▼" } else { "▲" })
        }
        _ => column.label().to_string(),
    };
    let on_click = move |_| {
        sort.update(|s| {
            *s = match *s {
                Sort {
                    column: c,
                    descending,
                } if c == column => Sort {
                    column,
                    descending: !descending,
                },
                _ => Sort {
                    column,
                    descending: true,
                },
            }
        })
    };
    view! {
        <th class="sortable" class:active=active on:click=on_click>
            {label}
        </th>
    }
}

/// Rows grouped by division: the known divisions in order, then any others.
fn by_division(rows: Vec<StandingsRow>) -> Vec<(String, Vec<StandingsRow>)> {
    let mut groups: Vec<(String, Vec<StandingsRow>)> = Vec::new();
    for r in rows {
        let division = match r.division.as_str() {
            "" => "Other".to_string(),
            d => d.to_string(),
        };
        match groups.iter_mut().find(|(d, _)| *d == division) {
            Some((_, rows)) => rows.push(r),
            None => groups.push((division, vec![r])),
        }
    }
    let rank = |d: &str| {
        DIVISIONS
            .iter()
            .position(|&k| k == d)
            .unwrap_or(DIVISIONS.len())
    };
    groups.sort_by_key(|(d, _)| rank(d));
    groups
}

fn team_row(r: &StandingsRow, i: usize, season: &str, sorted_by: Column) -> impl IntoView + use<> {
    let href = format!("/team/{}/{season}", r.stats.team_abbr);
    let navigate = use_navigate();
    let row_href = href.clone();
    let s = &r.stats;
    view! {
        <tr
            class="game-log-row"
            class:standings-alt=i % 2 == 1
            on:click=move |_| navigate(&row_href, Default::default())
        >
            <td class="standings-team">
                <a href=href class="team-link">
                    <img src=r.logo_url.clone() alt="" width="32" height="32" />
                    <span>{r.team_name.clone()}</span>
                </a>
            </td>
            {Column::ALL.iter().map(|&c| view! { <td class:active=c == sorted_by>{c.cell(s)}</td> })
                .collect_view()}
            <td>{s.so_record.clone()}</td>
        </tr>
    }
}
