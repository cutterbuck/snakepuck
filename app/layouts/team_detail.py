import dash_bootstrap_components as dbc
from dash import dcc, html


def create_team_detail_layout():
    return dbc.Container(
        [
            dcc.Store(id="team-detail-id"),
            dcc.Link(
                "Back to Standings",
                href="/",
                className="btn btn-secondary btn-sm",
            ),
            html.Div(id="team-detail-header", className="mb-3 mt-3"),
            dcc.Store(
                id="team-detail-sort", data={"column": "PTS", "direction": "desc"}
            ),
            html.Div(id="team-detail-table"),
        ],
        fluid=True,
    )
