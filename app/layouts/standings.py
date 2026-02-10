import dash_bootstrap_components as dbc
from dash import dcc, html


def create_standings_layout():
    return dbc.Container(
        [
            html.H2("Team Standings", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("League", className="fw-bold mb-1"),
                            dcc.Dropdown(
                                id="standings-league", clearable=False, searchable=False
                            ),
                        ],
                        width="auto",
                        style={"width": "270px"},
                    ),
                    dbc.Col(
                        [
                            html.Label("Season", className="fw-bold mb-1"),
                            dcc.Dropdown(
                                id="standings-season", clearable=False, searchable=False
                            ),
                        ],
                        width="auto",
                        style={"minWidth": "130px"},
                    ),
                    dbc.Col(
                        [
                            html.Label("View", className="fw-bold mb-1"),
                            html.Div(
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            "Division",
                                            id="standings-view-division",
                                            color="primary",
                                            outline=False,
                                            n_clicks=0,
                                        ),
                                        dbc.Button(
                                            "League",
                                            id="standings-view-league",
                                            color="primary",
                                            outline=True,
                                            n_clicks=0,
                                        ),
                                    ],
                                    style={"height": "34px"},
                                ),
                            ),
                        ],
                        width="auto",
                    ),
                ],
                className="mb-3",
            ),
            dcc.Store(id="standings-view", data="division"),
            dcc.Store(id="standings-sort", data={"column": "PTS", "direction": "desc"}),
            html.Div(id="standings-table"),
        ],
        fluid=True,
    )
