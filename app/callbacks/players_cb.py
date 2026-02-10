from dash import Input, Output

from app.models import Player, PlayerStats, Team


def _fmt_pct(val):
    if val is None:
        return ""
    return f"{val:.3f}"


def register_players_callbacks(dash_app):
    @dash_app.callback(
        Output("players-team-filter", "options"),
        Input("url", "pathname"),
    )
    def populate_team_filter(pathname):
        teams = Team.query.order_by(Team.abbrev).all()
        return [{"label": t.name or t.abbrev, "value": t.id} for t in teams]

    @dash_app.callback(
        Output("players-table", "data"),
        [
            Input("url", "pathname"),
            Input("players-team-filter", "value"),
            Input("players-position-filter", "value"),
        ],
    )
    def update_players(pathname, team_id, position):
        query = (
            PlayerStats.query.join(Player, PlayerStats.player_id == Player.playerId)
            .outerjoin(Team, Player.team_id == Team.id)
            .add_columns(
                Player.firstName,
                Player.lastName,
                Player.position,
                Team.name.label("team_name"),
            )
        )

        if team_id:
            query = query.filter(Player.team_id == team_id)
        if position:
            query = query.filter(Player.position == position)

        query = query.order_by(PlayerStats.points.desc(), PlayerStats.goals.desc())
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
                    "xg": ps.xg,
                }
            )
        return rows
