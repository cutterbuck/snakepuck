//! Team Detail: one team-season's roster, skaters then goalies.
//!
//! `/team/<team_abbr>/<season>?situation=pp&sort=goals&dir=asc`: the season is in the
//! path, the table's view in the query (see `stats_table`). Changing season keeps it.

use leptos::prelude::*;
use leptos_meta::Title;
use leptos_router::hooks::use_params_map;

use super::fetch;
use super::layout::{PageMessage, row_link};
use super::stats_table::{
    go_to, options, situation_toggle, sort_headers, stat_cells, stat_cols, url_query,
};
use crate::types::{PageError, PlayerSeasonLine, SortField, TableQuery, TeamDetail};

fn href(team_abbr: &str, season: &str, t: &TableQuery) -> String {
    format!("/team/{team_abbr}/{season}{}", fetch::query_string(t))
}

#[component]
pub fn TeamDetailPage() -> impl IntoView {
    let params = use_params_map();
    let table = url_query::<TableQuery>();
    let team = Resource::new(
        move || {
            let p = params.read();
            let team_abbr = p.get("team_abbr").unwrap_or_default();
            (team_abbr, p.get("season").unwrap_or_default(), table())
        },
        |(team_abbr, season, t)| fetch::team(team_abbr, season, t),
    );

    view! {
        <div class="container-fluid">
            <Transition fallback=|| ()>
                {move || Suspend::new(async move {
                    match team.await {
                        Ok(t) => view! { <Loaded team=t /> }.into_any(),
                        Err(PageError::NotFound(_)) => view! {
                            <Title text="HALO Project - Team" />
                            <PageMessage error=PageError::NotFound("Team not found".into()) />
                            <a href="/team-standings">"Back to Team Standings"</a>
                        }
                        .into_any(),
                        Err(e) => view! { <PageMessage error=e /> }.into_any(),
                    }
                })}
            </Transition>
        </div>
    }
}

#[component]
fn Loaded(team: TeamDetail) -> impl IntoView {
    let TeamDetail {
        team_abbr,
        team_name,
        logo_url,
        season,
        seasons,
        situation,
        sort,
        dir,
        skaters,
        goalies,
        ..
    } = team;
    let current = TableQuery {
        situation,
        sort,
        dir,
    };

    let on_season = {
        let go = go_to();
        let (team_abbr, current) = (team_abbr.clone(), current.clone());
        move |ev| go(&href(&team_abbr, &event_target_value(&ev), &current))
    };
    let situations = situation_toggle(situation, |situation| {
        let t = TableQuery {
            situation,
            ..current.clone()
        };
        href(&team_abbr, &season, &t)
    });
    let headers = sort_headers(sort, dir, |sort, dir| {
        let t = TableQuery {
            sort,
            dir,
            ..current.clone()
        };
        href(&team_abbr, &season, &t)
    });

    // Striped straight through, with a rule between skaters and goalies.
    let skater_rows = skaters
        .iter()
        .enumerate()
        .map(|(i, r)| player_row(r, i, sort))
        .collect_view();
    let separator = (!skaters.is_empty() && !goalies.is_empty()).then(|| {
        view! {
            <tr class="roster-separator">
                <td colspan="19"></td>
            </tr>
        }
    });
    let goalie_rows = goalies
        .iter()
        .enumerate()
        .map(|(i, r)| player_row(r, skaters.len() + i, sort))
        .collect_view();

    view! {
        <Title text=format!("HALO Project - {team_name}") />
        <div class="breadcrumb-nav mb-2">
            <a href="/team-standings" class="breadcrumb-link">
                "Team Standings"
            </a>
            <span class="breadcrumb-sep">" / "</span>
            <span class="breadcrumb-current">{team_name.clone()}</span>
        </div>
        <div class="team-header mb-3 mt-1">
            <img src=logo_url alt="" width="48" height="48" />
            <span>{team_name}</span>
        </div>
        <div class="d-flex align-items-center mb-3">
            <label class="fw-bold me-2">"Season"</label>
            <select class="form-select" style="width: 200px" on:change=on_season>
                {options(seasons, &season)}
            </select>
        </div>
        {situations}
        <table class="stats-table">
            <colgroup>
                <col style="width: 180px" />
                {stat_cols()}
            </colgroup>
            <thead>
                <tr>
                    <th>"Name"</th>
                    {headers}
                </tr>
            </thead>
            <tbody>{skater_rows} {separator} {goalie_rows}</tbody>
        </table>
    }
}

fn player_row(r: &PlayerSeasonLine, i: usize, sorted_by: SortField) -> impl IntoView + use<> {
    let player_href = format!("/player/{}", r.player_id);
    let on_click = row_link(player_href.clone());
    view! {
        <tr class="game-log-row" class:stats-alt=i % 2 == 1 on:click=on_click>
            <td class="text-start">
                <a href=player_href class="team-link">
                    {r.full_name.clone()}
                </a>
            </td>
            {stat_cells(r, sorted_by)}
        </tr>
    }
}
