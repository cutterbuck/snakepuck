import dash_bootstrap_components as dbc
from dash import html


def create_standings_layout():
    return dbc.Container(
        [
            html.H2("Team Standings", className="mb-3"),
            html.Div(id="standings-table"),
        ],
        fluid=True,
    )
