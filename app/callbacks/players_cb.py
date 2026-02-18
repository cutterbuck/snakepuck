import random

from dash import Input, Output
from sqlalchemy.sql.expression import func

from app.extensions import db
from app.models import Player, PlayerStats, Team


def _fmt_pct(val):
    if val is None:
        return ""
    return f"{val:.3f}"


def register_players_callbacks(dash_app):
    @dash_app.callback(
        Output("players-table", "data"),
        Input("url", "pathname"),
    )
    def update_players(pathname):
        # Fast random sampling via random ID selection
        id_range = db.session.query(
            func.min(PlayerStats.id), func.max(PlayerStats.id)
        ).one()
        min_id, max_id = id_range
        if min_id is None or max_id is None:
            return []
        random_ids = random.sample(
            range(min_id, max_id + 1), min(100, max_id - min_id + 1)
        )

        query = (
            PlayerStats.query.filter(PlayerStats.id.in_(random_ids))
            .join(Player, PlayerStats.player_id == Player.playerId)
            .outerjoin(Team, Player.team_id == Team.id)
            .add_columns(
                Player.firstName,
                Player.lastName,
                Player.position,
                Team.name.label("team_name"),
            )
            .order_by(PlayerStats.tot_points.desc(), PlayerStats.tot_goals.desc())
        )

        results = query.all()

        rows = []
        for ps, first_name, last_name, pos, team_name in results:
            rows.append(
                {
                    "name": f"{first_name} {last_name}",
                    "team": team_name,
                    "age": ps.age,
                    "position": pos,
                    "gp": ps.games_played,
                    "goals": ps.tot_goals,
                    "assists": ps.tot_assists,
                    "points": ps.tot_points,
                    "shots": ps.tot_shots,
                    "shooting_pct": _fmt_pct(ps.tot_shooting_pct),
                    "fow": ps.tot_faceoffs_won,
                    "fol": ps.tot_faceoffs_lost,
                    "fo_pct": _fmt_pct(ps.tot_faceoff_pct),
                    "penalties": ps.penalties,
                    "penalties_drawn": ps.penalties_drawn,
                    "blocks": ps.tot_blocks,
                    "checks": ps.tot_checks,
                    "tot_i_xg": ps.tot_i_xg,
                    "tot_oi_xgf": ps.tot_oi_xgf,
                    "tot_oi_xga": ps.tot_oi_xga,
                    "tot_xg_pct": _fmt_pct(ps.tot_xg_pct),
                    "es_i_xg": ps.es_i_xg,
                    "es_oi_xgf": ps.es_oi_xgf,
                    "es_oi_xga": ps.es_oi_xga,
                    "es_xg_pct": _fmt_pct(ps.es_xg_pct),
                    "ev5_i_xg": ps.ev5_i_xg,
                    "ev5_oi_xgf": ps.ev5_oi_xgf,
                    "ev5_oi_xga": ps.ev5_oi_xga,
                    "ev5_xg_pct": _fmt_pct(ps.ev5_xg_pct),
                }
            )
        return rows
