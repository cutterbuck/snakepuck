import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, ctx, dcc, html
from sqlalchemy import case
from sqlalchemy.orm import aliased

from app.models import Game, Player, PlayerGameStats, PlayerStats, Season, Team

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
    "Season",
    "Team",
    "GP",
    "ATOI",
    "G",
    "A",
    "PTS",
    "S",
    "S%",
    "FOW",
    "FOL",
    "FO%",
    "BLK",
    "HIT",
    "ixG",
    "oixGF",
    "oixGA",
    "xG%",
]


GAME_LOG_HEADERS = [
    "Date",
    "Opp",
    "Result",
    "TOI",
    "G",
    "A",
    "PTS",
    "S",
    "S%",
    "FOW",
    "FOL",
    "FO%",
    "BLK",
    "HIT",
    "ixG",
    "oixGF",
    "oixGA",
    "xG%",
]

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


def _fmt_pct(val):
    if val is None:
        return ""
    return f"{val:.3f}"


def _seconds_to_mmss(seconds):
    """Convert seconds (float) to M:SS format."""
    if seconds is None:
        return ""
    total = int(seconds)
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


def register_player_detail_callbacks(dash_app):
    @dash_app.callback(
        Output("player-detail-id", "data"),
        Input("url", "pathname"),
    )
    def store_player_id(pathname):
        if pathname and pathname.startswith("/player/"):
            try:
                return int(pathname.split("/player/")[1])
            except (ValueError, IndexError):
                return None
        return None

    @dash_app.callback(
        Output("player-detail-header", "children"),
        Input("player-detail-id", "data"),
    )
    def update_header(player_id):
        if not player_id:
            return html.Div()
        player = Player.query.get(player_id)
        if not player:
            return html.H2("Player not found")

        # Get most recent team via the player's latest game
        latest_pgs = (
            PlayerGameStats.query.filter_by(player_id=player.playerId)
            .join(Game, PlayerGameStats.game_id == Game.game_id)
            .order_by(Game.date.desc())
            .first()
        )
        team = latest_pgs.team if latest_pgs else None

        children = []
        if team and team.logo:
            children.append(
                html.Img(
                    src=team.logo,
                    style={
                        "width": "48px",
                        "height": "48px",
                        "verticalAlign": "middle",
                        "marginRight": "12px",
                    },
                )
            )
        children.append(
            html.Span(
                f"{player.firstName} {player.lastName}",
                style={
                    "fontSize": "24px",
                    "fontWeight": "bold",
                    "verticalAlign": "middle",
                },
            )
        )
        info_parts = []
        if player.position:
            info_parts.append(player.position)
        if team:
            info_parts.append(team.name)
        if info_parts:
            children.append(
                html.Span(
                    f"  |  {' | '.join(info_parts)}",
                    style={
                        "fontSize": "16px",
                        "color": "#666",
                        "verticalAlign": "middle",
                        "marginLeft": "8px",
                    },
                )
            )

        return html.Div(children, style={"display": "flex", "alignItems": "center"})

    @dash_app.callback(
        Output("player-detail-situation-toggle", "children"),
        Input("player-detail-id", "data"),
        Input("player-detail-situation", "data"),
    )
    def update_situation_toggle(player_id, selected_situation):
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
                    id={"type": "situation-btn", "index": value},
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
        Output("player-detail-situation", "data"),
        Input({"type": "situation-btn", "index": ALL}, "n_clicks"),
        State("player-detail-situation", "data"),
        prevent_initial_call=True,
    )
    def toggle_situation(n_clicks, current_situation):
        if not ctx.triggered_id or not any(n for n in n_clicks if n):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        return ctx.triggered_id["index"]

    @dash_app.callback(
        Output("player-detail-stats", "children"),
        Input("player-detail-id", "data"),
        Input("player-detail-situation", "data"),
    )
    def update_stats(player_id, situation=None):
        if not player_id:
            return html.Div()

        prefix = situation or "tot"

        player = Player.query.get(player_id)
        if not player:
            return html.Div("No stats available.", style={"color": "#666"})

        stats_list = (
            PlayerStats.query.filter_by(player_id=player.playerId)
            .join(Team, PlayerStats.team_id == Team.id)
            .join(Season, PlayerStats.season_id == Season.id)
            .add_columns(
                Team.name.label("team_name"),
                Team.id.label("tid"),
                Team.logo.label("team_logo"),
                Season.name.label("season_name"),
            )
            .order_by(Season.name, PlayerStats.games_played.desc())
            .all()
        )
        if not stats_list:
            return html.Div("No stats available.", style={"color": "#666"})

        header_cells = [html.Th(h, style=HEADER_STYLE) for h in STAT_HEADERS]
        thead = html.Thead(html.Tr(header_cells))

        stat_cols = [html.Col(style={"width": "80px"}), html.Col(style={"width": "180px"})]
        for _ in STAT_HEADERS[2:]:
            stat_cols.append(html.Col(style={"width": STAT_COL_WIDTH}))
        colgroup = html.Colgroup(stat_cols)

        rows = []
        seen_seasons = set()
        for i, (ps, team_name, tid, team_logo, season_name) in enumerate(stats_list):
            row_style = (
                {"backgroundColor": "#e8f4fb"}
                if i % 2 == 1
                else {"backgroundColor": "#ffffff"}
            )
            team_children = []
            if team_logo:
                team_children.append(
                    html.Img(
                        src=team_logo,
                        style={
                            "width": "24px",
                            "height": "24px",
                            "verticalAlign": "middle",
                        },
                    )
                )
            team_children.append(
                html.Span(
                    team_name,
                    style={"paddingLeft": "8px", "verticalAlign": "middle"},
                )
            )
            team_link = dcc.Link(
                html.Div(
                    team_children,
                    style={"display": "flex", "alignItems": "center"},
                ),
                href=f"/team/{tid}/{season_name}",
                className="team-link",
            )
            # Only show season name on the first row for that season
            display_season = season_name if season_name not in seen_seasons else ""
            seen_seasons.add(season_name)
            values = [
                ps.games_played,
                _seconds_to_mmss(getattr(ps, f"{prefix}_atoi")),
                getattr(ps, f"{prefix}_goals"),
                getattr(ps, f"{prefix}_assists"),
                getattr(ps, f"{prefix}_points"),
                getattr(ps, f"{prefix}_shots"),
                _fmt_pct(getattr(ps, f"{prefix}_shooting_pct")),
                getattr(ps, f"{prefix}_faceoffs_won"),
                getattr(ps, f"{prefix}_faceoffs_lost"),
                _fmt_pct(getattr(ps, f"{prefix}_faceoff_pct")),
                getattr(ps, f"{prefix}_blocks"),
                getattr(ps, f"{prefix}_checks"),
                getattr(ps, f"{prefix}_i_xg"),
                getattr(ps, f"{prefix}_oi_xgf"),
                getattr(ps, f"{prefix}_oi_xga"),
                _fmt_pct(getattr(ps, f"{prefix}_xg_pct")),
            ]
            cells = [
                html.Td(display_season, style=CELL_STYLE),
                html.Td(
                    team_link, style={**CELL_STYLE, "textAlign": "left"}
                ),
            ] + [html.Td(v, style=CELL_STYLE) for v in values]
            rows.append(html.Tr(cells, style=row_style))
        tbody = html.Tbody(rows)

        return html.Table(
            [colgroup, thead, tbody],
            style=TABLE_STYLE,
        )

    @dash_app.callback(
        Output("player-detail-game-log", "children"),
        Input("player-detail-id", "data"),
        Input("player-detail-situation", "data"),
    )
    def update_game_log(player_id, situation=None):
        if not player_id:
            return html.Div()

        prefix = situation or "tot"

        player = Player.query.get(player_id)
        if not player:
            return html.Div()

        OppTeam = aliased(Team)

        results = (
            PlayerGameStats.query.filter_by(player_id=player.playerId)
            .join(Game, PlayerGameStats.game_id == Game.game_id)
            .join(Team, PlayerGameStats.team_id == Team.id)
            .outerjoin(
                OppTeam,
                case(
                    (
                        PlayerGameStats.team_id == Game.home_team_id,
                        Game.away_team_id,
                    ),
                    else_=Game.home_team_id,
                )
                == OppTeam.id,
            )
            .add_columns(
                Game.id.label("game_pk"),
                Game.date,
                Game.home_score,
                Game.away_score,
                Game.game_outcome,
                Game.home_team_id,
                Team.logo.label("team_logo"),
                OppTeam.name.label("opp_name"),
                OppTeam.logo.label("opp_logo"),
                OppTeam.id.label("opp_id"),
                OppTeam.abbrev.label("opp_abbrev"),
            )
            .order_by(Game.date.desc())
            .all()
        )

        if not results:
            return html.Div()

        header_cells = [html.Th(h, style=HEADER_STYLE) for h in GAME_LOG_HEADERS]
        thead = html.Thead(html.Tr(header_cells))

        gl_cols = [
            html.Col(style={"width": "110px"}),  # Date
            html.Col(style={"width": "160px"}),   # Opp
            html.Col(style={"width": "90px"}),    # Result
        ]
        for _ in GAME_LOG_HEADERS[3:]:
            gl_cols.append(html.Col(style={"width": STAT_COL_WIDTH}))
        gl_colgroup = html.Colgroup(gl_cols)

        rows = []
        for i, (
            pgs,
            game_pk,
            game_date,
            home_score,
            away_score,
            game_outcome,
            home_team_id,
            team_logo,
            opp_name,
            opp_logo,
            opp_id,
            opp_abbrev,
        ) in enumerate(results):
            row_style = (
                {"backgroundColor": "#e8f4fb"}
                if i % 2 == 1
                else {"backgroundColor": "#ffffff"}
            )

            # Determine result
            is_home = pgs.team_id == home_team_id
            player_score = home_score if is_home else away_score
            opp_score = away_score if is_home else home_score
            outcome_str = (game_outcome or "").lower()
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

            # Opponent cell: player's team logo, vs./@, opp logo + abbreviation
            opp_prefix = "vs." if is_home else "@"
            opp_children = []
            if team_logo:
                opp_children.append(
                    html.Img(
                        src=team_logo,
                        style={
                            "width": "24px",
                            "height": "24px",
                            "verticalAlign": "middle",
                            "marginRight": "6px",
                        },
                    )
                )
            opp_children.append(
                html.Span(
                    opp_prefix,
                    style={"marginRight": "6px", "verticalAlign": "middle"},
                ),
            )
            if opp_logo:
                opp_children.append(
                    html.Img(
                        src=opp_logo,
                        style={
                            "width": "24px",
                            "height": "24px",
                            "verticalAlign": "middle",
                        },
                    )
                )
            opp_children.append(
                html.Span(
                    opp_abbrev or "",
                    style={"paddingLeft": "6px", "verticalAlign": "middle"},
                )
            )
            opp_cell = html.Div(
                opp_children,
                style={
                    "display": "flex",
                    "alignItems": "center",
                },
            )

            date_str = game_date.strftime("%Y-%m-%d") if game_date else ""

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
                getattr(pgs, f"{prefix}_blocks"),
                getattr(pgs, f"{prefix}_checks"),
                getattr(pgs, f"{prefix}_i_xg"),
                getattr(pgs, f"{prefix}_oi_xgf"),
                getattr(pgs, f"{prefix}_oi_xga"),
                _fmt_pct(
                    round(
                        getattr(pgs, f"{prefix}_oi_xgf")
                        / (
                            getattr(pgs, f"{prefix}_oi_xgf")
                            + getattr(pgs, f"{prefix}_oi_xga")
                        ),
                        3,
                    )
                    if (getattr(pgs, f"{prefix}_oi_xgf") or 0)
                    + (getattr(pgs, f"{prefix}_oi_xga") or 0)
                    > 0
                    else None
                ),
            ]
            cells = [
                html.Td(date_str, style={**CELL_STYLE, "whiteSpace": "nowrap"}),
                html.Td(
                    opp_cell,
                    style={**CELL_STYLE, "textAlign": "left"},
                ),
                html.Td(result, style=CELL_STYLE),
            ] + [html.Td(v, style=CELL_STYLE) for v in values]
            rows.append(
                html.Tr(
                    cells,
                    style=row_style,
                    className="game-log-row",
                    id={"type": "game-log-row", "index": f"{player_id}_{game_pk}"},
                    n_clicks=0,
                )
            )

        tbody = html.Tbody(rows)
        table = html.Table(
            [gl_colgroup, thead, tbody],
            style=TABLE_STYLE,
        )

        return html.Div([html.H4("Game Log"), table])

    @dash_app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Input({"type": "game-log-row", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def navigate_to_game_report(n_clicks):
        if not ctx.triggered_id or not any(n for n in n_clicks if n):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        row_id = ctx.triggered_id["index"]
        player_id, game_id = row_id.split("_", 1)
        return f"/player/{player_id}/game/{game_id}"
