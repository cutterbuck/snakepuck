//! Sample Raw Data: a fixed 100-row sample of each table, 20 rows to a page.
//!
//! `/sample-data?table=games`. The rows come as stored; this page picks the columns,
//! their labels and how many decimals to show.

use leptos::prelude::*;
use leptos_meta::Title;
use serde_json::Value;

use super::fetch;
use super::layout::PageMessage;
use super::stats_table::{go_to, url_query};
use crate::types::{SampleQuery, SampleRows};

const PAGE_SIZE: usize = 20;

/// A column: its key in the rows, label, and decimals for numbers (`None`: as stored).
type Column = (&'static str, &'static str, Option<usize>);

/// Each table: (name in the URL and API, button label, columns). The first is the default.
const TABLES: [(&str, &str, &[Column]); 5] = [
    (
        "players",
        "Players",
        &[
            ("player_id", "Player ID", None),
            ("first_name", "First Name", None),
            ("last_name", "Last Name", None),
            ("handed", "Handed", None),
            ("birth_date", "Birth Date", None),
            ("position_group", "Position Group", None),
            ("primary_position", "Primary Position", None),
        ],
    ),
    (
        "games",
        "Games",
        &[
            ("game_id", "Game ID", None),
            ("game_date", "Game Date", None),
            ("league", "League", None),
            ("season", "Season", None),
            ("home_team_abbr", "Home Team", None),
            ("away_team_abbr", "Away Team", None),
            ("home_score", "Home Score", None),
            ("away_score", "Away Score", None),
            ("game_outcome", "Game Outcome", None),
            ("home_start_net", "Home Start Net", None),
        ],
    ),
    (
        "stints",
        "Stints",
        &[
            ("game_id", "Game ID", None),
            ("player_id", "Player ID", None),
            ("team_abbr", "Team", None),
            ("period", "Period", None),
            ("period_time_start", "Time Start", Some(2)),
            ("period_time_end", "Time End", Some(2)),
            ("game_stint", "Game Stint", None),
            ("n_home_skaters", "Home Skaters", None),
            ("n_away_skaters", "Away Skaters", None),
            ("is_home_net_empty", "Home Net Empty", None),
            ("is_away_net_empty", "Away Net Empty", None),
            ("home_score", "Home Score", None),
            ("away_score", "Away Score", None),
        ],
    ),
    (
        "events",
        "Events",
        &[
            ("game_id", "Game ID", None),
            ("player_id", "Player ID", None),
            ("period", "Period", None),
            ("period_time", "Time", Some(2)),
            ("event_type", "Event Type", None),
            ("outcome", "Outcome", None),
            ("flags", "Flags", None),
            ("team_abbr", "Team", None),
            ("opp_team_abbr", "Opp Team", None),
            ("description", "Description", None),
            ("detail", "Detail", None),
            ("xg", "xG", Some(3)),
            ("x", "X", Some(2)),
            ("y", "Y", Some(2)),
        ],
    ),
    (
        "tracking",
        "Tracking",
        &[
            ("game_id", "Game ID", None),
            ("sl_event_id", "SL Event ID", None),
            ("team_abbr", "Team", None),
            ("player_id", "Player ID", None),
            ("display_name", "Player Name", None),
            ("tracking_x", "Tracking X", Some(2)),
            ("tracking_y", "Tracking Y", Some(2)),
            ("tracking_vel_x", "Vel X", Some(2)),
            ("tracking_vel_y", "Vel Y", Some(2)),
        ],
    ),
];

/// Columns holding long ids, shown narrow and cut short.
const ID_COLUMNS: [&str; 3] = ["game_id", "player_id", "sl_event_id"];

#[component]
pub fn SampleDataPage() -> impl IntoView {
    let query = url_query::<SampleQuery>();
    // An unknown table shows the first.
    let table = Memo::new(move |_| {
        let name = query().table.unwrap_or_default();
        TABLES.iter().position(|t| t.0 == name).unwrap_or(0)
    });
    let rows = Resource::new(
        move || table.get(),
        |t| fetch::sample(TABLES[t].0.to_string()),
    );

    let go = go_to();
    let buttons = TABLES
        .iter()
        .enumerate()
        .map(|(i, &(name, label, _))| {
            let go = go.clone();
            let link = format!(
                "/sample-data{}",
                fetch::query_string(&SampleQuery {
                    table: (i > 0).then(|| name.to_string()),
                })
            );
            view! {
                <button
                    type="button"
                    class="btn"
                    class:btn-primary=move || table.get() == i
                    class:btn-outline-primary=move || table.get() != i
                    on:click=move |_| go(&link)
                >
                    {label}
                </button>
            }
        })
        .collect_view();

    view! {
        <Title text="HALO Project - Sample Raw Data" />
        <div class="container-fluid">
            <h2 class="mb-3">"Sample Data (Random 100 Rows)"</h2>
            <div class="btn-group mb-3" role="group">{buttons}</div>
            <Transition fallback=|| ()>
                {move || Suspend::new(async move {
                    let t = table.get_untracked();
                    match rows.await {
                        Ok(rows) => view! { <SampleTable rows columns=TABLES[t].2 /> }.into_any(),
                        Err(e) => view! { <PageMessage error=e /> }.into_any(),
                    }
                })}
            </Transition>
        </div>
    }
}

/// The rows, a page at a time (the page is the browser's alone, as on Dash).
#[component]
fn SampleTable(rows: SampleRows, columns: &'static [Column]) -> impl IntoView {
    let page = RwSignal::new(0usize);
    let pages = rows.len().div_ceil(PAGE_SIZE).max(1);
    let headers = columns
        .iter()
        .map(|&(key, label, _)| {
            view! { <th class:sample-id=ID_COLUMNS.contains(&key)>{label}</th> }
        })
        .collect_view();
    let body = move || {
        let start = page.get() * PAGE_SIZE;
        rows.iter()
            .skip(start)
            .take(PAGE_SIZE)
            .enumerate()
            .map(|(i, row)| {
                let cells = columns
                    .iter()
                    .map(|&(key, _, places)| {
                        let text = cell(row.get(key), places);
                        let title = text.clone();
                        view! {
                            <td class:sample-id=ID_COLUMNS.contains(&key) title=title>
                                {text}
                            </td>
                        }
                    })
                    .collect_view();
                view! { <tr class:lpr-alt=i % 2 == 1>{cells}</tr> }
            })
            .collect_view()
    };
    let at_first = move || page.get() == 0;
    let at_last = move || page.get() + 1 >= pages;
    view! {
        <div class="sample-scroll">
            <table class="sample-table">
                <thead>
                    <tr>{headers}</tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </div>
        <div class="sample-pager">
            <button
                type="button"
                class="btn btn-sm btn-outline-secondary"
                disabled=at_first
                on:click=move |_| page.update(|p| *p = p.saturating_sub(1))
            >
                "‹"
            </button>
            <span>{move || format!("{} / {pages}", page.get() + 1)}</span>
            <button
                type="button"
                class="btn btn-sm btn-outline-secondary"
                disabled=at_last
                on:click=move |_| page.update(|p| *p = (*p + 1).min(pages - 1))
            >
                "›"
            </button>
        </div>
    }
}

/// A value as shown: numbers to `places` decimals if given, nulls blank.
fn cell(v: Option<&Value>, places: Option<usize>) -> String {
    match (v, places) {
        (None | Some(Value::Null), _) => String::new(),
        (Some(Value::Number(n)), Some(places)) => n
            .as_f64()
            .map_or(n.to_string(), |f| format!("{f:.places$}")),
        (Some(Value::String(s)), _) => s.clone(),
        (Some(v), _) => v.to_string(),
    }
}
