import dash_bootstrap_components as dbc
from dash import dash_table, html


def create_games_layout():
    return dbc.Container(
        [
            html.H2("Game Results (Random Sample of 100)", className="mb-3"),
            dash_table.DataTable(
                id="games-table",
                columns=[
                    {"name": "Date", "id": "date"},
                    {"name": "ID", "id": "id"},
                    {"name": "Game ID", "id": "game_id"},
                    {"name": "Home Team", "id": "home_team_id"},
                    {"name": "Away Team", "id": "away_team_id"},
                    {"name": "Home Score", "id": "home_score"},
                    {"name": "Away Score", "id": "away_score"},
                    {"name": "Outcome", "id": "game_outcome"},
                    {"name": "Home Start Net", "id": "home_start_net"},
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


"game_id"
(
    "period",
    "period_time",
    "game_stint",
    "sl_event_id",
    "sequence_id",
    "player_id",
    "player_name",
    "team",
    "team_id",
    "opp_team",
    "opp_team_id",
    "event_type",
    "outcome",
    "flags",
    "description",
    "detail",
    "sl_xg_all_shots",
    "x",
    "y",
    "x_adj",
    "y_adj",
    "has_tracking_data",
    "event_player_tracked",
)
