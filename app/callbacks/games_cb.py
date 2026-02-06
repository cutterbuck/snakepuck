from dash import Input, Output

from app.models import Game, Team


def register_games_callbacks(dash_app):
    @dash_app.callback(
        Output("games-team-filter", "options"),
        Input("url", "pathname"),
    )
    def populate_team_filter(pathname):
        teams = Team.query.order_by(Team.name).all()
        return [{"label": t.name, "value": t.id} for t in teams]

    @dash_app.callback(
        Output("games-table", "data"),
        Input("games-team-filter", "value"),
    )
    def update_games(team_id):
        query = Game.query.order_by(Game.date.desc())

        if team_id:
            query = query.filter(
                (Game.home_team_id == team_id) | (Game.away_team_id == team_id)
            )

        games = query.all()
        rows = []
        for g in games:
            home_name = g.home_team.name if g.home_team else str(g.home_team_id)
            away_name = g.away_team.name if g.away_team else str(g.away_team_id)
            is_overtime = g.last_period and g.last_period > 3
            result = "OT" if is_overtime else "REG"
            rows.append(
                {
                    "date": g.date.strftime("%Y-%m-%d"),
                    "home": home_name,
                    "away": away_name,
                    "score": f"{g.home_team_score} - {g.away_team_score}",
                    "result": result,
                }
            )
        return rows
