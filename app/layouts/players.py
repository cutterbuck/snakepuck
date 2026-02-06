import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html


def create_players_layout():
    return dbc.Container(
        [
            html.H2("Player Statistics", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(
                            id="players-team-filter",
                            placeholder="Filter by team...",
                            clearable=True,
                        ),
                        width=4,
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id="players-position-filter",
                            placeholder="Filter by position...",
                            options=[
                                {"label": "Center", "value": "C"},
                                {"label": "Defense", "value": "D"},
                                {"label": "Left Wing", "value": "L"},
                                {"label": "Right Wing", "value": "R"},
                                {"label": "Goalie", "value": "G"},
                            ],
                            clearable=True,
                        ),
                        width=4,
                    ),
                ],
                className="mb-3",
            ),
            dash_table.DataTable(
                id="players-table",
                columns=[
                    {"name": "Name", "id": "name"},
                    {"name": "Team", "id": "team"},
                    {"name": "Position", "id": "position"},
                    {"name": "Nationality", "id": "nationality"},
                    {"name": "Birth Date", "id": "birthDate"},
                    {"name": "Height", "id": "height"},
                    {"name": "Weight", "id": "weight"},
                    {"name": "Shoots/Catches", "id": "shootsCatches"},
                ],
                sort_action="native",
                page_size=25,
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
