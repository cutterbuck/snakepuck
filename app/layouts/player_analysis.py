import dash_bootstrap_components as dbc
from dash import dcc, html


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
                    dcc.Dropdown(
                        id="pa-dmen-lpr-dropdown",
                        options=[
                            {
                                "label": "Total Low Pressure Loose Puck Recovery",
                                "value": "low",
                            },
                            {
                                "label": "Total High Pressure Loose Puck Recovery",
                                "value": "high",
                            },
                            {
                                "label": "HiPressLPR Next Play Success",
                                "value": "high_next_success",
                            },
                            {
                                "label": "HiPressLPR Next Play Failure",
                                "value": "high_next_failure",
                            },
                            {
                                "label": "HiPress LPR Next Play Success Rate",
                                "value": "high_next_rate",
                            },
                        ],
                        value="high",
                        clearable=False,
                        searchable=False,
                        className="mb-2",
                        style={"maxWidth": "450px"},
                    ),
                    html.P(
                        id="pa-dmen-lpr-subtitle",
                        className="text-muted mb-2",
                        style={"fontSize": "14px"},
                    ),
                    dcc.Store(
                        id="pa-lpr-sort",
                        data={"column": "xG%", "direction": "desc"},
                    ),
                    dcc.Loading(
                        html.Div(id="player-analysis-dmen-lpr"),
                        type="default",
                        style={"minHeight": "100px"},
                    ),
                ],
            ),
        ],
        fluid=True,
    )
