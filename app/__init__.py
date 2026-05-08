import os

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from flask import Flask

from app.config import Config
from app.extensions import db, migrate

# AUTH DISABLED — uncomment to re-enable login
# from flask import redirect, request
# from flask_login import current_user
# from app.extensions import login_manager


def create_app():
    # Flask server
    server = Flask(__name__)
    server.config.from_object(Config)

    # Initialize extensions
    db.init_app(server)
    # AUTH DISABLED — uncomment to re-enable login
    # login_manager.init_app(server)
    migrate.init_app(server, db)
    # login_manager.login_view = "auth.login"

    # # User loader
    # from app.models.user import User
    #
    # @login_manager.user_loader
    # def load_user(user_id):
    #     return db.session.get(User, int(user_id))
    #
    # # Register auth blueprint
    # from app.auth import auth_bp
    #
    # server.register_blueprint(auth_bp, url_prefix="/auth")
    #
    # # Protect Dash routes
    # @server.before_request
    # def require_login():
    #     allowed_paths = ["/auth/login", "/auth/logout"]
    #     if request.path.startswith("/assets") or request.path.startswith("/_dash"):
    #         return
    #     if request.path in allowed_paths:
    #         return
    #     if not current_user.is_authenticated:
    #         return redirect("/auth/login")

    # Create Dash app
    assets_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, "assets")
    )
    dash_app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname="/",
        assets_folder=assets_path,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        title="SnakePuck",
    )
    dash_app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""

    # Import layouts
    from app.layouts.blog_post_detail import create_blog_post_detail_layout
    from app.layouts.blog_posts import create_blog_posts_layout
    from app.layouts.game_report import create_game_report_layout
    from app.layouts.navbar import create_navbar
    from app.layouts.player_analysis import create_player_analysis_layout
    from app.layouts.player_detail import create_player_detail_layout
    from app.layouts.player_stats import create_player_stats_layout
    from app.layouts.sample_data import create_sample_data_layout
    from app.layouts.standings import create_standings_layout
    from app.layouts.team_detail import create_team_detail_layout

    # App layout
    dash_app.layout = html.Div(
        [
            dcc.Location(id="url", refresh=False),
            create_navbar(),
            html.Div(id="page-content"),
        ]
    )

    # Page routing callback
    @dash_app.callback(
        dash.Output("page-content", "children"),
        dash.Input("url", "pathname"),
    )
    def display_page(pathname):
        if pathname == "/player-stats":
            return create_player_stats_layout()
        elif pathname == "/player-analysis":
            return create_player_analysis_layout()
        elif pathname == "/sample-data":
            return create_sample_data_layout()
        elif pathname and pathname.startswith("/blog/"):
            return create_blog_post_detail_layout()
        elif pathname == "/blog-posts":
            return create_blog_posts_layout()
        elif pathname and pathname.startswith("/team/"):
            return create_team_detail_layout()
        elif pathname and pathname.startswith("/player/") and "/game/" in pathname:
            return create_game_report_layout()
        elif pathname and pathname.startswith("/player/"):
            return create_player_detail_layout()
        else:
            return create_standings_layout()

    # Register data callbacks
    from app.callbacks import register_all_callbacks

    register_all_callbacks(dash_app)

    return server
