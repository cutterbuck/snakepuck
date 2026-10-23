import json

from dash import ALL, Input, Output, State, ctx, dcc, html

from app.models import Event, Game, Player, PlayerGameStats, Stint, Tracking
from app.utils.rink import create_rink_figure


# Playback runs at PLAYBACK_SPEED x real time, clamped so rapid-fire events
# stay visible and long stoppages don't stall the animation
PLAYBACK_SPEED = 1
MIN_FRAME_MS = 800
MAX_FRAME_MS = 3000

# Client-side renderer: copies the base rink figure and layers the current
# frame's event markers, team-logo player markers, and name labels on top.
# Plotly.react diffs the result, so the rink itself is never redrawn.
RENDER_FRAME_JS = """
function(base, stintData, frameIndex) {
    if (!base) {
        return window.dash_clientside.no_update;
    }
    const EVENT_COLORS = __EVENT_COLORS__;
    const DEFAULT_EVENT_COLOR = __DEFAULT_EVENT_COLOR__;

    const data = base.data.slice();
    const layout = Object.assign({}, base.layout);
    const images = (base.layout.images || []).slice();
    const annotations = (base.layout.annotations || []).slice();

    const frames = stintData && stintData.frames;
    if (frames && frames.length) {
        let idx = frameIndex || 0;
        if (idx >= frames.length) {
            idx = 0;
        }
        const frame = frames[idx];
        const logoMap = stintData.logo_map || {};
        const events = frame.events || [];

        // Events, grouped by type: glow layer plus main marker
        const eventsByType = {};
        events.forEach(function(e) {
            (eventsByType[e.event_type] = eventsByType[e.event_type] || []).push(e);
        });
        Object.keys(eventsByType).forEach(function(et) {
            const evs = eventsByType[et];
            const color = EVENT_COLORS[et] || DEFAULT_EVENT_COLOR;
            const xs = evs.map(function(e) { return e.x; });
            const ys = evs.map(function(e) { return e.y; });
            data.push({
                type: "scatter", x: xs, y: ys, mode: "markers",
                marker: {size: 24, color: color, opacity: 0.25},
                hoverinfo: "skip", showlegend: false,
            });
            data.push({
                type: "scatter", x: xs, y: ys, mode: "markers",
                marker: {size: 12, color: color, opacity: 1.0, line: {width: 2, color: "white"}},
                hoverinfo: "text",
                text: evs.map(function(e) {
                    return [
                        et + ": " + e.description,
                        e.detail ? "Detail: " + e.detail : "",
                        e.flags ? "Flags: " + e.flags : "",
                    ].filter(Boolean).join("<br>");
                }),
                name: et, showlegend: true,
            });
        });

        // Player markers (team logos) and last-name labels
        const tracking = frame.tracking || [];
        if (tracking.length) {
            const eventPlayerIds = new Set(
                events.filter(function(e) { return e.player_id; })
                      .map(function(e) { return e.player_id; })
            );
            // Cycle label placement (below, above, right, left) to spread labels out
            const placements = [
                {xanchor: "center", yanchor: "top", dx: 0, dy: -3.5},
                {xanchor: "center", yanchor: "bottom", dx: 0, dy: 3.5},
                {xanchor: "left", yanchor: "middle", dx: 3.5, dy: 0},
                {xanchor: "right", yanchor: "middle", dx: -3.5, dy: 0},
            ];
            tracking.forEach(function(t, i) {
                const involved = eventPlayerIds.has(t.player_id);
                const logo = logoMap[t.team_id];
                if (logo) {
                    const size = involved ? 7 : 5;
                    images.push({
                        source: logo, xref: "x", yref: "y",
                        x: t.tracking_x, y: t.tracking_y,
                        xanchor: "center", yanchor: "middle",
                        sizex: size, sizey: size,
                        opacity: involved ? 1.0 : 0.5, layer: "above",
                    });
                }
                if (t.last_name) {
                    const p = placements[i % placements.length];
                    annotations.push({
                        x: t.tracking_x + p.dx, y: t.tracking_y + p.dy,
                        text: involved ? "<b>" + t.last_name + "</b>" : t.last_name,
                        showarrow: false, font: {size: 8, color: "#333"},
                        xanchor: p.xanchor, yanchor: p.yanchor,
                    });
                }
            });
            // Invisible scatter for player-name hover
            data.push({
                type: "scatter",
                x: tracking.map(function(t) { return t.tracking_x; }),
                y: tracking.map(function(t) { return t.tracking_y; }),
                mode: "markers", marker: {size: 10, opacity: 0},
                hoverinfo: "text",
                text: tracking.map(function(t) { return t.player_name; }),
                showlegend: false,
            });
        }
    }

    layout.images = images;
    layout.annotations = annotations;
    return {data: data, layout: layout};
}
"""


def _playback_delay_ms(gap_seconds):
    """Convert the real-time gap between two events to a playback delay."""
    ms = max(gap_seconds, 0) * 1000 / PLAYBACK_SPEED
    return int(min(max(ms, MIN_FRAME_MS), MAX_FRAME_MS))


def _frame_delay(frame_delays, frame_index):
    if frame_delays and 0 <= (frame_index or 0) < len(frame_delays):
        return frame_delays[frame_index or 0]
    return MAX_FRAME_MS


def _seconds_to_mmss(seconds):
    """Convert seconds (float) to M:SS format."""
    total = int(seconds)
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


HEADER_STYLE = {
    "backgroundColor": "#163d5c",
    "color": "#d0e8f7",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "6px 10px",
    "borderBottom": "2px solid #4fc3f7",
}

CELL_STYLE = {
    "textAlign": "center",
    "padding": "5px 10px",
}

TABLE_STYLE = {
    "width": "100%",
    "borderCollapse": "collapse",
    "tableLayout": "fixed",
}

STAT_COL_WIDTH = "60px"

STAT_HEADERS = [
    "TOI",
    "G",
    "A",
    "PTS",
    "S",
    "S%",
    "FOW",
    "FOL",
    "FO%",
    "PIM",
    "PD",
    "BLK",
    "HIT",
    "ixG",
    "oixGF",
    "oixGA",
]


def _fmt_pct(val):
    if val is None:
        return ""
    return f"{val:.3f}"


SITUATIONS = [
    ("tot", "All"),
    ("es", "Even Strength"),
    ("ev5", "5-on-5"),
    ("pp", "Power Play"),
    ("pk", "Short-Handed"),
]

SITUATION_BTN_BASE = {
    "padding": "4px 12px",
    "border": "1px solid #ccc",
    "cursor": "pointer",
    "fontSize": "14px",
    "fontWeight": "bold",
}

# Fields that are NOT situation-dependent
STATIC_FIELDS = {"penalties", "penalties_drawn"}


def register_game_report_callbacks(dash_app):
    @dash_app.callback(
        Output("game-report-player-id", "data"),
        Output("game-report-game-id", "data"),
        Output("game-report-breadcrumb", "children"),
        Input("url", "pathname"),
    )
    def store_game_report_ids(pathname):
        if pathname and "/game/" in pathname:
            try:
                parts = pathname.strip("/").split("/")
                player_id = int(parts[1])
                game_int_id = int(parts[3])
                game = Game.query.get(game_int_id)
                if not game:
                    return None, None, html.Div()
                game_id = game.game_id
                player = Player.query.get(player_id)

                # Build breadcrumb
                crumbs = [
                    dcc.Link(
                        "Team Standings",
                        href="/team-standings",
                        className="breadcrumb-link",
                    ),
                    html.Span(" / ", className="breadcrumb-sep"),
                ]

                if player:
                    # Get team/season for team link
                    pgs = PlayerGameStats.query.filter_by(
                        player_id=player.playerId, game_id=game_id
                    ).first()
                    if pgs and pgs.team and pgs.season:
                        crumbs.append(
                            dcc.Link(
                                pgs.team.name,
                                href=f"/team/{pgs.team.id}/{pgs.season.name}",
                                className="breadcrumb-link",
                            )
                        )
                        crumbs.append(html.Span(" / ", className="breadcrumb-sep"))

                    crumbs.append(
                        dcc.Link(
                            f"{player.firstName} {player.lastName}",
                            href=f"/player/{player_id}",
                            className="breadcrumb-link",
                        )
                    )
                    crumbs.append(html.Span(" / ", className="breadcrumb-sep"))

                crumbs.append(html.Span("Game Report", className="breadcrumb-current"))
                breadcrumb = html.Div(crumbs, className="breadcrumb-nav")

                return player_id, game_id, breadcrumb
            except (ValueError, IndexError):
                return None, None, html.Div()
        return None, None, html.Div()

    @dash_app.callback(
        Output("game-report-header", "children"),
        Input("game-report-player-id", "data"),
        Input("game-report-game-id", "data"),
    )
    def update_game_report_header(player_id, game_id):
        if not player_id or not game_id:
            return html.Div()

        player = Player.query.get(player_id)
        if not player:
            return html.H2("Player not found")

        game = Game.query.filter_by(game_id=game_id).first()
        if not game:
            return html.H2("Game not found")

        # Determine opponent
        pgs = PlayerGameStats.query.filter_by(
            player_id=player.playerId, game_id=game_id
        ).first()
        if not pgs:
            return html.H2("Game stats not found")

        is_home = pgs.team_id == game.home_team_id
        opp_team = game.away_team if is_home else game.home_team
        player_team = game.home_team if is_home else game.away_team
        player_score = game.home_score if is_home else game.away_score
        opp_score = game.away_score if is_home else game.home_score

        outcome_str = (game.game_outcome or "").lower()
        if player_score > opp_score:
            if "_so_" in outcome_str:
                result = f"SOW {player_score}-{opp_score}"
            elif "_ot_" in outcome_str:
                result = f"OTW {player_score}-{opp_score}"
            else:
                result = f"W {player_score}-{opp_score}"
        elif "_ot_" in outcome_str:
            result = f"OTL {opp_score}-{player_score}"
        elif "_so_" in outcome_str:
            result = f"SOL {opp_score}-{player_score}"
        else:
            result = f"L {opp_score}-{player_score}"

        date_str = game.date.strftime("%B %d, %Y") if game.date else ""

        # Build single-line header
        prefix = "vs." if is_home else "@"
        children = []
        children.append(
            html.Span(
                f"{player.firstName} {player.lastName}",
                style={
                    "fontSize": "24px",
                    "fontWeight": "bold",
                    "marginRight": "12px",
                },
            )
        )
        children.append(
            html.Span("|", style={"marginRight": "12px", "color": "#666"}),
        )
        if player_team and player_team.logo:
            children.append(
                html.Img(
                    src=player_team.logo,
                    style={
                        "width": "24px",
                        "height": "24px",
                        "marginRight": "6px",
                    },
                )
            )
        children.append(
            html.Span(prefix, style={"marginRight": "6px"}),
        )
        if opp_team and opp_team.logo:
            children.append(
                html.Img(
                    src=opp_team.logo,
                    style={
                        "width": "24px",
                        "height": "24px",
                    },
                )
            )
        children.append(
            html.Span(
                opp_team.abbrev if opp_team else "???",
                style={"paddingLeft": "6px", "marginRight": "12px"},
            )
        )
        children.append(
            html.Span("|", style={"marginRight": "12px", "color": "#666"}),
        )
        children.append(
            html.Span(result, style={"marginRight": "12px"}),
        )
        children.append(
            html.Span("|", style={"marginRight": "12px", "color": "#666"}),
        )
        children.append(
            html.Span(date_str, style={"color": "#666"}),
        )

        return html.Div(
            children,
            style={"display": "flex", "alignItems": "center"},
        )

    @dash_app.callback(
        Output("game-report-situation-toggle", "children"),
        Input("game-report-player-id", "data"),
        Input("game-report-situation", "data"),
    )
    def update_gr_situation_toggle(player_id, selected_situation):
        if not player_id:
            return html.Div()

        selected = selected_situation or "tot"
        buttons = []
        for idx, (value, label) in enumerate(SITUATIONS):
            active = selected == value
            if idx == 0:
                radius = "4px 0 0 4px"
            elif idx == len(SITUATIONS) - 1:
                radius = "0 4px 4px 0"
            else:
                radius = "0"
            style = {
                **SITUATION_BTN_BASE,
                "backgroundColor": "#1a6fa8" if active else "#fff",
                "color": "#fff" if active else "#333",
                "borderRadius": radius,
            }
            buttons.append(
                html.Button(
                    label,
                    id={"type": "gr-situation-btn", "index": value},
                    n_clicks=0,
                    style=style,
                )
            )

        return html.Div(
            [
                html.Span(
                    "Situation:",
                    style={
                        "fontWeight": "bold",
                        "marginRight": "8px",
                        "fontSize": "14px",
                    },
                ),
                html.Div(buttons, style={"display": "flex"}),
            ],
            style={"display": "flex", "alignItems": "center"},
        )

    @dash_app.callback(
        Output("game-report-situation", "data"),
        Input({"type": "gr-situation-btn", "index": ALL}, "n_clicks"),
        State("game-report-situation", "data"),
        prevent_initial_call=True,
    )
    def toggle_gr_situation(n_clicks, current_situation):
        if not ctx.triggered_id or not any(n for n in n_clicks if n):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        return ctx.triggered_id["index"]

    @dash_app.callback(
        Output("game-report-stats", "children"),
        Input("game-report-player-id", "data"),
        Input("game-report-game-id", "data"),
        Input("game-report-situation", "data"),
    )
    def update_game_report_stats(player_id, game_id, situation=None):
        if not player_id or not game_id:
            return html.Div()

        player = Player.query.get(player_id)
        if not player:
            return html.Div()

        pgs = PlayerGameStats.query.filter_by(
            player_id=player.playerId, game_id=game_id
        ).first()
        if not pgs:
            return html.Div("No stats found for this game.", style={"color": "#666"})

        prefix = situation or "tot"

        header_cells = [html.Th(h, style=HEADER_STYLE) for h in STAT_HEADERS]
        thead = html.Thead(html.Tr(header_cells))

        stat_cols = [html.Col(style={"width": STAT_COL_WIDTH}) for _ in STAT_HEADERS]
        colgroup = html.Colgroup(stat_cols)

        values = [
            _seconds_to_mmss(getattr(pgs, f"{prefix}_toi")),
            getattr(pgs, f"{prefix}_goals"),
            getattr(pgs, f"{prefix}_assists"),
            getattr(pgs, f"{prefix}_points"),
            getattr(pgs, f"{prefix}_shots"),
            _fmt_pct(getattr(pgs, f"{prefix}_shooting_pct")),
            getattr(pgs, f"{prefix}_faceoffs_won"),
            getattr(pgs, f"{prefix}_faceoffs_lost"),
            _fmt_pct(getattr(pgs, f"{prefix}_faceoff_pct")),
            pgs.penalties,
            pgs.penalties_drawn,
            getattr(pgs, f"{prefix}_blocks"),
            getattr(pgs, f"{prefix}_checks"),
            getattr(pgs, f"{prefix}_i_xg"),
            getattr(pgs, f"{prefix}_oi_xgf"),
            getattr(pgs, f"{prefix}_oi_xga"),
        ]
        cells = [html.Td(v, style=CELL_STYLE) for v in values]
        row = html.Tr(cells, style={"backgroundColor": "#ffffff"})
        tbody = html.Tbody([row])

        table = html.Table(
            [colgroup, thead, tbody],
            style=TABLE_STYLE,
        )

        return html.Div([table], className="mt-3")

    STINT_HEADERS = [
        "Shift",
        "TOI",
        "Start",
        "End",
        "Home Skaters",
        "Away Skaters",
        "Home Net Empty",
        "Away Net Empty",
        "Score",
        "ixG",
        "oixGF",
        "oixGA",
    ]

    PERIOD_BTN_BASE = {
        "padding": "4px 12px",
        "border": "1px solid #ccc",
        "cursor": "pointer",
        "fontSize": "14px",
        "fontWeight": "bold",
    }

    @dash_app.callback(
        Output("game-report-stints-header", "children"),
        Input("game-report-stint-period", "data"),
        Input("game-report-player-id", "data"),
        Input("game-report-game-id", "data"),
    )
    def update_stints_header(selected_period, player_id, game_id):
        # Determine which periods exist for this player/game
        periods = [1, 2, 3]
        if player_id and game_id:
            player = Player.query.get(player_id)
            if player:
                distinct_periods = (
                    Stint.query.with_entities(Stint.period)
                    .filter_by(player_id=player.playerId, game_id=game_id)
                    .distinct()
                    .all()
                )
                existing = sorted(p[0] for p in distinct_periods if p[0] is not None)
                if existing:
                    periods = existing

        buttons = []
        for idx, p in enumerate(periods):
            active = selected_period == p
            label = "OT" if p >= 4 else str(p)
            if idx == 0:
                radius = "4px 0 0 4px"
            elif idx == len(periods) - 1:
                radius = "0 4px 4px 0"
            else:
                radius = "0"
            style = {
                **PERIOD_BTN_BASE,
                "backgroundColor": "#1a6fa8" if active else "#fff",
                "color": "#fff" if active else "#333",
                "borderRadius": radius,
            }
            buttons.append(
                html.Button(
                    label,
                    id={"type": "stint-period-btn", "index": p},
                    n_clicks=0,
                    style=style,
                )
            )

        return html.Div(
            [
                html.H4("Shifts", style={"marginRight": "32px", "marginBottom": "0"}),
                html.Span(
                    "Period:",
                    style={
                        "fontWeight": "bold",
                        "marginRight": "8px",
                        "fontSize": "14px",
                    },
                ),
                html.Div(buttons, style={"display": "flex"}),
            ],
            style={"display": "flex", "alignItems": "center"},
        )

    @dash_app.callback(
        Output("game-report-stint-period", "data"),
        Input({"type": "stint-period-btn", "index": ALL}, "n_clicks"),
        State("game-report-stint-period", "data"),
        prevent_initial_call=True,
    )
    def toggle_stint_period(n_clicks, current_period):
        if not ctx.triggered_id or not any(n for n in n_clicks if n):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        clicked = ctx.triggered_id["index"]
        # Toggle off if clicking the already-selected period
        if clicked == current_period:
            return None
        return clicked

    @dash_app.callback(
        Output("game-report-selected-stint", "data"),
        Input({"type": "stint-row", "index": ALL}, "n_clicks"),
        State("game-report-selected-stint", "data"),
        prevent_initial_call=True,
    )
    def toggle_selected_stint(n_clicks, current_selected):
        if not ctx.triggered_id or not any(n for n in n_clicks if n):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        clicked = ctx.triggered_id["index"]
        if clicked == current_selected:
            return None
        return clicked

    @dash_app.callback(
        Output("game-report-stints", "children"),
        Output("game-report-merged-stints", "data"),
        Input("game-report-player-id", "data"),
        Input("game-report-game-id", "data"),
        Input("game-report-stint-period", "data"),
        Input("game-report-selected-stint", "data"),
    )
    def update_game_report_stints(player_id, game_id, selected_period, selected_stint):
        if not player_id or not game_id:
            return html.Div(), {}

        player = Player.query.get(player_id)
        if not player:
            return html.Div(), {}

        # Get ALL stints for this player/game
        all_stints = (
            Stint.query.filter_by(player_id=player.playerId, game_id=game_id)
            .order_by(Stint.game_stint)
            .all()
        )

        if not all_stints:
            return html.Div("No stints found.", style={"color": "#666"}), {}

        # Group stints by shift number (from database)
        from collections import OrderedDict

        shift_groups = OrderedDict()
        for s in all_stints:
            shift_groups.setdefault(s.shift, []).append(s)
        all_groups = list(shift_groups.values())

        # Build merged stint mapping
        merged_map = {}
        for group in all_groups:
            first = group[0]
            last = group[-1]
            merged_map[str(first.id)] = {
                "period": first.period,
                "period_time_start": first.period_time_start,
                "period_time_end": last.period_time_end,
            }

        # Filter groups by selected period
        if selected_period is not None:
            groups = [g for g in all_groups if g[0].period == selected_period]
        else:
            groups = all_groups

        if not groups:
            return html.Div("No stints found.", style={"color": "#666"}), merged_map

        header_cells = [
            html.Th(
                h,
                style={
                    **HEADER_STYLE,
                    "position": "sticky",
                    "top": "0",
                    "zIndex": "1",
                },
            )
            for h in STINT_HEADERS
        ]
        thead = html.Thead(html.Tr(header_cells))

        rows = []
        for i, group in enumerate(groups):
            first = group[0]
            last = group[-1]
            is_selected = first.id == selected_stint
            row_bg = (
                {"backgroundColor": "#e8f4fb"}
                if i % 2 == 1
                else {"backgroundColor": "#ffffff"}
            )
            row_style = row_bg
            cls = "stint-row selected" if is_selected else "stint-row"

            # Aggregate xG across all stints in this shift
            def _sum_field(field):
                return round(sum(getattr(s, field) or 0 for s in group), 3)

            cells = [
                html.Td(first.shift, style=CELL_STYLE),
                html.Td(
                    _seconds_to_mmss(sum(getattr(s, "tot_toi") or 0 for s in group)),
                    style=CELL_STYLE,
                ),
                html.Td(
                    _seconds_to_mmss(first.period_time_start)
                    if first.period_time_start is not None
                    else "",
                    style=CELL_STYLE,
                ),
                html.Td(
                    _seconds_to_mmss(last.period_time_end)
                    if last.period_time_end is not None
                    else "",
                    style=CELL_STYLE,
                ),
                html.Td(first.n_home_skaters, style=CELL_STYLE),
                html.Td(first.n_away_skaters, style=CELL_STYLE),
                html.Td("Yes" if first.is_home_net_empty else "No", style=CELL_STYLE),
                html.Td("Yes" if first.is_away_net_empty else "No", style=CELL_STYLE),
                html.Td(
                    f"{first.home_score}-{first.away_score}"
                    if first.home_score is not None
                    else "",
                    style=CELL_STYLE,
                ),
                html.Td(_sum_field("tot_i_xg"), style=CELL_STYLE),
                html.Td(_sum_field("tot_oi_xgf"), style=CELL_STYLE),
                html.Td(_sum_field("tot_oi_xga"), style=CELL_STYLE),
            ]
            rows.append(
                html.Tr(
                    cells,
                    style=row_style,
                    className=cls,
                    id={"type": "stint-row", "index": first.id},
                    n_clicks=0,
                )
            )

            # Expand sub-rows for each stint when this shift is selected
            if is_selected and len(group) > 1:
                sub_cell_style = {**CELL_STYLE, "fontSize": "13px"}
                for si, stint in enumerate(group, 1):
                    sub_cells = [
                        html.Td(
                            f"Stint {si}",
                            style={
                                **sub_cell_style,
                                "borderLeft": "3px solid #1a6fa8",
                                "fontStyle": "italic",
                                "color": "#666",
                            },
                        ),
                        html.Td(
                            _seconds_to_mmss(stint.tot_toi or 0),
                            style=sub_cell_style,
                        ),
                        html.Td(
                            _seconds_to_mmss(stint.period_time_start)
                            if stint.period_time_start is not None
                            else "",
                            style=sub_cell_style,
                        ),
                        html.Td(
                            _seconds_to_mmss(stint.period_time_end)
                            if stint.period_time_end is not None
                            else "",
                            style=sub_cell_style,
                        ),
                        html.Td(stint.n_home_skaters, style=sub_cell_style),
                        html.Td(stint.n_away_skaters, style=sub_cell_style),
                        html.Td(
                            "Yes" if stint.is_home_net_empty else "No",
                            style=sub_cell_style,
                        ),
                        html.Td(
                            "Yes" if stint.is_away_net_empty else "No",
                            style=sub_cell_style,
                        ),
                        html.Td(
                            f"{stint.home_score}-{stint.away_score}"
                            if stint.home_score is not None
                            else "",
                            style=sub_cell_style,
                        ),
                        html.Td(stint.tot_i_xg or 0, style=sub_cell_style),
                        html.Td(stint.tot_oi_xgf or 0, style=sub_cell_style),
                        html.Td(stint.tot_oi_xga or 0, style=sub_cell_style),
                    ]
                    rows.append(
                        html.Tr(
                            sub_cells,
                            style={"backgroundColor": "rgba(79, 195, 247, 0.08)"},
                            className="stint-row",
                            id={
                                "type": "stint-sub-row",
                                "index": stint.period_time_start or 0,
                            },
                            n_clicks=0,
                        )
                    )

        tbody = html.Tbody(rows)
        table = html.Table(
            [thead, tbody],
            style=TABLE_STYLE,
        )

        return (
            html.Div(
                table,
                className="stints-scroll-container",
                style={
                    "maxHeight": "335px",
                    "overflowX": "auto",
                },
            ),
            merged_map,
        )

    EVENT_COLORS = {
        "goal": "#FFD700",
        "shot": "#dc3545",
        "assist": "#FFD700",
        "faceoff": "#28a745",
        "block": "#6c757d",
        "check": "#fd7e14",
        "penalty": "#6f42c1",
        "penaltydrawn": "#6f42c1",
    }
    DEFAULT_EVENT_COLOR = "#17a2b8"

    @dash_app.callback(
        Output("game-report-stint-events", "data"),
        Output("game-report-frame-slider", "max"),
        Output("game-report-frame-slider", "value"),
        Output("game-report-frame-slider", "marks"),
        Output("game-report-frame-index", "data", allow_duplicate=True),
        Output("game-report-playback-controls", "style"),
        Output("game-report-interval", "disabled", allow_duplicate=True),
        Output("game-report-play-btn", "children", allow_duplicate=True),
        Output("game-report-frame-delays", "data"),
        Input("game-report-selected-stint", "data"),
        State("game-report-player-id", "data"),
        State("game-report-game-id", "data"),
        State("game-report-merged-stints", "data"),
        prevent_initial_call=True,
    )
    def prepare_stint_frames(selected_stint, player_id, game_id, merged_map):
        hidden = {"display": "none", "alignItems": "center", "marginTop": "8px"}
        visible = {"display": "flex", "alignItems": "center", "marginTop": "8px"}

        if not selected_stint or not player_id or not game_id:
            return None, 0, 0, None, 0, hidden, True, "Play", []

        game = Game.query.filter_by(game_id=game_id).first()
        if not game:
            return None, 0, 0, None, 0, hidden, True, "Play", []

        # Use merged time range if available, otherwise fall back to single stint
        merged = (merged_map or {}).get(str(selected_stint))
        if merged:
            period = merged["period"]
            time_start = merged["period_time_start"]
            time_end = merged["period_time_end"]
            stint_game_id = game_id
        else:
            stint = Stint.query.get(selected_stint)
            if not stint:
                return None, 0, 0, None, 0, hidden, True, "Play", []
            period = stint.period
            time_start = stint.period_time_start
            time_end = stint.period_time_end
            stint_game_id = stint.game_id

        # Build logo map
        logo_map = {}
        center_logo = None
        if game.home_team and game.home_team.logo:
            center_logo = game.home_team.logo
            logo_map[game.home_team.source_team_id] = game.home_team.logo
        if game.away_team and game.away_team.logo:
            logo_map[game.away_team.source_team_id] = game.away_team.logo

        # Get all events during merged stint time window
        all_events = (
            Event.query.filter(
                Event.game_id == stint_game_id,
                Event.period == period,
                Event.period_time >= time_start,
                Event.period_time <= time_end,
            )
            .order_by(Event.period_time)
            .all()
        )

        # Get unique sl_event_ids preserving order, with period_time
        seen = set()
        ordered_sl_ids = []
        period_time_by_sl_id = {}
        for e in all_events:
            if e.sl_event_id and e.sl_event_id not in seen:
                seen.add(e.sl_event_id)
                ordered_sl_ids.append(e.sl_event_id)
                period_time_by_sl_id[e.sl_event_id] = e.period_time

        if not ordered_sl_ids:
            return None, 0, 0, None, 0, hidden, True, "Play", []

        # Get all tracking data for these events
        tracking_rows = Tracking.query.filter(
            Tracking.game_id == stint_game_id,
            Tracking.sl_event_id.in_(ordered_sl_ids),
        ).all()

        # Index tracking by sl_event_id
        tracking_by_event = {}
        for t in tracking_rows:
            tracking_by_event.setdefault(t.sl_event_id, []).append(t)

        # Index events by sl_event_id
        events_by_sl_id = {}
        for e in all_events:
            if e.sl_event_id:
                events_by_sl_id.setdefault(e.sl_event_id, []).append(e)

        # Build frames
        frames = []
        for sl_id in ordered_sl_ids:
            frame_events = []
            for e in events_by_sl_id.get(sl_id, []):
                if e.x is not None:
                    frame_events.append(
                        {
                            "x": e.x,
                            "y": e.y,
                            "event_type": (e.event_type or "unknown").lower(),
                            "description": e.description or "",
                            "detail": e.detail or "",
                            "flags": e.flags or "",
                            "player_id": e.player_id,
                        }
                    )

            frame_tracking = []
            for t in tracking_by_event.get(sl_id, []):
                if t.tracking_x is not None and t.tracking_y is not None:
                    last_name = ""
                    # ~31% of tracking rows have a location and team but no
                    # player identity; show them as unlabeled team markers
                    full_name = (
                        t.player_name
                        or f"Unidentified ({t.team_name or 'unknown team'})"
                    )
                    if t.player and t.player.lastName:
                        last_name = t.player.lastName
                        full_name = f"{t.player.firstName} {t.player.lastName}"
                    frame_tracking.append(
                        {
                            "tracking_x": t.tracking_x,
                            "tracking_y": t.tracking_y,
                            "team_id": t.team_id,
                            "player_id": t.player_id,
                            "player_name": full_name,
                            "last_name": last_name,
                        }
                    )

            frames.append(
                {
                    "sl_event_id": sl_id,
                    "period_time": period_time_by_sl_id.get(sl_id),
                    "events": frame_events,
                    "tracking": frame_tracking,
                }
            )

        stint_data = {
            "center_logo": center_logo,
            "logo_map": logo_map,
            "frames": frames,
        }

        max_frame = len(frames) - 1

        # Find stint boundaries within this shift
        shift_stints = []
        selected = Stint.query.get(selected_stint)
        if selected and selected.shift is not None:
            shift_stints = (
                Stint.query.filter_by(
                    player_id=selected.player_id,
                    game_id=selected.game_id,
                    shift=selected.shift,
                )
                .order_by(Stint.game_stint)
                .all()
            )

        def _closest_frame(target_time):
            closest_idx = None
            closest_dist = float("inf")
            for i, f in enumerate(frames):
                pt = f.get("period_time")
                if pt is not None:
                    dist = abs(pt - target_time)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_idx = i
            return closest_idx

        marks = {}
        boundary_style = {"color": "#dc3545", "fontWeight": "bold"}

        # Pin shift start and end to slider extremes
        first_start = shift_stints[0].period_time_start if shift_stints else None
        last_end = shift_stints[-1].period_time_end if shift_stints else None
        if first_start is not None:
            marks[0] = {
                "label": _seconds_to_mmss(first_start),
                "style": boundary_style,
            }
        if last_end is not None:
            marks[max_frame] = {
                "label": _seconds_to_mmss(last_end),
                "style": boundary_style,
            }

        # Add interior stint boundaries (skip first start and last end)
        pinned_times = {first_start, last_end}
        for s in shift_stints:
            for pt in [s.period_time_start, s.period_time_end]:
                if pt is not None and pt not in pinned_times:
                    idx = _closest_frame(pt)
                    if idx is not None and idx not in marks:
                        marks[idx] = {
                            "label": _seconds_to_mmss(pt),
                            "style": boundary_style,
                        }

        # Playback delay before advancing past each frame, scaled from the
        # real gap to the next event
        frame_delays = []
        for cur, nxt in zip(frames, frames[1:]):
            gap = (nxt["period_time"] or 0) - (cur["period_time"] or 0)
            frame_delays.append(_playback_delay_ms(gap))

        return stint_data, max_frame, 0, marks, 0, visible, True, "Play", frame_delays

    @dash_app.callback(
        Output("game-report-interval", "disabled"),
        Output("game-report-play-btn", "children"),
        Output("game-report-interval", "interval"),
        Input("game-report-play-btn", "n_clicks"),
        State("game-report-interval", "disabled"),
        State("game-report-frame-index", "data"),
        State("game-report-frame-delays", "data"),
        prevent_initial_call=True,
    )
    def toggle_play_pause(n_clicks, currently_disabled, current_frame, frame_delays):
        if not n_clicks:
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        new_disabled = not currently_disabled
        label = "Play" if new_disabled else "Pause"
        return new_disabled, label, _frame_delay(frame_delays, current_frame)

    @dash_app.callback(
        Output("game-report-frame-index", "data", allow_duplicate=True),
        Output("game-report-frame-slider", "value", allow_duplicate=True),
        Output("game-report-interval", "disabled", allow_duplicate=True),
        Output("game-report-play-btn", "children", allow_duplicate=True),
        Output("game-report-interval", "interval", allow_duplicate=True),
        Input("game-report-interval", "n_intervals"),
        State("game-report-frame-index", "data"),
        State("game-report-frame-slider", "max"),
        State("game-report-frame-delays", "data"),
        prevent_initial_call=True,
    )
    def advance_frame(n_intervals, current_frame, max_frame, frame_delays):
        if max_frame is None or max_frame == 0:
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        from dash import no_update

        if current_frame >= max_frame:
            return current_frame, current_frame, True, "Play", no_update
        next_frame = current_frame + 1
        return (
            next_frame,
            next_frame,
            no_update,
            no_update,
            _frame_delay(frame_delays, next_frame),
        )

    @dash_app.callback(
        Output("game-report-frame-index", "data"),
        Input("game-report-frame-slider", "value"),
        prevent_initial_call=True,
    )
    def slider_to_frame(value):
        return value or 0

    @dash_app.callback(
        Output("game-report-frame-index", "data", allow_duplicate=True),
        Output("game-report-frame-slider", "value", allow_duplicate=True),
        Input({"type": "stint-sub-row", "index": ALL}, "n_clicks"),
        State("game-report-stint-events", "data"),
        prevent_initial_call=True,
    )
    def sub_row_to_frame(n_clicks, stint_data):
        if not ctx.triggered_id or not any(n for n in n_clicks if n):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate

        target_time = ctx.triggered_id["index"]
        if not stint_data or not stint_data.get("frames"):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate

        # Find the frame closest to this stint's start time
        frames = stint_data["frames"]
        closest_idx = 0
        closest_dist = float("inf")
        for i, f in enumerate(frames):
            pt = f.get("period_time")
            if pt is not None:
                dist = abs(pt - target_time)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_idx = i

        return closest_idx, closest_idx

    @dash_app.callback(
        Output("game-report-rink-base", "data"),
        Input("game-report-game-id", "data"),
    )
    def build_rink_base(game_id):
        # The rink is drawn once per game; frames are layered on client-side
        if not game_id:
            return None
        center_logo = None
        game = Game.query.filter_by(game_id=game_id).first()
        if game and game.home_team and game.home_team.logo:
            center_logo = game.home_team.logo
        fig = create_rink_figure(center_logo_url=center_logo, rink_opacity=0.35)
        fig.update_layout(uirevision="rink")
        return fig.to_plotly_json()

    # Render the current frame's events and player markers on top of the
    # base rink in the browser, so playback doesn't rebuild the whole figure
    dash_app.clientside_callback(
        RENDER_FRAME_JS.replace("__EVENT_COLORS__", json.dumps(EVENT_COLORS)).replace(
            "__DEFAULT_EVENT_COLOR__", json.dumps(DEFAULT_EVENT_COLOR)
        ),
        Output("game-report-rink-graph", "figure"),
        Input("game-report-rink-base", "data"),
        Input("game-report-stint-events", "data"),
        Input("game-report-frame-index", "data"),
    )
