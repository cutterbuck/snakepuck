//! Player Detail: a player's seasons and game log, in one situation.
//!
//! `/player/<player_id>?situation=pp`. Neither table sorts (as on Dash). A game log row
//! opens that game's report.

use leptos::prelude::*;
use leptos_meta::Title;
use leptos_router::hooks::use_params_map;

use super::fetch;
use super::layout::{PageMessage, row_link};
use super::stats_table::{game_cells, plain_headers, season_cells, situation_toggle, url_query};
use crate::types::{GameLogLine, PageError, PlayerDetail, PlayerSeasonLine, SituationQuery};

#[component]
pub fn PlayerDetailPage() -> impl IntoView {
    let params = use_params_map();
    let situation = url_query::<SituationQuery>();
    let player = Resource::new(
        move || {
            let player_id = params.read().get("player_id").unwrap_or_default();
            (player_id, situation())
        },
        |(player_id, q)| fetch::player(player_id, q),
    );

    view! {
        <div class="container-fluid">
            <Transition fallback=|| ()>
                {move || Suspend::new(async move {
                    match player.await {
                        Ok(p) => view! { <Loaded player=p /> }.into_any(),
                        Err(PageError::NotFound(_)) => view! {
                            <Title text="HALO Project - Player" />
                            <PageMessage error=PageError::NotFound("Player not found".into()) />
                            <a href="/player-stats">"Back to Player Stats"</a>
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
fn Loaded(player: PlayerDetail) -> impl IntoView {
    let PlayerDetail {
        player_id,
        full_name,
        position,
        latest_team,
        situation,
        seasons,
        games,
    } = player;

    let team_href = latest_team
        .as_ref()
        .map(|t| format!("/team/{}/{}", t.team.team_abbr, t.season));
    let breadcrumb_team = latest_team
        .as_ref()
        .zip(team_href.clone())
        .map(|(t, href)| {
            view! {
                <a href=href class="breadcrumb-link">
                    {t.team.team_name.clone()}
                </a>
                <span class="breadcrumb-sep">" / "</span>
            }
        });
    let logo = latest_team
        .as_ref()
        .zip(team_href.clone())
        .map(|(t, href)| {
            view! {
                <a href=href class="team-link">
                    <img src=t.team.logo_url.clone() alt="" width="48" height="48" />
                </a>
            }
        });
    // "  |  C | Hershey Bears", the parts there are.
    let mut info: Vec<AnyView> = Vec::new();
    if !position.is_empty() {
        info.push(view! { <span>{position}</span> }.into_any());
    }
    if let Some((t, href)) = latest_team.as_ref().zip(team_href) {
        info.push(
            view! {
                <a href=href class="team-link">
                    {t.team.team_name.clone()}
                </a>
            }
            .into_any(),
        );
    }
    let info = (!info.is_empty()).then(|| {
        let parts = info
            .into_iter()
            .enumerate()
            .map(|(i, part)| view! { {(i > 0).then_some(" | ")} {part} })
            .collect_view();
        view! { <span class="player-info">"  |  " {parts}</span> }
    });

    let situations = situation_toggle(situation, |situation| {
        let q = SituationQuery { situation };
        format!("/player/{player_id}{}", fetch::query_string(&q))
    });

    view! {
        <Title text=format!("HALO Project - {full_name}") />
        <div class="breadcrumb-nav mb-2">
            <a href="/team-standings" class="breadcrumb-link">
                "Team Standings"
            </a>
            <span class="breadcrumb-sep">" / "</span>
            {breadcrumb_team}
            <span class="breadcrumb-current">{full_name.clone()}</span>
        </div>
        <div class="team-header mb-3 mt-1">{logo} <span>{full_name}</span> {info}</div>
        {situations}
        <Seasons seasons />
        <GameLog player_id games />
    }
}

#[component]
fn Seasons(seasons: Vec<PlayerSeasonLine>) -> impl IntoView {
    if seasons.is_empty() {
        return view! { <div class="text-muted">"No stats available."</div> }.into_any();
    }
    let rows = seasons
        .iter()
        .enumerate()
        .map(|(i, r)| {
            // The season shows on its first row only.
            let first_of_season = i == 0 || seasons[i - 1].season != r.season;
            let season = first_of_season.then(|| r.season.clone());
            let team_href = format!("/team/{}/{}", r.team_abbr, r.season);
            view! {
                <tr class:stats-alt=i % 2 == 1>
                    <td>{season}</td>
                    <td class="text-start">
                        <a href=team_href class="team-link player-team">
                            <img src=r.logo_url.clone() alt="" width="24" height="24" />
                            <span>{r.team_name.clone()}</span>
                        </a>
                    </td>
                    {season_cells(r)}
                </tr>
            }
        })
        .collect_view();
    view! {
        <table class="stats-table">
            <colgroup>
                <col style="width: 80px" />
                <col style="width: 180px" />
                {(0..16).map(|_| view! { <col style="width: 60px" /> }).collect_view()}
            </colgroup>
            <thead>
                <tr>
                    <th>"Season"</th>
                    <th>"Team"</th>
                    <th>"GP"</th>
                    {plain_headers("ATOI")}
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    }
    .into_any()
}

#[component]
fn GameLog(player_id: String, games: Vec<GameLogLine>) -> impl IntoView {
    if games.is_empty() {
        return ().into_any();
    }
    let rows = games
        .iter()
        .enumerate()
        .map(|(i, g)| {
            let on_click = row_link(format!("/player/{player_id}/game/{}", g.game_id));
            view! {
                <tr class="game-log-row" class:stats-alt=i % 2 == 1 on:click=on_click>
                    <td class="text-nowrap">{g.game_date.clone()}</td>
                    <td class="text-start">
                        <div class="game-opponent">
                            <img src=g.team.logo_url.clone() alt="" width="24" height="24" />
                            <span>{if g.is_home { "vs." } else { "@" }}</span>
                            <img src=g.opponent.logo_url.clone() alt="" width="24" height="24" />
                            <span>{g.opponent.team_abbr.clone()}</span>
                        </div>
                    </td>
                    <td>{result(g)}</td>
                    {game_cells(&g.stats)}
                </tr>
            }
        })
        .collect_view();
    view! {
        <div class="mt-4">
            <h4>"Game Log"</h4>
            <table class="stats-table">
                <colgroup>
                    <col style="width: 110px" />
                    <col style="width: 160px" />
                    <col style="width: 90px" />
                    {(0..15).map(|_| view! { <col style="width: 60px" /> }).collect_view()}
                </colgroup>
                <thead>
                    <tr>
                        <th>"Date"</th>
                        <th>"Opp"</th>
                        <th>"Result"</th>
                        {plain_headers("TOI")}
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    }
    .into_any()
}

/// "W 4-2", "OTL 3-2": the winner's score first.
fn result(g: &GameLogLine) -> String {
    let (first, second) = match g.result.ends_with('W') {
        true => (g.team_score, g.opp_score),
        false => (g.opp_score, g.team_score),
    };
    format!("{} {first}-{second}", g.result)
}
