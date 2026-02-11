import dash_bootstrap_components as dbc
from dash import dash_table, html


def create_players_layout():
    return dbc.Container(
        [
            html.H2("Player Statistics (Random Sample of 100)", className="mb-3"),
            dash_table.DataTable(
                id="players-table",
                columns=[
                    {"name": "Name", "id": "name"},
                    {"name": "Team", "id": "team"},
                    {"name": "Age", "id": "age"},
                    {"name": "Pos", "id": "position"},
                    {"name": "GP", "id": "gp"},
                    {"name": "G", "id": "goals"},
                    {"name": "A", "id": "assists"},
                    {"name": "PTS", "id": "points"},
                    {"name": "S", "id": "shots"},
                    {"name": "S%", "id": "shooting_pct"},
                    {"name": "FOW", "id": "fow"},
                    {"name": "FOL", "id": "fol"},
                    {"name": "FO%", "id": "fo_pct"},
                    {"name": "PIM", "id": "penalties"},
                    {"name": "PD", "id": "penalties_drawn"},
                    {"name": "BLK", "id": "blocks"},
                    {"name": "HIT", "id": "checks"},
                    {"name": "xG", "id": "xg"},
                ],
                page_size=20,
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "center",
                    "padding": "2px 6px",
                    "fontSize": "12px",
                },
                style_header={
                    "backgroundColor": "#343a40",
                    "color": "white",
                    "fontWeight": "bold",
                    "fontSize": "12px",
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
