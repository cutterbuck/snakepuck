import random

from dash import Input, Output, State, callback_context, dash_table, html, no_update
from sqlalchemy.sql.expression import func

from app.extensions import db
from app.models import Event, Game, Player, PlayerStats, Stint, Team

VIEWS = ["games", "players", "events", "stints"]

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
                "date": g.date.strftime("%Y-%m-%d"),
                "id": g.id,
                "game_id": g.game_id,
                "home_team_id": g.home_team.abbrev if g.home_team else g.home_team_id,
                "away_team_id": g.away_team.abbrev if g.away_team else g.away_team_id,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "game_outcome": g.game_outcome,
                "home_start_net": g.home_start_net,
            }
        )
    return dash_table.DataTable(
        id="sample-games-table",
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
        data=rows,
        page_size=20,
        style_table=TABLE_STYLE,
        style_cell=CELL_STYLE,
        style_cell_conditional=[{"if": {"column_id": "game_id"}, "maxWidth": "80px"}],
        style_header=HEADER_STYLE,
        style_data_conditional=ROW_STRIPE,
    )


def _build_players_table():
    ids = _random_ids(PlayerStats)
    if not ids:
        return html.Div()
    results = (
        PlayerStats.query.filter(PlayerStats.id.in_(ids))
        .join(Player, PlayerStats.player_id == Player.playerId)
        .outerjoin(Team, Player.team_id == Team.id)
        .add_columns(
            Player.firstName,
            Player.lastName,
            Player.position,
            Team.name.label("team_name"),
        )
        .order_by(PlayerStats.points.desc(), PlayerStats.goals.desc())
        .all()
    )
    rows = []
    for ps, first_name, last_name, pos, team_name in results:
        rows.append(
            {
                "name": f"{first_name} {last_name}",
                "team": team_name,
                "age": ps.age,
                "position": pos,
                "gp": ps.games_played,
                "goals": ps.goals,
                "assists": ps.assists,
                "points": ps.points,
                "shots": ps.shots,
                "shooting_pct": _fmt_pct(ps.shooting_pct),
                "fow": ps.faceoffs_won,
                "fol": ps.faceoffs_lost,
                "fo_pct": _fmt_pct(ps.faceoff_pct),
                "penalties": ps.penalties,
                "penalties_drawn": ps.penalties_drawn,
                "blocks": ps.blocks,
                "checks": ps.checks,
                "xg": ps.xg,
            }
        )
    return dash_table.DataTable(
        id="sample-players-table",
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
        data=rows,
        page_size=20,
        style_table=TABLE_STYLE,
        style_cell=CELL_STYLE,
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
                "period_time": f"{float(e.period_time):.2f}"
                if e.period_time is not None
                else None,
                "event_type": e.event_type,
                "outcome": e.outcome,
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


def register_sample_data_callbacks(dash_app):
    # Toggle view and button styles
    @dash_app.callback(
        Output("sample-data-view", "data"),
        Output("sample-view-games", "outline"),
        Output("sample-view-players", "outline"),
        Output("sample-view-events", "outline"),
        Output("sample-view-stints", "outline"),
        Input("sample-view-games", "n_clicks"),
        Input("sample-view-players", "n_clicks"),
        Input("sample-view-events", "n_clicks"),
        Input("sample-view-stints", "n_clicks"),
        State("sample-data-view", "data"),
    )
    def toggle_view(
        games_clicks, players_clicks, events_clicks, stints_clicks, current_view
    ):
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]["prop_id"] == ".":
            return (
                current_view,
                current_view != "games",
                current_view != "players",
                current_view != "events",
                current_view != "stints",
            )
        triggered = ctx.triggered[0]["prop_id"]
        if "games" in triggered:
            view = "games"
        elif "players" in triggered:
            view = "players"
        elif "events" in triggered:
            view = "events"
        else:
            view = "stints"
        return (
            view,
            view != "games",
            view != "players",
            view != "events",
            view != "stints",
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
        return html.Div()
