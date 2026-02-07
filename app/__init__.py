import os

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from flask import Flask, redirect, request
from flask_login import current_user

from app.config import Config
from app.extensions import db, login_manager, migrate


def create_app():
    # Flask server
    server = Flask(__name__)
    server.config.from_object(Config)

    # Initialize extensions
    db.init_app(server)
    login_manager.init_app(server)
    migrate.init_app(server, db)
    login_manager.login_view = "auth.login"

    # User loader
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register auth blueprint
    from app.auth import auth_bp

    server.register_blueprint(auth_bp, url_prefix="/auth")

    # Protect Dash routes
    @server.before_request
    def require_login():
        allowed_paths = ["/auth/login", "/auth/logout"]
        if request.path.startswith("/assets") or request.path.startswith("/_dash"):
            return
        if request.path in allowed_paths:
            return
        if not current_user.is_authenticated:
            return redirect("/auth/login")

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
    from app.layouts.games import create_games_layout
    from app.layouts.navbar import create_navbar
    from app.layouts.players import create_players_layout
    from app.layouts.standings import create_standings_layout

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
        if pathname == "/games":
            return create_games_layout()
        elif pathname == "/players":
            return create_players_layout()
        else:
            return create_standings_layout()

    # Register data callbacks
    from app.callbacks import register_all_callbacks

    register_all_callbacks(dash_app)

    return server
