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
        if not player or not player.team_rel:
            return dcc.Link(
                "Back to Standings",
                href="/",
                className="btn btn-secondary btn-sm",
            )
        return dcc.Link(
            f"Back to {player.team_rel.name}",
            href=f"/team/{player.team_id}",
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

        children = []
        if player.team_rel and player.team_rel.logo:
            children.append(
                html.Img(
                    src=player.team_rel.logo,
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
        if player.team_rel:
            info_parts.append(player.team_rel.name)
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
        ps = PlayerStats.query.filter_by(player_id=player.playerId).first()
        if not ps:
            return html.Div("No stats available.", style={"color": "#666"})

        header_cells = [html.Th(h, style=HEADER_STYLE) for h in STAT_HEADERS]
        thead = html.Thead(html.Tr(header_cells))

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
            ps.xg,
        ]
        cells = [html.Td(v, style=CELL_STYLE) for v in values]
        tbody = html.Tbody([html.Tr(cells)])

        return html.Table(
            [thead, tbody],
            style={"overflowX": "auto", "width": "100%", "borderCollapse": "collapse"},
        )
