import random

from dash import Input, Output
from sqlalchemy.sql.expression import func

from app.extensions import db
from app.models import Game


def register_games_callbacks(dash_app):
    @dash_app.callback(
        Output("games-table", "data"),
        Input("url", "pathname"),
    )
    def update_games(pathname):
        id_range = db.session.query(func.min(Game.id), func.max(Game.id)).one()
        min_id, max_id = id_range
        if min_id is None or max_id is None:
            return []
        random_ids = random.sample(
            range(min_id, max_id + 1), min(100, max_id - min_id + 1)
        )
        games = Game.query.filter(Game.id.in_(random_ids)).all()
        rows = []
        for g in games:
            rows.append(
                {
                    "date": g.date.strftime("%Y-%m-%d"),
                    "id": g.id,
                    "game_id": g.game_id,
                    "home_team_id": g.home_team.abbrev
                    if g.home_team
                    else g.home_team_id,
                    "away_team_id": g.away_team.abbrev
                    if g.away_team
                    else g.away_team_id,
                    "home_score": g.home_score,
                    "away_score": g.away_score,
                    "game_outcome": g.game_outcome,
                    "home_start_net": g.home_start_net,
                }
            )
        return rows
