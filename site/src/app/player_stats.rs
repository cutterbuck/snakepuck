//! Player Stats: one league-season's players, 25 to a page.
//!
//! Every choice is in the URL (`?season=2023-24&situation=pp&sort=goals&page=2`) and is
//! sent to `/api/player-stats` as-is: the server sorts and pages, so each change is a
//! navigation and one request. Changing league or season resets the sort, as on Dash.

use leptos::prelude::*;
use leptos_meta::Title;
use leptos_router::NavigateOptions;
use leptos_router::hooks::{use_location, use_navigate};

use super::fetch;
use super::layout::{PageMessage, row_link};
use crate::types::{Dir, PlayerSeasonLine, PlayerStats, PlayerStatsQuery, Situation, SortField};

const SITUATIONS: [(Situation, &str); 5] = [
    (Situation::Tot, "All"),
    (Situation::Es, "Even Strength"),
    (Situation::Ev5, "5-on-5"),
    (Situation::Pp, "Power Play"),
    (Situation::Pk, "Short-Handed"),
];

/// The stat columns after Name and Team, in order.
const COLUMNS: [(SortField, &str); 18] = [
    (SortField::Age, "Age"),
    (SortField::Position, "Pos"),
    (SortField::GamesPlayed, "GP"),
    (SortField::Atoi, "ATOI"),
    (SortField::Goals, "G"),
    (SortField::Assists, "A"),
    (SortField::Points, "PTS"),
    (SortField::Shots, "S"),
    (SortField::ShootingPct, "S%"),
    (SortField::FaceoffsWon, "FOW"),
    (SortField::FaceoffsLost, "FOL"),
    (SortField::FaceoffPct, "FO%"),
    (SortField::Blocks, "BLK"),
    (SortField::Checks, "HIT"),
    (SortField::IXg, "ixG"),
    (SortField::OiXgf, "oixGF"),
    (SortField::OiXga, "oixGA"),
    (SortField::XgPct, "xG%"),
];

fn href(q: &PlayerStatsQuery) -> String {
    format!("/player-stats{}", fetch::query_string(q))
}

#[component]
pub fn PlayerStatsPage() -> impl IntoView {
    let search = use_location().search;
    // An unreadable URL (say, an unknown sort) shows the default table.
    let query = move || {
        let search = search.get();
        serde_urlencoded::from_str::<PlayerStatsQuery>(search.trim_start_matches('?'))
            .unwrap_or_default()
    };
    let stats = Resource::new(query, fetch::player_stats);

    view! {
        <Title text="HALO Project - Player Stats" />
        <div class="container-fluid">
            <h2 class="mb-3">"Player Stats"</h2>
            <Transition fallback=|| ()>
                {move || Suspend::new(async move {
                    match stats.await {
                        Ok(s) => view! { <Loaded stats=s /> }.into_any(),
                        Err(e) => view! { <PageMessage error=e /> }.into_any(),
                    }
                })}
            </Transition>
        </div>
    }
}

#[component]
fn Loaded(stats: PlayerStats) -> impl IntoView {
    // The query this page answers; links change one part of it.
    let current = PlayerStatsQuery {
        league: Some(stats.league.clone()),
        season: Some(stats.season.clone()),
        situation: stats.situation,
        sort: stats.sort,
        dir: stats.dir,
        page: None,
    };

    let mut leagues: Vec<String> = Vec::new();
    for s in &stats.seasons {
        if !leagues.contains(&s.league) {
            leagues.push(s.league.clone());
        }
    }
    let league_seasons: Vec<String> = stats
        .seasons
        .iter()
        .filter(|s| s.league == stats.league)
        .map(|s| s.season.clone())
        .collect();

    let navigate = use_navigate();
    let go = move |q: PlayerStatsQuery| {
        // Re-sorting or switching situation keeps the reader's place on the page.
        let options = NavigateOptions {
            scroll: false,
            ..Default::default()
        };
        navigate(&href(&q), options);
    };
    let on_league = {
        let go = go.clone();
        move |ev| {
            go(PlayerStatsQuery {
                league: Some(event_target_value(&ev)),
                ..Default::default()
            })
        }
    };
    let on_season = {
        let go = go.clone();
        let league = stats.league.clone();
        move |ev| {
            go(PlayerStatsQuery {
                league: Some(league.clone()),
                season: Some(event_target_value(&ev)),
                ..Default::default()
            })
        }
    };

    let situation_buttons = SITUATIONS
        .iter()
        .map(|&(situation, label)| {
            let go = go.clone();
            let q = PlayerStatsQuery {
                situation,
                ..current.clone()
            };
            view! {
                <button
                    type="button"
                    class:active=situation == stats.situation
                    on:click=move |_| go(q.clone())
                >
                    {label}
                </button>
            }
        })
        .collect_view();

    let headers = COLUMNS
        .iter()
        .map(|&(field, label)| {
            let go = go.clone();
            let active = field == stats.sort;
            // Click to sort descending; click the sorted column again to flip it.
            let dir = match (active, stats.dir) {
                (true, Dir::Desc) => Dir::Asc,
                _ => Dir::Desc,
            };
            let q = PlayerStatsQuery {
                sort: field,
                dir,
                ..current.clone()
            };
            let label = match (active, stats.dir) {
                (true, Dir::Desc) => format!("{label} ▼"),
                (true, Dir::Asc) => format!("{label} ▲"),
                _ => label.to_string(),
            };
            view! {
                <th class="sortable" class:active=active on:click=move |_| go(q.clone())>
                    {label}
                </th>
            }
        })
        .collect_view();

    let sorted_by = stats.sort;
    let rows = stats
        .rows
        .iter()
        .enumerate()
        .map(|(i, r)| player_row(r, i, sorted_by))
        .collect_view();

    view! {
        <div class="row mb-3">
            <div class="col-auto" style="width: 270px">
                <label class="fw-bold mb-1">"League"</label>
                <select class="form-select" on:change=on_league>
                    {options(leagues, &stats.league)}
                </select>
            </div>
            <div class="col-auto" style="min-width: 130px">
                <label class="fw-bold mb-1">"Season"</label>
                <select class="form-select" on:change=on_season>
                    {options(league_seasons, &stats.season)}
                </select>
            </div>
        </div>
        <div class="situation-toggle mb-3">
            <span class="situation-label">"Situation:"</span>
            <div class="situation-buttons">{situation_buttons}</div>
        </div>
        <table class="stats-table">
            <colgroup>
                <col style="width: 180px" />
                <col style="width: 90px" />
                {COLUMNS.iter().map(|_| view! { <col style="width: 60px" /> }).collect_view()}
            </colgroup>
            <thead>
                <tr>
                    <th>"Name"</th>
                    <th>"Team"</th>
                    {headers}
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <Pagination stats current />
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

fn player_row(r: &PlayerSeasonLine, i: usize, sorted_by: SortField) -> impl IntoView + use<> {
    let player_href = format!("/player/{}", r.player_id);
    let team_href = format!("/team/{}/{}", r.team_abbr, r.season);
    let s = &r.stats;
    let cells: [String; 18] = [
        r.age.to_string(),
        r.position.clone(),
        r.games_played.to_string(),
        mmss(s.atoi),
        s.goals.to_string(),
        s.assists.to_string(),
        s.points.to_string(),
        s.shots.to_string(),
        pct(s.shooting_pct),
        s.faceoffs_won.to_string(),
        s.faceoffs_lost.to_string(),
        pct(s.faceoff_pct),
        s.blocks.to_string(),
        s.checks.to_string(),
        format!("{:.2}", s.i_xg),
        format!("{:.2}", s.oi_xgf),
        format!("{:.2}", s.oi_xga),
        pct(s.xg_pct),
    ];
    let cells = COLUMNS
        .iter()
        .zip(cells)
        .map(|(&(field, _), v)| view! { <td class:active=field == sorted_by>{v}</td> })
        .collect_view();
    let on_click = row_link(player_href.clone());
    view! {
        <tr class="game-log-row" class:stats-alt=i % 2 == 1 on:click=on_click>
            <td class="text-start">
                <a href=player_href class="team-link">
                    {r.full_name.clone()}
                </a>
            </td>
            <td class="text-start text-nowrap">
                <a href=team_href class="team-link ps-team">
                    <img src=r.logo_url.clone() alt="" width="24" height="24" />
                    <span>{r.team_abbr.clone()}</span>
                </a>
            </td>
            {cells}
        </tr>
    }
}

/// Seconds as m:ss.
fn mmss(seconds: f64) -> String {
    let total = seconds as i64;
    format!("{}:{:02}", total / 60, total % 60)
}

fn pct(v: Option<f64>) -> String {
    v.map(|v| format!("{v:.3}")).unwrap_or_default()
}

/// Prev, the page numbers (the first, the last and two either side of this one), Next.
#[component]
fn Pagination(stats: PlayerStats, current: PlayerStatsQuery) -> impl IntoView {
    let pages = stats.total.div_ceil(stats.page_size).max(1);
    if pages == 1 {
        return ().into_any();
    }
    let page = stats.page;
    let link = |p: usize, label: String, class: &'static str| {
        let q = PlayerStatsQuery {
            page: (p > 1).then_some(p),
            ..current.clone()
        };
        view! {
            <a href=href(&q) class=class>
                {label}
            </a>
        }
        .into_any()
    };
    let disabled =
        |label: &str| view! { <span class="disabled">{label.to_string()}</span> }.into_any();

    let mut items = vec![match page > 1 {
        true => link(page - 1, "◀ Prev".into(), ""),
        false => disabled("◀ Prev"),
    }];
    let mut gap = false;
    for p in 1..=pages {
        if pages <= 7 || p.abs_diff(page) <= 2 || p == 1 || p == pages {
            items.push(link(
                p,
                p.to_string(),
                if p == page { "active" } else { "" },
            ));
            gap = false;
        } else if !gap {
            items.push(view! { <span class="gap">"..."</span> }.into_any());
            gap = true;
        }
    }
    items.push(match page < pages {
        true => link(page + 1, "Next ▶".into(), ""),
        false => disabled("Next ▶"),
    });

    let start = (page - 1) * stats.page_size + 1;
    let end = (page * stats.page_size).min(stats.total);
    view! {
        <div class="ps-pagination mt-3 mb-3">
            <div class="ps-pages">{items}</div>
            <span class="ps-showing">
                {format!("Showing {start}-{end} of {} players", stats.total)}
            </span>
        </div>
    }
    .into_any()
}
