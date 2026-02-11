import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

from app.models import Player, PlayerStats, Team

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
    "xG",
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
        Output("player-detail-back", "children"),
        Input("player-detail-id", "data"),
    )
    def update_back_button(player_id):
        if not player_id:
            return dcc.Link(
                "Back to Standings",
                href="/",
                className="btn btn-secondary btn-sm",
            )
        player = Player.query.get(player_id)
        if not player:
            return dcc.Link(
                "Back to Standings",
                href="/",
                className="btn btn-secondary btn-sm",
            )
        # Find the player's primary team (most games played) via PlayerStats
        ps = (
            PlayerStats.query.filter_by(player_id=player.playerId)
            .order_by(PlayerStats.games_played.desc())
            .first()
        )
        if not ps or not ps.team:
            return dcc.Link(
                "Back to Standings",
                href="/",
                className="btn btn-secondary btn-sm",
            )
        return dcc.Link(
            f"Back to {ps.team.name}",
            href=f"/team/{ps.team_id}",
            className="btn btn-secondary btn-sm",
        )

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

        # Get primary team (most games played) via PlayerStats
        ps = (
            PlayerStats.query.filter_by(player_id=player.playerId)
            .order_by(PlayerStats.games_played.desc())
            .first()
        )
        team = ps.team if ps else None

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
            .add_columns(Team.name.label("team_name"))
            .order_by(PlayerStats.games_played.desc())
            .all()
        )
        if not stats_list:
            return html.Div("No stats available.", style={"color": "#666"})

        header_cells = [html.Th(h, style=HEADER_STYLE) for h in STAT_HEADERS]
        thead = html.Thead(html.Tr(header_cells))

        rows = []
        for i, (ps, team_name) in enumerate(stats_list):
            row_style = (
                {"backgroundColor": "rgb(245, 245, 245)"}
                if i % 2 == 1
                else {"backgroundColor": "rgb(255, 255, 255)"}
            )
            values = [
                team_name,
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
                ps.xg,
            ]
            cells = [html.Td(v, style=CELL_STYLE) for v in values]
            rows.append(html.Tr(cells, style=row_style))
        tbody = html.Tbody(rows)

        return html.Table(
            [thead, tbody],
            style={"overflowX": "auto", "width": "100%", "borderCollapse": "collapse"},
        )
