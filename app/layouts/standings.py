import dash_bootstrap_components as dbc
from dash import dash_table, html


def create_standings_layout():
    return dbc.Container(
        [
            html.H2("Team Standings", className="mb-3"),
            dash_table.DataTable(
                id="standings-table",
                columns=[
                    {"name": "Team", "id": "team"},
                    {"name": "GP", "id": "gp"},
                    {"name": "W", "id": "w"},
                    {"name": "L", "id": "l"},
                    {"name": "OTL", "id": "otl"},
                    {"name": "PTS", "id": "pts"},
                    {"name": "P%", "id": "pts_pct"},
                    {"name": "RW", "id": "rw"},
                    {"name": "ROW", "id": "row"},
                    {"name": "GF", "id": "gf"},
                    {"name": "GA", "id": "ga"},
                    {"name": "DIFF", "id": "diff"},
                    {"name": "SO", "id": "so"},
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
