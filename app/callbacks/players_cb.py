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
            .order_by(PlayerStats.points.desc(), PlayerStats.goals.desc())
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
                    "i_xg": ps.i_xg,
                    "oi_xgf": ps.oi_xgf,
                    "oi_xga": ps.oi_xga,
                    "xg_percentage": _fmt_pct(ps.xg_percentage),
                }
            )
        return rows
