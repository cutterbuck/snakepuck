//! The rink as SVG, in feet: x from -100 to 100 along the length, y from -42.5 to 42.5
//! across, center ice at the origin (HALO's coordinates). SVG's y runs down, so every y
//! is flipped. Ported from the Dash site's `app/utils/rink.py`; line widths are in screen
//! pixels, as Plotly drew them.

use leptos::prelude::*;

use crate::types::Frame;

const ICE: &str = "#f0f5ff";
const RED: &str = "#c8102e";
const BLUE: &str = "#0033a0";
const BOARDS: &str = "#333333";
const CREASE: &str = "#add8e6";
/// The markings are faded so players and events stand out.
const MARKINGS_OPACITY: f64 = 0.35;

const HALF_LENGTH: f64 = 100.0;
const HALF_WIDTH: f64 = 42.5;
const CORNER_RADIUS: f64 = 28.0;
const BLUE_LINE_X: f64 = 25.0;
const GOAL_LINE_X: f64 = 89.0;
const CIRCLE_RADIUS: f64 = 15.0;
const ZONE_DOT: (f64, f64) = (69.0, 22.0);
const NEUTRAL_DOT: (f64, f64) = (20.0, 22.0);

/// Event marker colors, by event type; anything else is teal.
pub fn event_color(event_type: &str) -> &'static str {
    match event_type {
        "goal" | "assist" => "#FFD700",
        "shot" => "#dc3545",
        "faceoff" => "#28a745",
        "block" => "#6c757d",
        "check" => "#fd7e14",
        "penalty" | "penaltydrawn" => "#6f42c1",
        _ => "#17a2b8",
    }
}

/// The rink, with any `children` drawn on top in rink coordinates (y flipped).
#[component]
pub fn Rink(center_logo: String, #[prop(optional)] children: Option<Children>) -> impl IntoView {
    view! {
        <svg class="rink" viewBox="-105 -47 210 94" role="img" aria-label="Rink">
            <rect x=-HALF_LENGTH y=-HALF_WIDTH width=2.0 * HALF_LENGTH height=2.0 * HALF_WIDTH
                rx=CORNER_RADIUS fill=ICE />
            <g opacity=MARKINGS_OPACITY>{markings()}</g>
            <image href=center_logo x=-11 y=-11 width=22 height=22 opacity=0.3 />
            {children.map(|c| c())}
        </svg>
    }
}

fn line(x1: f64, y1: f64, x2: f64, y2: f64, color: &'static str, width: f64) -> impl IntoView {
    view! {
        <line x1=x1 y1=-y1 x2=x2 y2=-y2 stroke=color stroke-width=width
            vector-effect="non-scaling-stroke" />
    }
}

fn ring(x: f64, y: f64, color: &'static str, width: f64) -> impl IntoView {
    view! {
        <circle cx=x cy=-y r=CIRCLE_RADIUS fill="none" stroke=color stroke-width=width
            vector-effect="non-scaling-stroke" />
    }
}

fn dot(x: f64, y: f64, r: f64, color: &'static str) -> impl IntoView {
    view! { <circle cx=x cy=-y r=r fill=color /> }
}

fn markings() -> impl IntoView {
    let corners = [(1.0, 1.0), (1.0, -1.0), (-1.0, 1.0), (-1.0, -1.0)];
    let goal_line_y = board_y(GOAL_LINE_X);
    view! {
        <rect x=-HALF_LENGTH y=-HALF_WIDTH width=2.0 * HALF_LENGTH height=2.0 * HALF_WIDTH
            rx=CORNER_RADIUS fill="none" stroke=BOARDS stroke-width=3
            vector-effect="non-scaling-stroke" />
        {line(0.0, -HALF_WIDTH, 0.0, HALF_WIDTH, RED, 3.0)}
        {line(BLUE_LINE_X, -HALF_WIDTH, BLUE_LINE_X, HALF_WIDTH, BLUE, 3.0)}
        {line(-BLUE_LINE_X, -HALF_WIDTH, -BLUE_LINE_X, HALF_WIDTH, BLUE, 3.0)}
        {line(GOAL_LINE_X, -goal_line_y, GOAL_LINE_X, goal_line_y, RED, 2.0)}
        {line(-GOAL_LINE_X, -goal_line_y, -GOAL_LINE_X, goal_line_y, RED, 2.0)}
        {ring(0.0, 0.0, BLUE, 2.0)}
        {dot(0.0, 0.0, 1.0, BLUE)}
        {corners
            .into_iter()
            .map(|(sx, sy)| ring(sx * ZONE_DOT.0, sy * ZONE_DOT.1, RED, 1.5))
            .collect_view()}
        {corners
            .into_iter()
            .map(|(sx, sy)| {
                view! {
                    {dot(sx * ZONE_DOT.0, sy * ZONE_DOT.1, 0.7, RED)}
                    {dot(sx * NEUTRAL_DOT.0, sy * NEUTRAL_DOT.1, 0.7, RED)}
                }
            })
            .collect_view()}
        {[1.0, -1.0]
            .into_iter()
            .map(|side| {
                view! {
                    <path d=crease(side) fill=CREASE stroke=RED stroke-width=1.5
                        vector-effect="non-scaling-stroke" />
                    {trapezoid(side)}
                }
            })
            .collect_view()}
    }
}

/// Half the rink's width at `x`: the full half-width, less in the rounded corners.
fn board_y(x: f64) -> f64 {
    let corner_x = HALF_LENGTH - CORNER_RADIUS;
    let dx = (x.abs() - corner_x).max(0.0);
    match dx >= CORNER_RADIUS {
        true => HALF_WIDTH - CORNER_RADIUS,
        false => HALF_WIDTH - CORNER_RADIUS + (CORNER_RADIUS * CORNER_RADIUS - dx * dx).sqrt(),
    }
}

/// The goal crease at one end (`side` 1 is the right net): 4 ft either side of the net
/// on the goal line, straight 4.5 ft out, closed by a 6 ft arc.
fn crease(side: f64) -> String {
    let gx = GOAL_LINE_X * side;
    let (half_w, straight, r) = (4.0_f64, 4.5, 6.0_f64);
    let out = -side; // toward center ice
    let half_angle = (half_w / r).asin();
    let mut points = vec![(gx, -half_w), (gx + out * straight, -half_w)];
    for i in 0..=30 {
        let t = i as f64 / 30.0;
        // From -half_angle to +half_angle, measured from the direction of center ice.
        let a = -half_angle + 2.0 * half_angle * t;
        points.push((gx + out * r * a.cos(), r * a.sin()));
    }
    points.extend([(gx + out * straight, half_w), (gx, half_w)]);
    let mut d = String::new();
    for (i, (x, y)) in points.iter().enumerate() {
        d.push_str(&format!(
            "{}{x:.2},{:.2} ",
            if i == 0 { "M" } else { "L" },
            -y
        ));
    }
    d.push('Z');
    d
}

/// The trapezoid behind a net: its three red sides (the boards close it).
fn trapezoid(side: f64) -> impl IntoView {
    let (gx, bx) = (GOAL_LINE_X * side, HALF_LENGTH * side);
    view! {
        {line(gx, 11.0, bx, 14.0, RED, 1.5)}
        {line(gx, -11.0, bx, -14.0, RED, 1.5)}
        {line(gx, -11.0, gx, 11.0, RED, 1.5)}
    }
}

/// Label positions around a marker (below, above, right, left), cycled so neighbours'
/// labels spread out: (dx, dy, text-anchor, dominant-baseline).
const LABEL_PLACES: [(f64, f64, &str, &str); 4] = [
    (0.0, -3.5, "middle", "hanging"),
    (0.0, 3.5, "middle", "auto"),
    (3.5, 0.0, "start", "central"),
    (-3.5, 0.0, "end", "central"),
];

/// One frame on the rink: the event, and each tracked skater as their team's logo with
/// their last name. The player in the event is drawn larger, opaque and in bold.
pub fn frame_markers(frame: &Frame, logo: impl Fn(&str) -> String) -> AnyView {
    let e = &frame.event;
    let skaters = frame
        .skaters
        .iter()
        .enumerate()
        .map(|(i, s)| {
            let involved = s.player_id.is_some() && s.player_id == e.player_id;
            let size = if involved { 7.0 } else { 5.0 };
            let (x, y) = (s.tracking_x, -s.tracking_y);
            let (dx, dy, anchor, baseline) = LABEL_PLACES[i % LABEL_PLACES.len()];
            let label = s.last_name.clone().filter(|n| !n.is_empty()).map(|name| {
                view! {
                    <text x=x + dx y=y - dy text-anchor=anchor dominant-baseline=baseline
                        font-size=2 fill="#333" font-weight=if involved { "bold" } else { "normal" }>
                        {name}
                    </text>
                }
            });
            view! {
                <g class="rink-skater">
                    <title>{s.display_name.clone()}</title>
                    <image href=logo(&s.team_abbr) x=x - size / 2.0 y=y - size / 2.0
                        width=size height=size opacity=if involved { 1.0 } else { 0.5 } />
                    {label}
                </g>
            }
        })
        .collect_view();

    let event = e.x.zip(e.y).map(|(x, y)| {
        let color = event_color(&e.event_type);
        let mut text = vec![format!("{}: {}", e.event_type, e.description)];
        if !e.detail.is_empty() {
            text.push(format!("Detail: {}", e.detail));
        }
        if let Some(flags) = e.flags.as_ref().filter(|f| !f.is_empty()) {
            text.push(format!("Flags: {flags}"));
        }
        view! {
            <g class="rink-event">
                <title>{text.join("\n")}</title>
                <circle cx=x cy=-y r=2.8 fill=color opacity=0.25 />
                <circle cx=x cy=-y r=1.4 fill=color stroke="white" stroke-width=2
                    vector-effect="non-scaling-stroke" />
            </g>
        }
    });

    view! { {skaters} {event} }.into_any()
}
