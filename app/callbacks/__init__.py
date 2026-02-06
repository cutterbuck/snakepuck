from app.callbacks.games_cb import register_games_callbacks
from app.callbacks.players_cb import register_players_callbacks
from app.callbacks.standings_cb import register_standings_callbacks


def register_all_callbacks(dash_app):
    register_standings_callbacks(dash_app)
    register_games_callbacks(dash_app)
    register_players_callbacks(dash_app)
