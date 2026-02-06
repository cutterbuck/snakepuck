import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html


def create_games_layout():
    return dbc.Container(
        [
            html.H2("Game Results", className="mb-3"),
            dbc.Row(
                dbc.Col(
                    dcc.Dropdown(
                        id="games-team-filter",
                        placeholder="Filter by team...",
                        clearable=True,
                    ),
                    width=4,
                ),
                className="mb-3",
            ),
            dash_table.DataTable(
                id="games-table",
                columns=[
                    {"name": "Date", "id": "date"},
                    {"name": "Home", "id": "home"},
                    {"name": "Away", "id": "away"},
                    {"name": "Score", "id": "score"},
                    {"name": "Result", "id": "result"},
                ],
                sort_action="native",
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "center", "padding": "8px"},
                style_header={
                    "backgroundColor": "#343a40",
                    "color": "white",
                    "fontWeight": "bold",
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "#f8f9fa",
                    }
                ],
            ),
        ],
        fluid=True,
    )
