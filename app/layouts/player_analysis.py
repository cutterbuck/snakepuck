import dash_bootstrap_components as dbc
from dash import html


def create_player_analysis_layout():
    return dbc.Container(
        [
            html.H2("Player Analysis", className="mb-4"),
            # Forwards section
            html.Div(
                [
                    html.H4("Forwards", className="mb-3"),
                    html.Div(
                        id="player-analysis-forwards",
                        children=html.P("Coming soon.", className="text-muted"),
                    ),
                ],
                className="mb-5",
            ),
            # Defensemen section
            html.Div(
                [
                    html.H4("Defensemen", className="mb-3"),
                    html.H5("Total Loose Puck Recovery", className="mb-1"),
                    html.P(
                        "How often do defensemen come away with possession after contesting a loose puck? (min. 15 GP)",
                        className="text-muted mb-2",
                        style={"fontSize": "14px"},
                    ),
                    html.Div(id="player-analysis-dmen-lpr"),
                ],
            ),
        ],
        fluid=True,
    )
