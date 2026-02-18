from app.callbacks.blog_posts_cb import register_blog_posts_callbacks
from app.callbacks.game_report_cb import register_game_report_callbacks
from app.callbacks.player_detail_cb import register_player_detail_callbacks
from app.callbacks.sample_data_cb import register_sample_data_callbacks
from app.callbacks.standings_cb import register_standings_callbacks
from app.callbacks.team_detail_cb import register_team_detail_callbacks


def register_all_callbacks(dash_app):
    register_standings_callbacks(dash_app)
    register_sample_data_callbacks(dash_app)
    register_team_detail_callbacks(dash_app)
    register_player_detail_callbacks(dash_app)
    register_game_report_callbacks(dash_app)
    register_blog_posts_callbacks(dash_app)
