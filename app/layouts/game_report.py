import dash_bootstrap_components as dbc
from dash import dcc, html


def create_game_report_layout():
    return dbc.Container(
        [
            dcc.Store(id="game-report-player-id"),
            dcc.Store(id="game-report-game-id"),
            dcc.Link(
                "Back to Player",
                id="game-report-back-link",
                href="/",
                className="btn btn-secondary btn-sm",
            ),
            html.Div(id="game-report-header", className="mb-3 mt-3"),
            html.Div(id="game-report-stats"),
            dcc.Store(id="game-report-stint-period", data=1),
            dcc.Store(id="game-report-selected-stint", data=None),
            html.Div(id="game-report-stints-header", style={"marginTop": "3px"}),
            html.Div(id="game-report-stints"),
            html.Div(id="game-report-rink", className="mt-3"),
        ],
        fluid=True,
    )
