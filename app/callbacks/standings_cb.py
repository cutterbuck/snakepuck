from dash import Input, Output

from app.models import Team, TeamStats


def register_standings_callbacks(dash_app):
    @dash_app.callback(
        Output("standings-table", "data"),
        Input("url", "pathname"),
    )
    def update_standings(pathname):
        if pathname != "/":
            from dash import no_update

            return no_update

        results = (
            TeamStats.query.join(Team, TeamStats.team_id == Team.id)
            .add_columns(Team.name)
            .order_by(TeamStats.points.desc())
            .all()
        )

        rows = []
        for ts, team_name in results:
            rows.append(
                {
                    "team": team_name,
                    "gp": ts.games_played,
                    "w": ts.wins,
                    "l": ts.losses,
                    "otl": ts.ot_losses,
                    "pts": ts.points,
                    "pts_pct": ts.points_percentage,
                    "rw": ts.regulation_wins,
                    "row": ts.regulation_or_ot_wins,
                    "gf": ts.goals_forward,
                    "ga": ts.goals_against,
                    "diff": ts.goal_diff,
                    "so": ts.so_record,
                }
            )

        return rows
