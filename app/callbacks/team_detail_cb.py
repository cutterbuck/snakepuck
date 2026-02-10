from dash import Input, Output, html

from app.models import Player, PlayerStats, Team


def register_team_detail_callbacks(dash_app):
    @dash_app.callback(
        Output("team-detail-id", "data"),
        Input("url", "pathname"),
    )
    def store_team_id(pathname):
        if pathname and pathname.startswith("/team/"):
            try:
                return int(pathname.split("/team/")[1])
            except (ValueError, IndexError):
                return None
        return None

    @dash_app.callback(
        Output("team-detail-header", "children"),
        Input("team-detail-id", "data"),
    )
    def update_header(team_id):
        if not team_id:
            return html.Div()
        team = Team.query.get(team_id)
        if not team:
            return html.H2("Team not found")
        children = []
        if team.logo:
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
                team.name,
                style={
                    "fontSize": "24px",
                    "fontWeight": "bold",
                    "verticalAlign": "middle",
                },
            )
        )
        return html.Div(children, style={"display": "flex", "alignItems": "center"})

    @dash_app.callback(
        Output("team-detail-table", "data"),
        Input("team-detail-id", "data"),
    )
    def update_roster(team_id):
        if not team_id:
            return []

        results = (
            PlayerStats.query.join(Player, PlayerStats.player_id == Player.playerId)
            .filter(Player.team_id == team_id)
            .add_columns(Player.firstName, Player.lastName, Player.position)
            .order_by(PlayerStats.points.desc(), PlayerStats.goals.desc())
            .all()
        )

        rows = []
        for ps, first_name, last_name, pos in results:
            rows.append(
                {
                    "name": f"{first_name} {last_name}",
                    "age": ps.age,
                    "position": pos,
                    "gp": ps.games_played,
                    "goals": ps.goals,
                    "assists": ps.assists,
                    "points": ps.points,
                    "shots": ps.shots,
                    "shooting_pct": ps.shooting_pct,
                    "fow": ps.faceoffs_won,
                    "fol": ps.faceoffs_lost,
                    "fo_pct": ps.faceoff_pct,
                    "penalties": ps.penalties,
                    "penalties_drawn": ps.penalties_drawn,
                    "blocks": ps.blocks,
                    "checks": ps.checks,
                    "xg": ps.xg,
                }
            )
        return rows
