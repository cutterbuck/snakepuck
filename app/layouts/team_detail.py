import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html


def create_team_detail_layout():
    return dbc.Container(
        [
            dcc.Store(id="team-detail-id"),
            dcc.Link(
                dbc.Button(
                    "Back to Standings",
                    color="secondary",
                    size="sm",
                ),
                href="/",
                style={"textDecoration": "none"},
            ),
            html.Div(id="team-detail-header", className="mb-3 mt-3"),
            dash_table.DataTable(
                id="team-detail-table",
                columns=[
                    {"name": "Name", "id": "name"},
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
                sort_action="native",
                page_size=50,
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
