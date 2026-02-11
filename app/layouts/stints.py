import dash_bootstrap_components as dbc
from dash import dash_table, html


def create_stints_layout():
    return dbc.Container(
        [
            html.H2("Stints Data (Random Sample of 100)", className="mb-3"),
            dash_table.DataTable(
                id="stints-table",
                columns=[
                    {"name": "Game ID", "id": "game_id"},
                    {"name": "Player ID", "id": "player_id"},
                    {"name": "Period", "id": "period"},
                    {"name": "Time Start", "id": "period_time_start"},
                    {"name": "Time End", "id": "period_time_end"},
                    {"name": "Game Stint", "id": "game_stint"},
                    {"name": "Home Skaters", "id": "n_home_skaters"},
                    {"name": "Away Skaters", "id": "n_away_skaters"},
                    {"name": "Home Net Empty", "id": "is_home_net_empty"},
                    {"name": "Away Net Empty", "id": "is_away_net_empty"},
                    {"name": "Home Score", "id": "home_score"},
                    {"name": "Away Score", "id": "away_score"},
                    {"name": "Source Team ID", "id": "source_team_id"},
                    {"name": "Team", "id": "team_abbr"},
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
                    {"if": {"column_id": "source_team_id"}, "maxWidth": "80px"},
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
