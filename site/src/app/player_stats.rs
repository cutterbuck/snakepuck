//! Player Stats: one league-season's players, 25 to a page.
//!
//! Every choice is in the URL (`?season=2023-24&situation=pp&sort=goals&page=2`) and is
//! sent to `/api/player-stats` as-is: the server sorts and pages, so each change is a
//! navigation and one request. Changing league or season resets the sort, as on Dash.

use leptos::prelude::*;
use leptos_meta::Title;

use super::fetch;
use super::layout::{PageMessage, row_link};
use super::stats_table::{
    go_to, options, situation_toggle, sort_headers, stat_cells, stat_cols, url_query,
};
use crate::types::{PlayerSeasonLine, PlayerStats, PlayerStatsQuery, SortField};

fn href(q: &PlayerStatsQuery) -> String {
    format!("/player-stats{}", fetch::query_string(q))
}

#[component]
pub fn PlayerStatsPage() -> impl IntoView {
    let stats = Resource::new(url_query::<PlayerStatsQuery>(), fetch::player_stats);

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

    let go = go_to();
    let on_league = {
        let go = go.clone();
        move |ev| {
            go(&href(&PlayerStatsQuery {
                league: Some(event_target_value(&ev)),
                ..Default::default()
            }))
        }
    };
    let on_season = {
        let league = stats.league.clone();
        move |ev| {
            go(&href(&PlayerStatsQuery {
                league: Some(league.clone()),
                season: Some(event_target_value(&ev)),
                ..Default::default()
            }))
        }
    };

    let situations = situation_toggle(stats.situation, |situation| {
        href(&PlayerStatsQuery {
            situation,
            ..current.clone()
        })
    });
    let headers = sort_headers(stats.sort, stats.dir, |sort, dir| {
        href(&PlayerStatsQuery {
            sort,
            dir,
            ..current.clone()
        })
    });
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
        {situations}
        <table class="stats-table">
            <colgroup>
                <col style="width: 180px" />
                <col style="width: 90px" />
                {stat_cols()}
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

fn player_row(r: &PlayerSeasonLine, i: usize, sorted_by: SortField) -> impl IntoView + use<> {
    let player_href = format!("/player/{}", r.player_id);
    let team_href = format!("/team/{}/{}", r.team_abbr, r.season);
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
            {stat_cells(r, sorted_by)}
        </tr>
    }
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
