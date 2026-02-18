import dash_bootstrap_components as dbc
from dash import dcc, html


def create_team_detail_layout():
    return dbc.Container(
        [
            dcc.Store(id="team-detail-id"),
            dcc.Store(id="team-detail-situation", data="tot"),
            dcc.Link(
                "Back to Standings",
                href="/",
                className="btn btn-secondary btn-sm",
            ),
            html.Div(id="team-detail-header", className="mb-3 mt-3"),
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
            html.Div(id="team-detail-table"),
        ],
        fluid=True,
    )
