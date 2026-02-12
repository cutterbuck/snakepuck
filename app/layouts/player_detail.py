import dash_bootstrap_components as dbc
from dash import dcc, html


def create_player_detail_layout():
    return dbc.Container(
        [
            dcc.Store(id="player-detail-id"),
            html.Div(id="player-detail-header", className="mb-3 mt-3"),
            html.Div(id="player-detail-stats"),
            html.Div(id="player-detail-game-log", className="mt-4"),
        ],
        fluid=True,
    )
