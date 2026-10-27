//! What the player tables share (Player Stats, Team Detail, Player Detail): the stat
//! columns, sortable headers and the situation toggle. Each choice is a link: the server
//! sorts.

use leptos::prelude::*;
use leptos_router::NavigateOptions;
use leptos_router::hooks::{use_location, use_navigate};
use serde::de::DeserializeOwned;

use crate::types::{Dir, GameStats, PlayerSeasonLine, Situation, SortField};

const SITUATIONS: [(Situation, &str); 5] = [
    (Situation::Tot, "All"),
    (Situation::Es, "Even Strength"),
    (Situation::Ev5, "5-on-5"),
    (Situation::Pp, "Power Play"),
    (Situation::Pk, "Short-Handed"),
];

/// The stat columns after the name (and team), in order.
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

/// Time on ice to xG%, as shown, from `SeasonStats` (`atoi`) or `GameStats` (`toi`).
macro_rules! stat_values {
    ($s:expr, $toi:ident) => {{
        let s = $s;
        [
            mmss(s.$toi),
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
        ]
    }};
}
/// The page's query string, parsed. An unreadable one (say, an unknown sort) gives the
/// default, so a bad link shows the default table.
pub fn url_query<T: DeserializeOwned + Default>() -> impl Fn() -> T + Copy {
    let search = use_location().search;
    move || {
        let search = search.get();
        serde_urlencoded::from_str(search.trim_start_matches('?')).unwrap_or_default()
    }
}

/// Navigate within the page: re-sorting or switching situation keeps the reader's place.
pub fn go_to() -> impl Fn(&str) + Clone + 'static {
    let navigate = use_navigate();
    move |href| {
        let options = NavigateOptions {
            scroll: false,
            ..Default::default()
        };
        navigate(href, options)
    }
}

/// `<option>`s for a `<select>`.
pub fn options(values: Vec<String>, selected: &str) -> impl IntoView + use<> {
    values
        .into_iter()
        .map(|v| {
            let is_selected = v == selected;
            let label = v.clone();
            view! { <option value=v selected=is_selected>{label}</option> }
        })
        .collect_view()
}

/// "Situation:" and a button per situation; `href` gives each one's link. These return
/// `AnyView` so the result doesn't borrow `href`, which is only called here.
pub fn situation_toggle(current: Situation, href: impl Fn(Situation) -> String) -> AnyView {
    let go = go_to();
    let buttons = SITUATIONS
        .iter()
        .map(|&(situation, label)| {
            let go = go.clone();
            let href = href(situation);
            view! {
                <button
                    type="button"
                    class:active=situation == current
                    on:click=move |_| go(&href)
                >
                    {label}
                </button>
            }
        })
        .collect_view();
    view! {
        <div class="situation-toggle mb-3">
            <span class="situation-label">"Situation:"</span>
            <div class="situation-buttons">{buttons}</div>
        </div>
    }
    .into_any()
}

/// `<col>`s for the stat columns.
pub fn stat_cols() -> impl IntoView {
    COLUMNS
        .iter()
        .map(|_| view! { <col style="width: 60px" /> })
        .collect_view()
}

/// A sortable `<th>` per stat column. A click sorts descending; clicking the sorted
/// column again flips it. `href` gives the link for a sort.
pub fn sort_headers(sort: SortField, dir: Dir, href: impl Fn(SortField, Dir) -> String) -> AnyView {
    let go = go_to();
    COLUMNS
        .iter()
        .map(|&(field, label)| {
            let go = go.clone();
            let active = field == sort;
            let next = match (active, dir) {
                (true, Dir::Desc) => Dir::Asc,
                _ => Dir::Desc,
            };
            let href = href(field, next);
            let label = match (active, dir) {
                (true, Dir::Desc) => format!("{label} ▼"),
                (true, Dir::Asc) => format!("{label} ▲"),
                _ => label.to_string(),
            };
            view! {
                <th class="sortable" class:active=active on:click=move |_| go(&href)>
                    {label}
                </th>
            }
        })
        .collect_view()
        .into_any()
}

/// A `<td>` per stat column, the sorted column highlighted.
pub fn stat_cells(r: &PlayerSeasonLine, sorted_by: SortField) -> impl IntoView + use<> {
    let mut values = vec![
        r.age.to_string(),
        r.position.clone(),
        r.games_played.to_string(),
    ];
    values.extend(stat_values!(&r.stats, atoi));
    COLUMNS
        .iter()
        .zip(values)
        .map(|(&(field, _), v)| view! { <td class:active=field == sorted_by>{v}</td> })
        .collect_view()
}

/// Unsortable `<th>`s from time on ice to xG%, the first labelled `toi` (ATOI or TOI).
pub fn plain_headers(toi: &'static str) -> impl IntoView {
    std::iter::once(toi)
        .chain(COLUMNS[4..].iter().map(|&(_, label)| label))
        .map(|label| view! { <th>{label}</th> })
        .collect_view()
}

/// `<td>`s for a season row from GP to xG% (Player Detail's seasons).
pub fn season_cells(r: &PlayerSeasonLine) -> impl IntoView + use<> {
    let mut values = vec![r.games_played.to_string()];
    values.extend(stat_values!(&r.stats, atoi));
    tds(values)
}

/// `<td>`s for a game from TOI to xG% (the game log).
pub fn game_cells(s: &GameStats) -> impl IntoView + use<> {
    tds(stat_values!(s, toi).into())
}

fn tds(values: Vec<String>) -> impl IntoView {
    values
        .into_iter()
        .map(|v| view! { <td>{v}</td> })
        .collect_view()
}

/// Seconds as m:ss.
pub fn mmss(seconds: f64) -> String {
    let total = seconds as i64;
    format!("{}:{:02}", total / 60, total % 60)
}

pub fn pct(v: Option<f64>) -> String {
    v.map(|v| format!("{v:.3}")).unwrap_or_default()
}
