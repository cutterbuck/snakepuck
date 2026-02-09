from dash import Input, Output

from app.models import Player, Team


def register_players_callbacks(dash_app):
    @dash_app.callback(
        Output("players-team-filter", "options"),
        Input("url", "pathname"),
    )
    def populate_team_filter(pathname):
        teams = Team.query.order_by(Team.abbrev).all()
        return [{"label": t.abbrev, "value": t.id} for t in teams]

    @dash_app.callback(
        Output("players-table", "data"),
        [
            Input("players-team-filter", "value"),
            Input("players-position-filter", "value"),
        ],
    )
    def update_players(team_id, position):
        query = Player.query.join(Team)

        if team_id:
            query = query.filter(Player.team_id == team_id)
        if position:
            query = query.filter(Player.position == position)

        query = query.order_by(Player.lastName, Player.firstName)
        players = query.all()

        rows = []
        for p in players:
            rows.append(
                {
                    "name": f"{p.firstName} {p.lastName}",
                    "team": p.team,
                    "position": p.position,
                    "nationality": p.nationality,
                    "birthDate": p.birthDate,
                    "height": p.height,
                    "weight": p.weight,
                    "shootsCatches": p.shootsCatches,
                }
            )
        return rows
