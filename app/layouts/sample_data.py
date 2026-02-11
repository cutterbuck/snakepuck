import dash_bootstrap_components as dbc
from dash import dcc, html


def create_sample_data_layout():
    return dbc.Container(
        [
            html.H2("Sample Data (Random 100 Rows)", className="mb-3"),
            dbc.ButtonGroup(
                [
                    dbc.Button(
                        "Players",
                        id="sample-view-players",
                        color="primary",
                        outline=False,
                        n_clicks=0,
                    ),
                    dbc.Button(
                        "Games",
                        id="sample-view-games",
                        color="primary",
                        outline=True,
                        n_clicks=0,
                    ),
                    dbc.Button(
                        "Stints",
                        id="sample-view-stints",
                        color="primary",
                        outline=True,
                        n_clicks=0,
                    ),
                    dbc.Button(
                        "Events",
                        id="sample-view-events",
                        color="primary",
                        outline=True,
                        n_clicks=0,
                    ),
                    dbc.Button(
                        "Tracking",
                        id="sample-view-tracking",
                        color="primary",
                        outline=True,
                        n_clicks=0,
                    ),
                ],
                className="mb-3",
                style={"height": "34px"},
            ),
            dcc.Store(id="sample-data-view", data="players"),
            html.Div(id="sample-data-content"),
        ],
        fluid=True,
    )
