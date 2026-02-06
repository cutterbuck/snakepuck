from dash import Input, Output

from app.extensions import db
from app.models import Game, Team


def register_standings_callbacks(dash_app):
    @dash_app.callback(
        Output("standings-table", "data"),
        Input("url", "pathname"),
    )
    def update_standings(pathname):
        if pathname != "/":
            from dash import no_update

            return no_update

        teams = Team.query.all()
        games = Game.query.all()

        stats = {}
        for team in teams:
            stats[team.id] = {
                "team": team.name,
                "gp": 0,
                "w": 0,
                "l": 0,
                "otl": 0,
                "pts": 0,
                "gf": 0,
                "ga": 0,
            }

        for game in games:
            home_id = game.home_team_id
            away_id = game.away_team_id
            is_overtime = game.last_period and game.last_period > 3

            if home_id in stats:
                stats[home_id]["gp"] += 1
                stats[home_id]["gf"] += game.home_team_score
                stats[home_id]["ga"] += game.away_team_score

            if away_id in stats:
                stats[away_id]["gp"] += 1
                stats[away_id]["gf"] += game.away_team_score
                stats[away_id]["ga"] += game.home_team_score

            if game.home_team_score > game.away_team_score:
                # Home win
                if home_id in stats:
                    stats[home_id]["w"] += 1
                    stats[home_id]["pts"] += 2
                if away_id in stats:
                    if is_overtime:
                        stats[away_id]["otl"] += 1
                        stats[away_id]["pts"] += 1
                    else:
                        stats[away_id]["l"] += 1
            else:
                # Away win
                if away_id in stats:
                    stats[away_id]["w"] += 1
                    stats[away_id]["pts"] += 2
                if home_id in stats:
                    if is_overtime:
                        stats[home_id]["otl"] += 1
                        stats[home_id]["pts"] += 1
                    else:
                        stats[home_id]["l"] += 1

        rows = sorted(stats.values(), key=lambda r: r["pts"], reverse=True)
        return rows
