from dash import ALL, Input, Output, State, ctx, dcc, html
from sqlalchemy import case
from sqlalchemy.orm import aliased

from app.models import Game, Player, PlayerGameStats, Stint, Team
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
            row_style = (
                {"backgroundColor": "rgb(245, 245, 245)"}
                if i % 2 == 1
                else {"backgroundColor": "rgb(255, 255, 255)"}
            )
            cls = "stint-row selected" if is_selected else "stint-row"
            cells = [
                html.Td(stint.period_time_start or "", style=CELL_STYLE),
                html.Td(stint.period_time_end or "", style=CELL_STYLE),
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

    @dash_app.callback(
        Output("game-report-rink", "children"),
        Input("game-report-player-id", "data"),
        Input("game-report-game-id", "data"),
    )
    def update_game_report_rink(player_id, game_id):
        if not player_id or not game_id:
            return html.Div()

        fig = create_rink_figure()

        return dcc.Graph(
            figure=fig,
            config={"staticPlot": True},
            style={"width": "100%"},
        )
