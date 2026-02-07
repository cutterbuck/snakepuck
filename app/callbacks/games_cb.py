from dash import Input, Output

from app.models import Game


def register_games_callbacks(dash_app):
    @dash_app.callback(
        Output("games-table", "data"),
        Input("url", "pathname"),
    )
    def update_games(pathname):
        games = Game.query.order_by(Game.date.desc()).all()
        rows = []
        for g in games:
            rows.append(
                {
                    "date": g.date.strftime("%Y-%m-%d"),
                    "id": g.id,
                    "game_id": g.game_id,
                    "home_team_id": g.home_team.name if g.home_team else g.home_team_id,
                    "away_team_id": g.away_team.name if g.away_team else g.away_team_id,
                    "home_score": g.home_score,
                    "away_score": g.away_score,
                    "game_outcome": g.game_outcome,
                    "home_start_net": g.home_start_net,
                }
            )
        return rows
