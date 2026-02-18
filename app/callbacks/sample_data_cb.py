import random

from dash import Input, Output, State, callback_context, dash_table, html, no_update
from sqlalchemy.sql.expression import func

from app.extensions import db
from app.models import Event, Game, Player, PlayerStats, Stint, Team, Tracking

VIEWS = ["games", "players", "events", "stints", "tracking"]

TABLE_STYLE = {"overflowX": "auto"}
CELL_STYLE = {
    "textAlign": "center",
    "padding": "2px 6px",
    "fontSize": "12px",
    "overflow": "hidden",
    "textOverflow": "ellipsis",
}
HEADER_STYLE = {
    "backgroundColor": "#343a40",
    "color": "white",
    "fontWeight": "bold",
    "fontSize": "12px",
}
ROW_STRIPE = [{"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"}]


def _fmt_pct(val):
    if val is None:
        return ""
    return f"{val:.3f}"


def _fmt_time(val):
    if val is None:
        return None
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return val


def _random_ids(model_cls, n=100):
    id_range = db.session.query(func.min(model_cls.id), func.max(model_cls.id)).one()
    min_id, max_id = id_range
    if min_id is None or max_id is None:
        return []
    return random.sample(range(min_id, max_id + 1), min(n, max_id - min_id + 1))


def _build_games_table():
    ids = _random_ids(Game)
    if not ids:
        return html.Div()
    games = Game.query.filter(Game.id.in_(ids)).all()
    rows = []
    for g in games:
        rows.append(
            {
                "game_id": g.game_id,
                "game_date": g.date.strftime("%Y-%m-%d"),
                "league": g.league.abbrev if g.league else None,
                "season": "2023-24",
                "home_team": g.home_team.abbrev if g.home_team else g.home_team_id,
                "away_team": g.away_team.abbrev if g.away_team else g.away_team_id,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "game_outcome": g.game_outcome,
                "home_start_net": g.home_start_net,
            }
        )
    return dash_table.DataTable(
        id="sample-games-table",
        columns=[
            {"name": "Game ID", "id": "game_id"},
            {"name": "Game Date", "id": "game_date"},
            {"name": "League", "id": "league"},
            {"name": "Season", "id": "season"},
            {"name": "Home Team", "id": "home_team"},
            {"name": "Away Team", "id": "away_team"},
            {"name": "Home Score", "id": "home_score"},
            {"name": "Away Score", "id": "away_score"},
            {"name": "Game Outcome", "id": "game_outcome"},
            {"name": "Home Start Net", "id": "home_start_net"},
        ],
        data=rows,
        page_size=20,
        style_table=TABLE_STYLE,
        style_cell=CELL_STYLE,
        style_cell_conditional=[{"if": {"column_id": "game_id"}, "maxWidth": "80px"}],
        style_header=HEADER_STYLE,
        style_data_conditional=ROW_STRIPE,
    )


def _build_players_table():
    ids = _random_ids(Player)
    if not ids:
        return html.Div()
    players = Player.query.filter(Player.id.in_(ids)).all()
    rows = []
    for p in players:
        rows.append(
            {
                "player_id": p.playerId,
                "player_name": f"{p.firstName} {p.lastName}",
                "last_name": p.lastName,
                "first_name": p.firstName,
                "handed": p.handed,
                "birth_date": str(p.birthDate) if p.birthDate else None,
                "position_group": p.position_group,
                "primary_position": p.position,
            }
        )
    return dash_table.DataTable(
        id="sample-players-table",
        columns=[
            {"name": "Player ID", "id": "player_id"},
            {"name": "Player Name", "id": "player_name"},
            {"name": "Last Name", "id": "last_name"},
            {"name": "First Name", "id": "first_name"},
            {"name": "Handed", "id": "handed"},
            {"name": "Birth Date", "id": "birth_date"},
            {"name": "Position Group", "id": "position_group"},
            {"name": "Primary Position", "id": "primary_position"},
        ],
        data=rows,
        page_size=20,
        style_table=TABLE_STYLE,
        style_cell=CELL_STYLE,
        style_cell_conditional=[
            {"if": {"column_id": "player_id"}, "maxWidth": "80px"},
        ],
        style_header=HEADER_STYLE,
        style_data_conditional=ROW_STRIPE,
    )


def _build_events_table():
    ids = _random_ids(Event)
    if not ids:
        return html.Div()
    events = Event.query.filter(Event.id.in_(ids)).all()
    rows = []
    for e in events:
        rows.append(
            {
                "game_id": e.game_id,
                "player_id": e.player_id,
                "period": e.period,
                "period_time": f"{e.period_time:.2f}"
                if e.period_time is not None
                else None,
                "event_type": e.event_type,
                "outcome": e.outcome,
                "flags": e.flags,
                "team_abbr": e.team_abbr,
                "opp_team_abbr": e.opp_team_abbr,
                "description": e.description,
                "detail": e.detail,
                "xg": round(e.xg, 3) if e.xg is not None else None,
                "x": round(e.x, 2) if e.x is not None else None,
                "y": round(e.y, 2) if e.y is not None else None,
            }
        )
    return dash_table.DataTable(
        id="sample-events-table",
        columns=[
            {"name": "Game ID", "id": "game_id"},
            {"name": "Player ID", "id": "player_id"},
            {"name": "Period", "id": "period"},
            {"name": "Time", "id": "period_time"},
            {"name": "Event Type", "id": "event_type"},
            {"name": "Outcome", "id": "outcome"},
            {"name": "Flags", "id": "flags"},
            {"name": "Team", "id": "team_abbr"},
            {"name": "Opp Team", "id": "opp_team_abbr"},
            {"name": "Description", "id": "description"},
            {"name": "Detail", "id": "detail"},
            {"name": "xG", "id": "xg"},
            {"name": "X", "id": "x"},
            {"name": "Y", "id": "y"},
        ],
        data=rows,
        page_size=20,
        style_table=TABLE_STYLE,
        style_cell=CELL_STYLE,
        style_cell_conditional=[
            {"if": {"column_id": "game_id"}, "maxWidth": "80px"},
            {"if": {"column_id": "player_id"}, "maxWidth": "80px"},
        ],
        style_header=HEADER_STYLE,
        style_data_conditional=ROW_STRIPE,
    )


def _build_stints_table():
    ids = _random_ids(Stint)
    if not ids:
        return html.Div()
    stints = Stint.query.filter(Stint.id.in_(ids)).all()
    rows = []
    for s in stints:
        rows.append(
            {
                "game_id": s.game_id,
                "player_id": s.player_id,
                "period": s.period,
                "period_time_start": _fmt_time(s.period_time_start),
                "period_time_end": _fmt_time(s.period_time_end),
                "game_stint": s.game_stint,
                "n_home_skaters": s.n_home_skaters,
                "n_away_skaters": s.n_away_skaters,
                "is_home_net_empty": s.is_home_net_empty,
                "is_away_net_empty": s.is_away_net_empty,
                "home_score": s.home_score,
                "away_score": s.away_score,
                "source_team_id": s.source_team_id,
                "team_abbr": s.team_abbr,
            }
        )
    return dash_table.DataTable(
        id="sample-stints-table",
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
        data=rows,
        page_size=20,
        style_table=TABLE_STYLE,
        style_cell=CELL_STYLE,
        style_cell_conditional=[
            {"if": {"column_id": "game_id"}, "maxWidth": "80px"},
            {"if": {"column_id": "player_id"}, "maxWidth": "80px"},
            {"if": {"column_id": "source_team_id"}, "maxWidth": "80px"},
        ],
        style_header=HEADER_STYLE,
        style_data_conditional=ROW_STRIPE,
    )


def _build_tracking_table():
    ids = _random_ids(Tracking)
    if not ids:
        return html.Div()
    rows_data = Tracking.query.filter(Tracking.id.in_(ids)).all()
    rows = []
    for t in rows_data:
        rows.append(
            {
                "game_id": t.game_id,
                "sl_event_id": t.sl_event_id,
                "team_id": t.team_id,
                "team_name": t.team_name,
                "player_id": t.player_id,
                "player_name": t.player_name,
                "tracking_x": round(t.tracking_x, 2)
                if t.tracking_x is not None
                else None,
                "tracking_y": round(t.tracking_y, 2)
                if t.tracking_y is not None
                else None,
                "tracking_vel_x": round(t.tracking_vel_x, 2)
                if t.tracking_vel_x is not None
                else None,
                "tracking_vel_y": round(t.tracking_vel_y, 2)
                if t.tracking_vel_y is not None
                else None,
            }
        )
    return dash_table.DataTable(
        id="sample-tracking-table",
        columns=[
            {"name": "Game ID", "id": "game_id"},
            {"name": "SL Event ID", "id": "sl_event_id"},
            {"name": "Team ID", "id": "team_id"},
            {"name": "Team Name", "id": "team_name"},
            {"name": "Player ID", "id": "player_id"},
            {"name": "Player Name", "id": "player_name"},
            {"name": "Tracking X", "id": "tracking_x"},
            {"name": "Tracking Y", "id": "tracking_y"},
            {"name": "Vel X", "id": "tracking_vel_x"},
            {"name": "Vel Y", "id": "tracking_vel_y"},
        ],
        data=rows,
        page_size=20,
        style_table=TABLE_STYLE,
        style_cell=CELL_STYLE,
        style_cell_conditional=[
            {"if": {"column_id": "game_id"}, "maxWidth": "80px"},
            {"if": {"column_id": "sl_event_id"}, "maxWidth": "80px"},
            {"if": {"column_id": "team_id"}, "maxWidth": "80px"},
            {"if": {"column_id": "player_id"}, "maxWidth": "80px"},
        ],
        style_header=HEADER_STYLE,
        style_data_conditional=ROW_STRIPE,
    )


def register_sample_data_callbacks(dash_app):
    # Toggle view and button styles
    @dash_app.callback(
        Output("sample-data-view", "data"),
        Output("sample-view-games", "outline"),
        Output("sample-view-players", "outline"),
        Output("sample-view-events", "outline"),
        Output("sample-view-stints", "outline"),
        Output("sample-view-tracking", "outline"),
        Input("sample-view-games", "n_clicks"),
        Input("sample-view-players", "n_clicks"),
        Input("sample-view-events", "n_clicks"),
        Input("sample-view-stints", "n_clicks"),
        Input("sample-view-tracking", "n_clicks"),
        State("sample-data-view", "data"),
    )
    def toggle_view(
        games_clicks,
        players_clicks,
        events_clicks,
        stints_clicks,
        tracking_clicks,
        current_view,
    ):
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]["prop_id"] == ".":
            return (
                current_view,
                current_view != "games",
                current_view != "players",
                current_view != "events",
                current_view != "stints",
                current_view != "tracking",
            )
        triggered = ctx.triggered[0]["prop_id"]
        if "games" in triggered:
            view = "games"
        elif "players" in triggered:
            view = "players"
        elif "events" in triggered:
            view = "events"
        elif "stints" in triggered:
            view = "stints"
        else:
            view = "tracking"
        return (
            view,
            view != "games",
            view != "players",
            view != "events",
            view != "stints",
            view != "tracking",
        )

    # Render content based on active view
    @dash_app.callback(
        Output("sample-data-content", "children"),
        Input("sample-data-view", "data"),
    )
    def update_content(view):
        if view == "games":
            return _build_games_table()
        elif view == "players":
            return _build_players_table()
        elif view == "events":
            return _build_events_table()
        elif view == "stints":
            return _build_stints_table()
        elif view == "tracking":
            return _build_tracking_table()
        return html.Div()
