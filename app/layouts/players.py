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
                    {"name": "Tot ixG", "id": "tot_i_xg"},
                    {"name": "Tot oixGF", "id": "tot_oi_xgf"},
                    {"name": "Tot oixGA", "id": "tot_oi_xga"},
                    {"name": "Tot xG%", "id": "tot_xg_pct"},
                    {"name": "ES ixG", "id": "es_i_xg"},
                    {"name": "ES oixGF", "id": "es_oi_xgf"},
                    {"name": "ES oixGA", "id": "es_oi_xga"},
                    {"name": "ES xG%", "id": "es_xg_pct"},
                    {"name": "5v5 ixG", "id": "ev5_i_xg"},
                    {"name": "5v5 oixGF", "id": "ev5_oi_xgf"},
                    {"name": "5v5 oixGA", "id": "ev5_oi_xga"},
                    {"name": "5v5 xG%", "id": "ev5_xg_pct"},
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
