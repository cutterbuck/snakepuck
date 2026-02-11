import random

from dash import Input, Output
from sqlalchemy.sql.expression import func

from app.extensions import db
from app.models import Stint


def _fmt_time(val):
    """Format time string to hundredths decimal place."""
    if val is None:
        return None
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return val


def register_stints_callbacks(dash_app):
    @dash_app.callback(
        Output("stints-table", "data"),
        Input("url", "pathname"),
    )
    def update_stints(pathname):
        # Fast random sampling via random ID selection
        id_range = db.session.query(func.min(Stint.id), func.max(Stint.id)).one()
        min_id, max_id = id_range
        if min_id is None or max_id is None:
            return []
        random_ids = random.sample(
            range(min_id, max_id + 1), min(100, max_id - min_id + 1)
        )
        stints = Stint.query.filter(Stint.id.in_(random_ids)).all()
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
        return rows
