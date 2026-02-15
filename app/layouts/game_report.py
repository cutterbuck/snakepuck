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
            dcc.Store(id="game-report-stint-events", data=None),
            dcc.Store(id="game-report-frame-index", data=0),
            html.Div(
                [
                    html.Button(
                        "Play",
                        id="game-report-play-btn",
                        n_clicks=0,
                        className="btn btn-primary btn-sm",
                        style={"marginRight": "12px", "minWidth": "70px"},
                    ),
                    html.Div(
                        dcc.Slider(
                            id="game-report-frame-slider",
                            min=0,
                            max=0,
                            step=1,
                            value=0,
                            marks=None,
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),
                        style={"flex": "1"},
                    ),
                ],
                id="game-report-playback-controls",
                style={
                    "display": "none",
                    "alignItems": "center",
                    "marginTop": "8px",
                },
            ),
            dcc.Interval(
                id="game-report-interval",
                interval=500,
                disabled=True,
            ),
        ],
        fluid=True,
    )
