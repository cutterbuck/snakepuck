import dash_bootstrap_components as dbc
from dash import dcc, html


def create_game_report_layout():
    return dbc.Container(
        [
            dcc.Store(id="game-report-player-id"),
            dcc.Store(id="game-report-game-id"),
            html.Div(id="game-report-breadcrumb", className="mb-2"),
            html.Div(id="game-report-header", className="mb-3 mt-1"),
            dcc.Store(id="game-report-situation", data="tot"),
            html.Div(id="game-report-situation-toggle", className="mb-2"),
            dcc.Loading(
                html.Div(id="game-report-stats"),
                type="circle",
                color="#4fc3f7",
            ),
            dcc.Store(id="game-report-stint-period", data=1),
            dcc.Store(id="game-report-selected-stint", data=None),
            dcc.Store(id="game-report-merged-stints", data={}),
            html.Div(id="game-report-stints-header", style={"marginTop": "3px"}),
            html.Div(id="game-report-stints"),
            dcc.Store(id="game-report-stint-events", data=None),
            dcc.Store(id="game-report-frame-index", data=0),
            dcc.Store(id="game-report-frame-delays", data=[]),
            html.Div(
                [
                    html.Button(
                        "Play",
                        id="game-report-play-btn",
                        n_clicks=0,
                        className="btn btn-info btn-sm",
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
            # Persistent graph: the rink is drawn once and only frame
            # markers update during playback (no Loading wrapper, so no flicker)
            dcc.Store(id="game-report-rink-base"),
            dcc.Graph(
                id="game-report-rink-graph",
                figure={
                    "layout": {
                        "xaxis": {"visible": False},
                        "yaxis": {"visible": False},
                        "height": 400,
                        "plot_bgcolor": "white",
                    }
                },
                config={"displayModeBar": False},
                style={"width": "100%"},
                className="mt-3",
            ),
            dcc.Interval(
                id="game-report-interval",
                interval=1500,
                disabled=True,
            ),
        ],
        fluid=True,
    )
