import dash_bootstrap_components as dbc
from dash import dcc, html


def create_team_detail_layout():
    return dbc.Container(
        [
            dcc.Store(id="team-detail-id"),
            dcc.Store(id="team-detail-situation", data="tot"),
            html.Div(id="team-detail-breadcrumb", className="mb-2"),
            html.Div(id="team-detail-header", className="mb-3 mt-1"),
            html.Div(
                [
                    html.Label(
                        "Season",
                        style={"fontWeight": "bold", "marginRight": "8px"},
                    ),
                    dcc.Dropdown(
                        id="season-selector",
                        clearable=False,
                        style={"width": "200px"},
                    ),
                ],
                id="team-detail-season-dropdown",
                className="mb-3",
                style={"display": "flex", "alignItems": "center"},
            ),
            html.Div(id="team-detail-situation-toggle", className="mb-3"),
            dcc.Store(
                id="team-detail-sort", data={"column": "PTS", "direction": "desc"}
            ),
            dcc.Loading(
                html.Div(id="team-detail-table"),
                type="circle",
                color="#4fc3f7",
            ),
        ],
        fluid=True,
    )
