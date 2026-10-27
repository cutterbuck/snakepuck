//! Game Report: one player's game. Their stat line, their shifts by period, and the rink
//! for a chosen shift: a frame per event, played back at the pace the events happened.
//!
//! `/player/<player_id>/game/<game_id>?situation=pp&period=2&shift=5`. The frame shown
//! and playback are the browser's alone.

use std::collections::HashMap;
use std::time::Duration;

use leptos::prelude::*;
use leptos_meta::Title;
use leptos_router::hooks::use_params_map;

use super::fetch;
use super::layout::PageMessage;
use super::rink::{Rink, event_color, frame_markers};
use super::stats_table::{go_to, mmss, pct, situation_toggle, url_query};
use crate::types::{
    Frame, GameReport, GameReportQuery, PageError, Shift, ShiftDetail, SituationQuery, Stint,
};

/// Playback holds each frame for the real gap to the next event, within these bounds, so
/// quick sequences stay visible and stoppages don't stall it (as on Dash).
const MIN_FRAME_MS: f64 = 800.0;
const MAX_FRAME_MS: f64 = 3000.0;

const MONTHS: [&str; 12] = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
];

/// Which periods the shift table shows.
#[derive(Clone, Copy, PartialEq)]
enum Periods {
    All,
    One(i64),
}

#[component]
pub fn GameReportPage() -> impl IntoView {
    let params = use_params_map();
    let query = url_query::<GameReportQuery>();
    let ids = move || {
        let p = params.read();
        (
            p.get("game_id").unwrap_or_default(),
            p.get("player_id").unwrap_or_default(),
        )
    };
    let report = Resource::new(
        move || {
            (
                ids(),
                SituationQuery {
                    situation: query().situation,
                },
            )
        },
        |((game_id, player_id), q)| fetch::game_report(game_id, player_id, q),
    );
    let shift = Memo::new(move |_| query().shift);
    let detail = Resource::new(
        move || (ids(), shift.get()),
        |((game_id, player_id), shift)| async move {
            match shift {
                Some(n) => fetch::shift(game_id, player_id, n).await.map(Some),
                None => Ok(None),
            }
        },
    );

    // The rink's frame, and whether it's playing. A new shift starts at its first frame.
    let frame = RwSignal::new(0usize);
    let playing = RwSignal::new(false);
    Effect::new(move |_| {
        shift.track();
        frame.set(0);
        playing.set(false);
    });

    view! {
        <div class="container-fluid">
            <Transition fallback=|| ()>
                {move || Suspend::new(async move {
                    match report.await {
                        Ok(r) => view! { <Loaded report=r query=query() detail frame playing /> }
                            .into_any(),
                        Err(PageError::NotFound(_)) => view! {
                            <Title text="HALO Project - Game Report" />
                            <PageMessage error=PageError::NotFound("Game not found".into()) />
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

type Detail = Resource<Result<Option<ShiftDetail>, PageError>>;

#[component]
fn Loaded(
    report: GameReport,
    query: GameReportQuery,
    detail: Detail,
    frame: RwSignal<usize>,
    playing: RwSignal<bool>,
) -> impl IntoView {
    let r = &report;
    let base = format!("/player/{}/game/{}", r.player_id, r.game.game_id);
    let href = {
        let base = base.clone();
        move |q: &GameReportQuery| format!("{base}{}", fetch::query_string(q))
    };
    let (team, opponent) = match r.is_home {
        true => (&r.game.home, &r.game.away),
        false => (&r.game.away, &r.game.home),
    };
    let logos: HashMap<String, String> = [&r.game.home, &r.game.away]
        .into_iter()
        .map(|t| (t.team_abbr.clone(), t.logo_url.clone()))
        .collect();

    let selected = query.shift;
    let periods = match query.period.as_deref() {
        Some("all") => Periods::All,
        Some(p) => p.parse().map_or(Periods::All, Periods::One),
        None => selected
            .and_then(|n| r.shifts.iter().find(|s| s.shift == n))
            .map(|s| s.period)
            .or(r.periods.first().copied())
            .map_or(Periods::All, Periods::One),
    };

    let situations = situation_toggle(r.situation, |situation| {
        href(&GameReportQuery {
            situation,
            ..query.clone()
        })
    });

    view! {
        <Title text=format!("HALO Project - {} Game Report", r.full_name) />
        <div class="breadcrumb-nav mb-2">
            <a href="/team-standings" class="breadcrumb-link">
                "Team Standings"
            </a>
            <span class="breadcrumb-sep">" / "</span>
            <a href=format!("/team/{}/{}", team.team_abbr, r.game.season) class="breadcrumb-link">
                {team.team_name.clone()}
            </a>
            <span class="breadcrumb-sep">" / "</span>
            <a href=format!("/player/{}", r.player_id) class="breadcrumb-link">
                {r.full_name.clone()}
            </a>
            <span class="breadcrumb-sep">" / "</span>
            <span class="breadcrumb-current">"Game Report"</span>
        </div>
        <div class="game-header mb-3 mt-1">
            <span class="game-header-name">{r.full_name.clone()}</span>
            <span class="game-header-sep">"|"</span>
            <img src=team.logo_url.clone() alt="" width="24" height="24" />
            <span>{if r.is_home { "vs." } else { "@" }}</span>
            <img src=opponent.logo_url.clone() alt="" width="24" height="24" />
            <span>{opponent.team_abbr.clone()}</span>
            <span class="game-header-sep">"|"</span>
            <span>{result(r)}</span>
            <span class="game-header-sep">"|"</span>
            <span class="text-muted">{long_date(&r.game.game_date)}</span>
        </div>
        {situations}
        {stat_line(r)}
        <ShiftTable report=report.clone() query=query.clone() periods href=href.clone() detail frame />
        <RinkSection report detail frame playing logos />
    }
}

/// "W 4-2", "OTL 3-2": the winner's score first.
fn result(r: &GameReport) -> String {
    let (first, second) = match r.result.ends_with('W') {
        true => (r.team_score, r.opp_score),
        false => (r.opp_score, r.team_score),
    };
    format!("{} {first}-{second}", r.result)
}

/// 2023-10-14 as "October 14, 2023".
fn long_date(date: &str) -> String {
    let mut parts = date.split('-').map(|p| p.parse::<usize>().ok());
    match (parts.next(), parts.next(), parts.next()) {
        (Some(Some(y)), Some(Some(m @ 1..=12)), Some(Some(d))) => {
            format!("{} {d:02}, {y}", MONTHS[m - 1])
        }
        _ => date.to_string(),
    }
}

fn stat_line(r: &GameReport) -> impl IntoView + use<> {
    let s = &r.stats;
    let cells = [
        ("TOI", mmss(s.toi)),
        ("G", s.goals.to_string()),
        ("A", s.assists.to_string()),
        ("PTS", s.points.to_string()),
        ("S", s.shots.to_string()),
        ("S%", pct(s.shooting_pct)),
        ("FOW", s.faceoffs_won.to_string()),
        ("FOL", s.faceoffs_lost.to_string()),
        ("FO%", pct(s.faceoff_pct)),
        ("PIM", r.penalties.to_string()),
        ("PD", r.penalties_drawn.to_string()),
        ("BLK", s.blocks.to_string()),
        ("HIT", s.checks.to_string()),
        ("ixG", format!("{:.2}", s.i_xg)),
        ("oixGF", format!("{:.2}", s.oi_xgf)),
        ("oixGA", format!("{:.2}", s.oi_xga)),
    ];
    let headers = cells
        .iter()
        .map(|(h, _)| view! { <th>{*h}</th> })
        .collect_view();
    let values = cells
        .into_iter()
        .map(|(_, v)| view! { <td>{v}</td> })
        .collect_view();
    view! {
        <div class="mt-3">
            <table class="stats-table">
                <thead>
                    <tr>{headers}</tr>
                </thead>
                <tbody>
                    <tr>{values}</tr>
                </tbody>
            </table>
        </div>
    }
}

/// The player's shifts in the chosen period. A click puts a shift on the rink (or takes
/// it off); a shift of several stints then lists them, and a stint jumps the rink to it.
#[component]
fn ShiftTable(
    report: GameReport,
    query: GameReportQuery,
    periods: Periods,
    href: impl Fn(&GameReportQuery) -> String + Clone + Send + 'static,
    detail: Detail,
    frame: RwSignal<usize>,
) -> impl IntoView {
    let go = go_to();
    let period_buttons = report
        .periods
        .iter()
        .map(|&p| {
            let active = periods == Periods::One(p);
            // Clicking the shown period shows them all.
            let q = GameReportQuery {
                period: Some(if active { "all".into() } else { p.to_string() }),
                ..query.clone()
            };
            let (go, link) = (go.clone(), href(&q));
            view! {
                <button type="button" class:active=active on:click=move |_| go(&link)>
                    {if p >= 4 { "OT".to_string() } else { p.to_string() }}
                </button>
            }
        })
        .collect_view();

    let shifts: Vec<&Shift> = report
        .shifts
        .iter()
        .filter(|s| periods == Periods::All || periods == Periods::One(s.period))
        .collect();
    let rows = shifts
        .iter()
        .enumerate()
        .map(|(i, s)| {
            let is_selected = query.shift == Some(s.shift);
            let q = GameReportQuery {
                shift: (!is_selected).then_some(s.shift),
                ..query.clone()
            };
            let (go, link) = (go.clone(), href(&q));
            let stints: Vec<Stint> = report
                .stints
                .iter()
                .filter(|st| st.shift == Some(s.shift))
                .cloned()
                .collect();
            let sub_rows =
                (is_selected && stints.len() > 1).then(|| stint_rows(stints, detail, frame));
            view! {
                <tr
                    class="stint-row"
                    class:selected=is_selected
                    class:stats-alt=i % 2 == 1
                    on:click=move |_| go(&link)
                >
                    <td>{s.shift}</td>
                    <td>{mmss(s.toi)}</td>
                    <td>{mmss(s.period_time_start)}</td>
                    <td>{mmss(s.period_time_end)}</td>
                    <td>{s.n_home_skaters}</td>
                    <td>{s.n_away_skaters}</td>
                    <td>{yes_no(s.is_home_net_empty)}</td>
                    <td>{yes_no(s.is_away_net_empty)}</td>
                    <td>{format!("{}-{}", s.home_score, s.away_score)}</td>
                    <td>{format!("{:.2}", s.i_xg)}</td>
                    <td>{format!("{:.2}", s.oi_xgf)}</td>
                    <td>{format!("{:.2}", s.oi_xga)}</td>
                </tr>
                {sub_rows}
            }
        })
        .collect_view();

    let table = match shifts.is_empty() {
        true => view! { <div class="text-muted">"No shifts found."</div> }.into_any(),
        false => view! {
            <div class="stints-scroll-container" style="max-height: 335px; overflow-x: auto">
                <table class="stats-table shift-table">
                    <thead>
                        <tr>
                            <th>"Shift"</th>
                            <th>"TOI"</th>
                            <th>"Start"</th>
                            <th>"End"</th>
                            <th>"Home Skaters"</th>
                            <th>"Away Skaters"</th>
                            <th>"Home Net Empty"</th>
                            <th>"Away Net Empty"</th>
                            <th>"Score"</th>
                            <th>"ixG"</th>
                            <th>"oixGF"</th>
                            <th>"oixGA"</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        }
        .into_any(),
    };

    view! {
        <div class="shifts-header">
            <h4>"Shifts"</h4>
            <span class="situation-label">"Period:"</span>
            <div class="situation-buttons">{period_buttons}</div>
        </div>
        {table}
    }
}

fn yes_no(b: bool) -> &'static str {
    if b { "Yes" } else { "No" }
}

/// A selected shift's stints. A click jumps the rink to the frame nearest the stint's start.
fn stint_rows(stints: Vec<Stint>, detail: Detail, frame: RwSignal<usize>) -> impl IntoView {
    stints
        .into_iter()
        .enumerate()
        .map(|(i, st)| {
            let start = st.period_time_start;
            let jump = move |ev: leptos::ev::MouseEvent| {
                ev.stop_propagation(); // not a click on the shift's row
                if let Some(Ok(Some(d))) = detail.get_untracked() {
                    frame.set(nearest_frame(&d.frames, start));
                }
            };
            view! {
                <tr class="stint-row stint-sub" on:click=jump>
                    <td>{format!("Stint {}", i + 1)}</td>
                    <td>{mmss(st.toi)}</td>
                    <td>{mmss(st.period_time_start)}</td>
                    <td>{mmss(st.period_time_end)}</td>
                    <td>{st.n_home_skaters}</td>
                    <td>{st.n_away_skaters}</td>
                    <td>{yes_no(st.is_home_net_empty)}</td>
                    <td>{yes_no(st.is_away_net_empty)}</td>
                    <td>{format!("{}-{}", st.home_score, st.away_score)}</td>
                    <td>{format!("{:.2}", st.i_xg)}</td>
                    <td>{format!("{:.2}", st.oi_xgf)}</td>
                    <td>{format!("{:.2}", st.oi_xga)}</td>
                </tr>
            }
        })
        .collect_view()
}

/// The frame whose event is closest in time to `period_time`.
fn nearest_frame(frames: &[Frame], period_time: f64) -> usize {
    frames
        .iter()
        .enumerate()
        .min_by(|(_, a), (_, b)| {
            let (da, db) = (
                (a.event.period_time - period_time).abs(),
                (b.event.period_time - period_time).abs(),
            );
            da.total_cmp(&db)
        })
        .map_or(0, |(i, _)| i)
}

#[component]
fn RinkSection(
    report: GameReport,
    detail: Detail,
    frame: RwSignal<usize>,
    playing: RwSignal<bool>,
    logos: HashMap<String, String>,
) -> impl IntoView {
    let center_logo = report.game.home.logo_url.clone();
    let no_tracking = (!report.has_tracking).then(|| {
        view! {
            <div class="text-muted small mt-1">
                "HALO has no tracking for this game, so the rink shows events only."
            </div>
        }
    });
    view! {
        <Transition fallback=|| ()>
            {move || {
                let (center_logo, logos) = (center_logo.clone(), logos.clone());
                Suspend::new(async move {
                    match detail.await {
                        Ok(Some(d)) if !d.frames.is_empty() => {
                            view! { <ShiftRink detail=d frame playing center_logo logos /> }.into_any()
                        }
                        Ok(Some(_)) => view! {
                            <div class="text-muted mt-2">"No events in this shift."</div>
                            <div class="rink-row mt-3">
                                <Rink center_logo />
                            </div>
                        }
                        .into_any(),
                        Ok(None) => view! {
                            <div class="text-muted mt-2">"Select a shift to see it on the rink."</div>
                            <div class="rink-row mt-3">
                                <Rink center_logo />
                            </div>
                        }
                        .into_any(),
                        Err(e) => view! { <div class="text-muted mt-2">{e.to_string()}</div> }.into_any(),
                    }
                })
            }}
        </Transition>
        {no_tracking}
    }
}

/// The rink for one shift, with Play/Pause and a frame slider marked at the stints'
/// boundaries.
#[component]
fn ShiftRink(
    detail: ShiftDetail,
    frame: RwSignal<usize>,
    playing: RwSignal<bool>,
    center_logo: String,
    logos: HashMap<String, String>,
) -> impl IntoView {
    let ShiftDetail { stints, frames, .. } = detail;
    let last = frames.len() - 1;
    let delays: Vec<u64> = frames
        .windows(2)
        .map(|w| {
            let gap_ms = (w[1].event.period_time - w[0].event.period_time).max(0.0) * 1000.0;
            gap_ms.clamp(MIN_FRAME_MS, MAX_FRAME_MS) as u64
        })
        .collect();

    // Advance one frame after the current one's delay, until the last.
    Effect::new(move |_| {
        if !playing.get() {
            return;
        }
        let i = frame.get();
        if i >= last {
            playing.set(false);
            return;
        }
        let advance = move || frame.set(i + 1);
        if let Ok(handle) = set_timeout_with_handle(advance, Duration::from_millis(delays[i])) {
            on_cleanup(move || handle.clear());
        }
    });
    let toggle = move |_| {
        if !playing.get_untracked() && frame.get_untracked() >= last {
            frame.set(0); // play again from the start
        }
        playing.update(|p| *p = !*p);
    };

    // Stint boundaries on the slider: the shift's start and end pinned to its ends, and
    // the stints' other boundaries at the frame nearest each, leaving out any too close
    // to one already shown to read.
    const MIN_GAP_PCT: f64 = 4.0;
    let left = |i: usize| {
        if last == 0 {
            0.0
        } else {
            100.0 * i as f64 / last as f64
        }
    };
    let mut marks: Vec<(f64, f64)> = Vec::new();
    if let (Some(first), Some(end)) = (stints.first(), stints.last()) {
        let (start, end) = (first.period_time_start, end.period_time_end);
        marks.push((0.0, start));
        let mut inner: Vec<(f64, f64)> = stints
            .iter()
            .flat_map(|st| [st.period_time_start, st.period_time_end])
            .filter(|&t| t != start && t != end)
            .map(|t| (left(nearest_frame(&frames, t)), t))
            .collect();
        inner.sort_by(|a, b| a.0.total_cmp(&b.0));
        for (pct, t) in inner {
            let clear_of_last = pct - marks.last().map_or(0.0, |m| m.0) >= MIN_GAP_PCT;
            if clear_of_last && 100.0 - pct >= MIN_GAP_PCT {
                marks.push((pct, t));
            }
        }
        marks.push((100.0, end));
    }
    let marks = marks
        .into_iter()
        .map(|(left, t)| {
            view! {
                <span class="slider-mark" style=format!("left: {left:.2}%")>
                    {mmss(t)}
                </span>
            }
        })
        .collect_view();

    let frames = std::sync::Arc::new(frames);
    let current = {
        let frames = frames.clone();
        move || frames[frame.get().min(last)].clone()
    };
    let time = {
        let current = current.clone();
        move || mmss(current().event.period_time)
    };
    let markers = {
        let current = current.clone();
        move || {
            let logos = logos.clone();
            frame_markers(&current(), move |team| {
                logos.get(team).cloned().unwrap_or_default()
            })
        }
    };
    let legend = move || {
        let e = current().event;
        e.x.is_some().then(|| {
            view! {
                <div class="rink-legend-item">
                    <span class="rink-legend-dot" style=format!("background: {}", event_color(&e.event_type))></span>
                    {e.event_type}
                </div>
            }
        })
    };

    view! {
        <div class="playback-controls">
            <button type="button" class="btn btn-info btn-sm playback-button" on:click=toggle>
                {move || if playing.get() { "Pause" } else { "Play" }}
            </button>
            <div class="playback-slider">
                <input
                    type="range"
                    class="form-range"
                    min=0
                    max=last
                    step=1
                    prop:value=move || frame.get()
                    on:input=move |ev| frame.set(event_target_value(&ev).parse().unwrap_or(0))
                />
                <div class="slider-marks">{marks}</div>
            </div>
            <span class="playback-time">{time}</span>
        </div>
        <div class="rink-row mt-3">
            <Rink center_logo>{markers}</Rink>
            <div class="rink-legend">{legend}</div>
        </div>
    }
}
