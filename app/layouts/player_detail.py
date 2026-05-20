import dash_bootstrap_components as dbc
from dash import dcc, html


def create_player_detail_layout():
    return dbc.Container(
        [
            dcc.Store(id="player-detail-id"),
            dcc.Store(id="player-detail-situation", data="tot"),
            html.Div(id="player-detail-breadcrumb", className="mb-2"),
            html.Div(id="player-detail-header", className="mb-3 mt-1"),
            html.Div(id="player-detail-situation-toggle", className="mb-3"),
            dcc.Loading(
                html.Div(id="player-detail-stats"),
                type="circle",
                color="#4fc3f7",
            ),
            dcc.Loading(
                html.Div(id="player-detail-game-log", className="mt-4"),
                type="circle",
                color="#4fc3f7",
            ),
        ],
        fluid=True,
    )
