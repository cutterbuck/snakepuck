import dash_bootstrap_components as dbc
from dash import dash_table, html


def create_events_layout():
    return dbc.Container(
        [
            html.H2("Events Data (Random Sample of 100)", className="mb-3"),
            dash_table.DataTable(
                id="events-table",
                columns=[
                    {"name": "Game ID", "id": "game_id"},
                    {"name": "Player ID", "id": "player_id"},
                    {"name": "Period", "id": "period"},
                    {"name": "Time", "id": "period_time"},
                    {"name": "Event Type", "id": "event_type"},
                    {"name": "Outcome", "id": "outcome"},
                    {"name": "Team", "id": "team_abbr"},
                    {"name": "Opp Team", "id": "opp_team_abbr"},
                    {"name": "Description", "id": "description"},
                    {"name": "Detail", "id": "detail"},
                    {"name": "xG", "id": "xg"},
                    {"name": "X", "id": "x"},
                    {"name": "Y", "id": "y"},
                ],
                page_size=20,
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "center",
                    "padding": "2px 6px",
                    "fontSize": "12px",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
                style_cell_conditional=[
                    {"if": {"column_id": "game_id"}, "maxWidth": "80px"},
                    {"if": {"column_id": "player_id"}, "maxWidth": "80px"},
                ],
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
