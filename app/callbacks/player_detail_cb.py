import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, ctx, dcc, html
from sqlalchemy import case
from sqlalchemy.orm import aliased

from app.models import Game, Player, PlayerGameStats, PlayerStats, Season, Team

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
    "Season",
    "Team",
    "GP",
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
    "xG%",
]


GAME_LOG_HEADERS = [
    "Date",
    "Opp",
    "Result",
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
        Output("player-detail-stats", "children"),
        Input("player-detail-id", "data"),
    )
    def update_stats(player_id):
        if not player_id:
            return html.Div()

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

        rows = []
        seen_seasons = set()
        for i, (ps, team_name, tid, team_logo, season_name) in enumerate(stats_list):
            row_style = (
                {"backgroundColor": "rgb(245, 245, 245)"}
                if i % 2 == 1
                else {"backgroundColor": "rgb(255, 255, 255)"}
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
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "padding": "4px 8px",
                    "width": "100%",
                    "height": "100%",
                    "boxSizing": "border-box",
                },
            )
            # Only show season name on the first row for that season
            display_season = season_name if season_name not in seen_seasons else ""
            seen_seasons.add(season_name)
            values = [
                ps.games_played,
                ps.goals,
                ps.assists,
                ps.points,
                ps.shots,
                _fmt_pct(ps.shooting_pct),
                ps.faceoffs_won,
                ps.faceoffs_lost,
                _fmt_pct(ps.faceoff_pct),
                ps.penalties,
                ps.penalties_drawn,
                ps.blocks,
                ps.checks,
                ps.i_xg,
                ps.oi_xgf,
                ps.oi_xga,
                _fmt_pct(ps.xg_percentage),
            ]
            cells = [
                html.Td(display_season, style=CELL_STYLE),
                html.Td(
                    team_link, style={**CELL_STYLE, "padding": "0", "textAlign": "left"}
                ),
            ] + [html.Td(v, style=CELL_STYLE) for v in values]
            rows.append(html.Tr(cells, style=row_style))
        tbody = html.Tbody(rows)

        return html.Table(
            [thead, tbody],
            style={"overflowX": "auto", "width": "100%", "borderCollapse": "collapse"},
        )

    @dash_app.callback(
        Output("player-detail-game-log", "children"),
        Input("player-detail-id", "data"),
    )
    def update_game_log(player_id):
        if not player_id:
            return html.Div()

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

        rows = []
        for i, (
            pgs,
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
                {"backgroundColor": "rgb(245, 245, 245)"}
                if i % 2 == 1
                else {"backgroundColor": "rgb(255, 255, 255)"}
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
            prefix = "vs." if is_home else "@"
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
                    prefix,
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
                    "padding": "4px 8px",
                },
            )

            date_str = game_date.strftime("%Y-%m-%d") if game_date else ""

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
                pgs.i_xg,
                pgs.oi_xgf,
                pgs.oi_xga,
            ]
            cells = [
                html.Td(date_str, style=CELL_STYLE),
                html.Td(
                    opp_cell,
                    style={**CELL_STYLE, "padding": "0", "textAlign": "left"},
                ),
                html.Td(result, style=CELL_STYLE),
            ] + [html.Td(v, style=CELL_STYLE) for v in values]
            rows.append(
                html.Tr(
                    cells,
                    style=row_style,
                    className="game-log-row",
                    id={"type": "game-log-row", "index": f"{player_id}_{pgs.game_id}"},
                    n_clicks=0,
                )
            )

        tbody = html.Tbody(rows)
        table = html.Table(
            [thead, tbody],
            style={"overflowX": "auto", "width": "100%", "borderCollapse": "collapse"},
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
