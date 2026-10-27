//! Player Analysis: forwards (coming soon), and the defensemen loose-puck-recovery (LPR)
//! table in five views.
//!
//! `/player-analysis?view=low&sort=avg_oi_xgf&dir=asc`: the server sorts, so each choice
//! is a navigation. Changing view resets the sort, to the view's own default.

use leptos::prelude::*;
use leptos_meta::Title;

use super::fetch;
use super::layout::PageMessage;
use super::stats_table::{go_to, url_query};
use crate::types::{Dir, LprQuery, LprSortField, LprTable, LprView};

const VIEWS: [(LprView, &str); 5] = [
    (LprView::Low, "Total Low Pressure Loose Puck Recovery"),
    (LprView::High, "Total High Pressure Loose Puck Recovery"),
    (LprView::HighNextSuccess, "HiPressLPR Next Play Success"),
    (LprView::HighNextFailure, "HiPressLPR Next Play Failure"),
    (LprView::HighNextRate, "HiPress LPR Next Play Success Rate"),
];

fn href(q: &LprQuery) -> String {
    format!("/player-analysis{}", fetch::query_string(q))
}

/// The value a `<select>` option carries for a view: its name in the URL.
fn view_value(view: LprView) -> String {
    serde_json::to_value(view)
        .ok()
        .and_then(|v| v.as_str().map(String::from))
        .unwrap_or_default()
}

#[component]
pub fn PlayerAnalysisPage() -> impl IntoView {
    let table = Resource::new(url_query::<LprQuery>(), fetch::defense_lpr);
    view! {
        <Title text="HALO Project - Player Analysis" />
        <div class="container-fluid">
            <div class="mb-5">
                <h4 class="mb-3">"Forwards"</h4>
                <p class="text-muted">"Coming soon."</p>
            </div>
            <h4 class="mb-3">"Defensemen"</h4>
            <Transition fallback=|| ()>
                {move || Suspend::new(async move {
                    match table.await {
                        Ok(t) => view! { <Loaded table=t /> }.into_any(),
                        Err(e) => view! { <PageMessage error=e /> }.into_any(),
                    }
                })}
            </Transition>
        </div>
    }
}

#[component]
fn Loaded(table: LprTable) -> impl IntoView {
    let go = go_to();
    let on_view = {
        let go = go.clone();
        move |ev| {
            let value = event_target_value(&ev);
            let view = VIEWS
                .iter()
                .map(|&(v, _)| v)
                .find(|&v| view_value(v) == value)
                .unwrap_or_default();
            go(&href(&LprQuery {
                view,
                ..Default::default()
            }))
        }
    };
    let options = VIEWS
        .iter()
        .map(|&(v, label)| {
            view! {
                <option value=view_value(v) selected=v == table.view>
                    {label}
                </option>
            }
        })
        .collect_view();

    let minimums = format!(
        "5-on-5, min. {} GP, min. {} LPRs",
        table.min_games_played, table.min_lprs
    );
    let subtitle = match table.view {
        LprView::HighNextSuccess => format!(
            "Expected goals after high-pressure LPRs where the defenseman's next play within 5s was successful ({minimums})"
        ),
        LprView::HighNextFailure => format!(
            "Expected goals after high-pressure LPRs where the defenseman had no successful next play within 5s ({minimums})"
        ),
        LprView::HighNextRate => {
            format!("Next play success rate after high-pressure LPRs ({minimums})")
        }
        LprView::Low | LprView::High => format!(
            "Expected goals for the rest of the defenseman's shift or until a faceoff occurs ({minimums})"
        ),
    };

    let body = match table.rows.is_empty() {
        true => view! { <p class="text-muted">"No data available."</p> }.into_any(),
        false => lpr_table(table).into_any(),
    };
    view! {
        <select class="form-select mb-2" style="max-width: 450px" on:change=on_view>
            {options}
        </select>
        <p class="text-muted mb-2" style="font-size: 14px">{subtitle}</p>
        {body}
    }
}

/// A column: its header, the sort it offers (if any), and its cell for a row.
type Column = (&'static str, Option<LprSortField>);

fn lpr_table(table: LprTable) -> impl IntoView {
    let rate_view = table.view == LprView::HighNextRate;
    let columns: Vec<Column> = match rate_view {
        true => vec![
            ("Player", None),
            ("GP", None),
            ("Success", Some(LprSortField::Successes)),
            ("Failure", Some(LprSortField::Failures)),
            ("Success Rate", Some(LprSortField::SuccessRate)),
        ],
        false => vec![
            ("Player", None),
            ("GP", None),
            ("LPR", None),
            ("Avg oixGF", Some(LprSortField::AvgOiXgf)),
            ("Avg oixGA", Some(LprSortField::AvgOiXga)),
            ("oixGF", Some(LprSortField::TotalOiXgf)),
            ("oixGA", Some(LprSortField::TotalOiXga)),
            ("xG%", Some(LprSortField::XgPct)),
        ],
    };
    let current = LprQuery {
        view: table.view,
        sort: Some(table.sort),
        dir: table.dir,
    };

    let go = go_to();
    let headers = columns
        .iter()
        .map(|&(label, sort)| match sort {
            None => view! { <th>{label}</th> }.into_any(),
            Some(field) => {
                let active = field == table.sort;
                let (dir, label) = match (active, table.dir) {
                    (true, Dir::Desc) => (Dir::Asc, format!("{label} ▼")),
                    (true, Dir::Asc) => (Dir::Desc, format!("{label} ▲")),
                    _ => (Dir::Desc, label.to_string()),
                };
                let link = href(&LprQuery {
                    sort: Some(field),
                    dir,
                    ..current.clone()
                });
                let go = go.clone();
                view! {
                    <th class="sortable" class:active=active on:click=move |_| go(&link)>
                        {label}
                    </th>
                }
                .into_any()
            }
        })
        .collect_view();

    let sorts: Vec<Option<LprSortField>> = columns.iter().map(|c| c.1).collect();
    let row = |name: AnyView, values: Vec<String>, total: bool, i: usize| {
        let cells = values
            .into_iter()
            .zip(&sorts[1..])
            .map(|(v, &sort)| {
                let active = !total && sort == Some(table.sort);
                view! { <td class:active=active>{v}</td> }
            })
            .collect_view();
        view! {
            <tr class:lpr-total=total class:lpr-alt=!total && i % 2 == 1>
                <td class="lpr-name">{name}</td>
                {cells}
            </tr>
        }
    };

    let t = &table.totals;
    let total = match rate_view {
        true => vec![
            String::new(),
            t.successes.unwrap_or_default().to_string(),
            t.failures.unwrap_or_default().to_string(),
            pct1(t.success_rate),
        ],
        false => vec![
            String::new(),
            t.lpr_count.to_string(),
            dec(t.avg_oi_xgf, 3),
            dec(t.avg_oi_xga, 3),
            dec(t.total_oi_xgf, 2),
            dec(t.total_oi_xga, 2),
            pct1(t.xg_pct),
        ],
    };
    let total_row = row(view! { "Total" }.into_any(), total, true, 0);
    let rows = table
        .rows
        .iter()
        .enumerate()
        .map(|(i, r)| {
            let s = &r.stats;
            let values = match rate_view {
                true => vec![
                    s.games_played.to_string(),
                    s.successes.unwrap_or_default().to_string(),
                    s.failures.unwrap_or_default().to_string(),
                    pct1(s.success_rate),
                ],
                false => vec![
                    s.games_played.to_string(),
                    s.lpr_count.to_string(),
                    dec(s.avg_oi_xgf, 3),
                    dec(s.avg_oi_xga, 3),
                    dec(s.total_oi_xgf, 2),
                    dec(s.total_oi_xga, 2),
                    pct1(s.xg_pct),
                ],
            };
            let name = view! {
                <a href=format!("/player/{}", s.player_id) class="team-link">
                    {r.full_name.clone()}
                </a>
            }
            .into_any();
            row(name, values, false, i)
        })
        .collect_view();

    view! {
        <table class="lpr-table">
            <thead>
                <tr>{headers}</tr>
            </thead>
            <tbody>{total_row} {rows}</tbody>
        </table>
    }
}

fn dec(v: Option<f64>, places: usize) -> String {
    v.map(|v| format!("{v:.places$}")).unwrap_or_default()
}

/// A fraction as a percentage to one place: 0.5123 is "51.2%".
fn pct1(v: Option<f64>) -> String {
    v.map(|v| format!("{:.1}%", v * 100.0)).unwrap_or_default()
}
