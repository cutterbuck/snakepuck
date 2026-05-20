import dash_bootstrap_components as dbc
from dash import dcc, html


def create_player_stats_layout():
    return dbc.Container(
        [
            html.H2("Player Stats", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("League", className="fw-bold mb-1"),
                            dcc.Dropdown(
                                id="ps-league", clearable=False, searchable=False
                            ),
                        ],
                        width="auto",
                        style={"width": "270px"},
                    ),
                    dbc.Col(
                        [
                            html.Label("Season", className="fw-bold mb-1"),
                            dcc.Dropdown(
                                id="ps-season", clearable=False, searchable=False
                            ),
                        ],
                        width="auto",
                        style={"minWidth": "130px"},
                    ),
                ],
                className="mb-3",
            ),
            html.Div(id="ps-situation-toggle", className="mb-3"),
            dcc.Store(id="ps-situation", data="tot"),
            dcc.Store(id="ps-sort", data={"column": "PTS", "direction": "desc"}),
            dcc.Store(id="ps-page", data=1),
            dcc.Loading(
                html.Div(id="ps-table"),
                type="circle",
                color="#4fc3f7",
            ),
            html.Div(id="ps-pagination", className="mt-3 mb-3"),
        ],
        fluid=True,
    )
