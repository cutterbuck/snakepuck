import dash_bootstrap_components as dbc
from dash import html


def create_player_analysis_layout():
    return dbc.Container(
        [
            html.H2("Player Analysis", className="mb-4"),
            html.P("Coming soon."),
        ],
        fluid=True,
    )
