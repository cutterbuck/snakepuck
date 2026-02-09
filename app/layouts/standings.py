import dash_bootstrap_components as dbc
from dash import dcc, html


def create_standings_layout():
    return dbc.Container(
        [
            html.H2("Team Standings", className="mb-3"),
            dcc.Store(id="standings-sort", data={"column": "PTS", "direction": "desc"}),
            html.Div(id="standings-table"),
        ],
        fluid=True,
    )
