from dash import ALL, Input, Output, State, ctx, dcc, html
from sqlalchemy import case
from sqlalchemy.orm import aliased

from app.models import Event, Game, Player, PlayerGameStats, Stint, Team, Tracking
from app.utils.rink import create_rink_figure

HEADER_STYLE = {
    "backgroundColor": "#343a40",
    "color": "white",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "4px 8px",
}

CELL_STYLE = {
    "textAlign": "center",
    "padding": "4px 8px",
}

STAT_HEADERS = [
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
    "xG",
]


def _fmt_pct(val):
    if val is None:
        return ""
    return f"{val:.3f}"


def register_game_report_callbacks(dash_app):
    @dash_app.callback(
        Output("game-report-player-id", "data"),
        Output("game-report-game-id", "data"),
        Output("game-report-back-link", "href"),
        Output("game-report-back-link", "children"),
        Input("url", "pathname"),
    )
    def store_game_report_ids(pathname):
        if pathname and "/game/" in pathname:
            try:
                # URL: /player/{player_id}/game/{game_id}
                parts = pathname.strip("/").split("/")
                # parts: ["player", player_id, "game", game_id]
                player_id = int(parts[1])
                game_id = parts[3]
                player = Player.query.get(player_id)
                if player:
                    label = f"Back to {player.firstName} {player.lastName}"
                else:
                    label = "Back to Player"
                return player_id, game_id, f"/player/{player_id}", label
            except (ValueError, IndexError):
                return None, None, "/", "Back to Player"
        return None, None, "/", "Back to Player"

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
        Output("game-report-stats", "children"),
        Input("game-report-player-id", "data"),
        Input("game-report-game-id", "data"),
    )
    def update_game_report_stats(player_id, game_id):
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

        header_cells = [html.Th(h, style=HEADER_STYLE) for h in STAT_HEADERS]
        thead = html.Thead(html.Tr(header_cells))

        values = [
            pgs.goals,
            pgs.assists,
            pgs.points,
            pgs.shots,
            _fmt_pct(pgs.shooting_pct),
            pgs.faceoffs_won,
            pgs.faceoffs_lost,
            _fmt_pct(pgs.faceoff_pct),
            pgs.penalties,
            pgs.penalties_drawn,
            pgs.blocks,
            pgs.checks,
            pgs.xg,
        ]
        cells = [html.Td(v, style=CELL_STYLE) for v in values]
        row = html.Tr(cells, style={"backgroundColor": "rgb(255, 255, 255)"})
        tbody = html.Tbody([row])

        table = html.Table(
            [thead, tbody],
            style={
                "overflowX": "auto",
                "width": "100%",
                "borderCollapse": "collapse",
            },
        )

        return html.Div([table], className="mt-3")

    STINT_HEADERS = [
        "Start",
        "End",
        "Home Skaters",
        "Away Skaters",
        "Home Net Empty",
        "Away Net Empty",
        "Score",
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
    )
    def update_stints_header(selected_period):
        buttons = []
        for p in [1, 2, 3]:
            active = selected_period == p
            style = {
                **PERIOD_BTN_BASE,
                "backgroundColor": "#0d6efd" if active else "#fff",
                "color": "#fff" if active else "#333",
                "borderRadius": "4px 0 0 4px"
                if p == 1
                else ("0 4px 4px 0" if p == 3 else "0"),
            }
            buttons.append(
                html.Button(
                    str(p),
                    id={"type": "stint-period-btn", "index": p},
                    n_clicks=0,
                    style=style,
                )
            )

        return html.Div(
            [
                html.H4("Stints", style={"marginRight": "32px", "marginBottom": "0"}),
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
            style={"display": "flex", "alignItems": "baseline"},
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
        Input("game-report-player-id", "data"),
        Input("game-report-game-id", "data"),
        Input("game-report-stint-period", "data"),
        Input("game-report-selected-stint", "data"),
    )
    def update_game_report_stints(player_id, game_id, selected_period, selected_stint):
        if not player_id or not game_id:
            return html.Div()

        player = Player.query.get(player_id)
        if not player:
            return html.Div()

        query = Stint.query.filter_by(player_id=player.playerId, game_id=game_id)
        if selected_period is not None:
            query = query.filter_by(period=selected_period)
        stints = query.order_by(Stint.game_stint).all()

        if not stints:
            return html.Div("No stints found.", style={"color": "#666"})

        # Find which game_stints have event data for this player
        stints_with_events = set(
            row.game_stint
            for row in (
                Event.query.filter_by(
                    game_id=game_id,
                    player_id=player.playerId,
                )
                .with_entities(Event.game_stint)
                .distinct()
                .all()
            )
            if row.game_stint is not None
        )

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
        for i, stint in enumerate(stints):
            is_selected = stint.id == selected_stint
            has_tracking = stint.game_stint in stints_with_events
            row_bg = (
                {"backgroundColor": "rgb(245, 245, 245)"}
                if i % 2 == 1
                else {"backgroundColor": "rgb(255, 255, 255)"}
            )
            row_style = {**row_bg, "fontWeight": "bold"} if has_tracking else row_bg
            cls = "stint-row selected" if is_selected else "stint-row"
            cells = [
                html.Td(
                    f"{stint.period_time_start:.2f}"
                    if stint.period_time_start is not None
                    else "",
                    style=CELL_STYLE,
                ),
                html.Td(
                    f"{stint.period_time_end:.2f}"
                    if stint.period_time_end is not None
                    else "",
                    style=CELL_STYLE,
                ),
                html.Td(stint.n_home_skaters, style=CELL_STYLE),
                html.Td(stint.n_away_skaters, style=CELL_STYLE),
                html.Td("Yes" if stint.is_home_net_empty else "No", style=CELL_STYLE),
                html.Td("Yes" if stint.is_away_net_empty else "No", style=CELL_STYLE),
                html.Td(
                    f"{stint.home_score}-{stint.away_score}"
                    if stint.home_score is not None
                    else "",
                    style=CELL_STYLE,
                ),
            ]
            rows.append(
                html.Tr(
                    cells,
                    style=row_style,
                    className=cls,
                    id={"type": "stint-row", "index": stint.id},
                    n_clicks=0,
                )
            )

        tbody = html.Tbody(rows)
        table = html.Table(
            [thead, tbody],
            style={
                "width": "100%",
                "borderCollapse": "collapse",
            },
        )

        return html.Div(
            table,
            className="stints-scroll-container",
            style={
                "maxHeight": "335px",
                "overflowX": "auto",
            },
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
        Output("game-report-frame-index", "data", allow_duplicate=True),
        Output("game-report-playback-controls", "style"),
        Output("game-report-interval", "disabled", allow_duplicate=True),
        Output("game-report-play-btn", "children", allow_duplicate=True),
        Input("game-report-selected-stint", "data"),
        State("game-report-player-id", "data"),
        State("game-report-game-id", "data"),
        prevent_initial_call=True,
    )
    def prepare_stint_frames(selected_stint, player_id, game_id):
        hidden = {"display": "none", "alignItems": "center", "marginTop": "8px"}
        visible = {"display": "flex", "alignItems": "center", "marginTop": "8px"}

        if not selected_stint or not player_id or not game_id:
            return None, 0, 0, 0, hidden, True, "Play"

        game = Game.query.filter_by(game_id=game_id).first()
        if not game:
            return None, 0, 0, 0, hidden, True, "Play"

        stint = Stint.query.get(selected_stint)
        if not stint:
            return None, 0, 0, 0, hidden, True, "Play"

        # Build logo map
        logo_map = {}
        center_logo = None
        if game.home_team and game.home_team.logo:
            center_logo = game.home_team.logo
            logo_map[game.home_team.source_team_id] = game.home_team.logo
        if game.away_team and game.away_team.logo:
            logo_map[game.away_team.source_team_id] = game.away_team.logo

        # Get all events during stint time window
        all_events = (
            Event.query.filter(
                Event.game_id == stint.game_id,
                Event.period == stint.period,
                Event.period_time >= stint.period_time_start,
                Event.period_time <= stint.period_time_end,
            )
            .order_by(Event.period_time)
            .all()
        )

        # Get unique sl_event_ids preserving order
        seen = set()
        ordered_sl_ids = []
        for e in all_events:
            if e.sl_event_id and e.sl_event_id not in seen:
                seen.add(e.sl_event_id)
                ordered_sl_ids.append(e.sl_event_id)

        if not ordered_sl_ids:
            return None, 0, 0, 0, hidden, True, "Play"

        # Get all tracking data for these events
        tracking_rows = Tracking.query.filter(
            Tracking.game_id == stint.game_id,
            Tracking.sl_event_id.in_(ordered_sl_ids),
            Tracking.player_id.isnot(None),
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
                if e.x_adj is not None:
                    frame_events.append(
                        {
                            "x_adj": e.x_adj,
                            "y_adj": e.y_adj,
                            "event_type": (e.event_type or "unknown").lower(),
                            "description": e.description or "",
                        }
                    )

            frame_tracking = []
            for t in tracking_by_event.get(sl_id, []):
                if t.tracking_x is not None and t.tracking_y is not None:
                    frame_tracking.append(
                        {
                            "tracking_x": t.tracking_x,
                            "tracking_y": t.tracking_y,
                            "team_id": t.team_id,
                            "player_name": t.player_name or "",
                        }
                    )

            frames.append(
                {
                    "sl_event_id": sl_id,
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
        return stint_data, max_frame, 0, 0, visible, True, "Play"

    @dash_app.callback(
        Output("game-report-interval", "disabled"),
        Output("game-report-play-btn", "children"),
        Input("game-report-play-btn", "n_clicks"),
        State("game-report-interval", "disabled"),
        prevent_initial_call=True,
    )
    def toggle_play_pause(n_clicks, currently_disabled):
        if not n_clicks:
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        new_disabled = not currently_disabled
        label = "Play" if new_disabled else "Pause"
        return new_disabled, label

    @dash_app.callback(
        Output("game-report-frame-index", "data", allow_duplicate=True),
        Output("game-report-frame-slider", "value", allow_duplicate=True),
        Output("game-report-interval", "disabled", allow_duplicate=True),
        Output("game-report-play-btn", "children", allow_duplicate=True),
        Input("game-report-interval", "n_intervals"),
        State("game-report-frame-index", "data"),
        State("game-report-frame-slider", "max"),
        prevent_initial_call=True,
    )
    def advance_frame(n_intervals, current_frame, max_frame):
        if max_frame is None or max_frame == 0:
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        from dash import no_update

        if current_frame >= max_frame:
            return current_frame, current_frame, True, "Play"
        next_frame = current_frame + 1
        return next_frame, next_frame, no_update, no_update

    @dash_app.callback(
        Output("game-report-frame-index", "data"),
        Input("game-report-frame-slider", "value"),
        prevent_initial_call=True,
    )
    def slider_to_frame(value):
        return value or 0

    @dash_app.callback(
        Output("game-report-rink", "children"),
        Input("game-report-player-id", "data"),
        Input("game-report-game-id", "data"),
        Input("game-report-stint-events", "data"),
        Input("game-report-frame-index", "data"),
    )
    def update_game_report_rink(player_id, game_id, stint_data, frame_index):
        if not player_id or not game_id:
            return html.Div()

        import plotly.graph_objects as go

        # Get center logo
        center_logo = None
        if stint_data and stint_data.get("center_logo"):
            center_logo = stint_data["center_logo"]
        else:
            game = Game.query.filter_by(game_id=game_id).first()
            if game and game.home_team and game.home_team.logo:
                center_logo = game.home_team.logo

        fig = create_rink_figure(center_logo_url=center_logo)

        # If stint data exists, render the current frame
        if stint_data and stint_data.get("frames"):
            frames = stint_data["frames"]
            idx = frame_index or 0
            if idx >= len(frames):
                idx = 0
            frame = frames[idx]
            logo_map = stint_data.get("logo_map", {})

            # Render events for this frame
            if frame.get("events"):
                events_by_type = {}
                for ev in frame["events"]:
                    et = ev["event_type"]
                    events_by_type.setdefault(et, []).append(ev)

                for et, evs in events_by_type.items():
                    fig.add_trace(
                        go.Scatter(
                            x=[e["x_adj"] for e in evs],
                            y=[e["y_adj"] for e in evs],
                            mode="markers",
                            marker=dict(
                                size=8,
                                color=EVENT_COLORS.get(et, DEFAULT_EVENT_COLOR),
                                opacity=0.8,
                                line=dict(width=1, color="white"),
                            ),
                            hoverinfo="text",
                            text=[f"{et}: {e['description']}" for e in evs],
                            name=et,
                            showlegend=True,
                        )
                    )

            # Render tracking logos for this frame
            if frame.get("tracking"):
                for t in frame["tracking"]:
                    logo = logo_map.get(t["team_id"])
                    if logo:
                        fig.add_layout_image(
                            source=logo,
                            xref="x",
                            yref="y",
                            x=t["tracking_x"],
                            y=t["tracking_y"],
                            xanchor="center",
                            yanchor="middle",
                            sizex=5,
                            sizey=5,
                            layer="above",
                        )

                # Invisible scatter for hover
                fig.add_trace(
                    go.Scatter(
                        x=[t["tracking_x"] for t in frame["tracking"]],
                        y=[t["tracking_y"] for t in frame["tracking"]],
                        mode="markers",
                        marker=dict(size=10, opacity=0),
                        hoverinfo="text",
                        text=[t["player_name"] for t in frame["tracking"]],
                        showlegend=False,
                    )
                )

        return dcc.Graph(
            figure=fig,
            config={"displayModeBar": False},
            style={"width": "100%"},
        )
