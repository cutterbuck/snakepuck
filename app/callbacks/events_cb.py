import random

from dash import Input, Output
from sqlalchemy.sql.expression import func

from app.extensions import db
from app.models import Event


def register_events_callbacks(dash_app):
    @dash_app.callback(
        Output("events-table", "data"),
        Input("url", "pathname"),
    )
    def update_events(pathname):
        # Fast random sampling via random ID selection
        id_range = db.session.query(func.min(Event.id), func.max(Event.id)).one()
        min_id, max_id = id_range
        if min_id is None or max_id is None:
            return []
        random_ids = random.sample(
            range(min_id, max_id + 1), min(100, max_id - min_id + 1)
        )
        events = Event.query.filter(Event.id.in_(random_ids)).all()
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
                    "team_abbr": e.team_abbr,
                    "opp_team_abbr": e.opp_team_abbr,
                    "description": e.description,
                    "detail": e.detail,
                    "xg": round(e.xg, 3) if e.xg is not None else None,
                    "x": round(e.x, 2) if e.x is not None else None,
                    "y": round(e.y, 2) if e.y is not None else None,
                }
            )
        return rows
