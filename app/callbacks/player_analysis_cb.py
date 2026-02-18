from dash import Input, Output, html
from sqlalchemy import case, func

from app.extensions import db
from app.models import Event, Player, PlayerStats
from app.models.stint import Stint

MIN_GP = 15

HEADER_STYLE = {
    "backgroundColor": "#343a40",
    "color": "white",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "4px 8px",
    "whiteSpace": "nowrap",
}

CELL_STYLE = {
    "textAlign": "center",
    "padding": "4px 8px",
}

NAME_CELL_STYLE = {
    "textAlign": "left",
    "padding": "4px 8px",
    "whiteSpace": "nowrap",
}

STRIPE_BG = "#f8f9fa"


def register_player_analysis_callbacks(dash_app):
    @dash_app.callback(
        Output("player-analysis-dmen-lpr", "children"),
        Input("url", "pathname"),
    )
    def update_dmen_lpr(pathname):
        if pathname != "/player-analysis":
            from dash import no_update

            return no_update

        # Subquery: defensemen with >= MIN_GP games played (sum across teams/seasons)
        gp_sub = (
            db.session.query(
                PlayerStats.player_id,
                func.sum(PlayerStats.games_played).label("total_gp"),
            )
            .join(Player, PlayerStats.player_id == Player.playerId)
            .filter(Player.position == "D")
            .group_by(PlayerStats.player_id)
            .having(func.sum(PlayerStats.games_played) >= MIN_GP)
            .subquery()
        )

        # Subquery: distinct 5v5 game stints
        ev5_stints = (
            db.session.query(
                Stint.game_id,
                Stint.game_stint,
            )
            .filter(
                Stint.n_home_skaters == 5,
                Stint.n_away_skaters == 5,
            )
            .distinct()
            .subquery()
        )

        # Count LPR events per player during 5v5, split by outcome
        results = (
            db.session.query(
                Player.firstName,
                Player.lastName,
                gp_sub.c.total_gp,
                func.count(Event.id).label("total_lpr"),
                func.sum(
                    case((Event.description == "HI PRESS DUMP IN LPR+", 1), else_=0)
                ).label("won"),
                func.sum(
                    case((Event.description == "HI PRESS DUMP IN LPR-", 1), else_=0)
                ).label("lost"),
            )
            .join(Player, Event.player_id == Player.playerId)
            .join(gp_sub, Player.playerId == gp_sub.c.player_id)
            .join(
                ev5_stints,
                db.and_(
                    Event.game_id == ev5_stints.c.game_id,
                    Event.game_stint == ev5_stints.c.game_stint,
                ),
            )
            .filter(
                Event.event_type == "lpr",
                Event.description.in_(
                    ["HI PRESS DUMP IN LPR+", "HI PRESS DUMP IN LPR-"]
                ),
            )
            .group_by(
                Player.playerId, Player.firstName, Player.lastName, gp_sub.c.total_gp
            )
            .order_by(
                (
                    func.sum(
                        case((Event.description == "HI PRESS DUMP IN LPR+", 1), else_=0)
                    )
                    * 100.0
                    / func.count(Event.id)
                ).desc()
            )
            .all()
        )

        if not results:
            return html.P("No data available.", className="text-muted")

        headers = ["Player", "GP", "LPR", "Won", "Lost", "Recovery %"]
        thead = html.Thead(html.Tr([html.Th(h, style=HEADER_STYLE) for h in headers]))

        rows = []
        for i, (first, last, gp, total, won, lost, *_) in enumerate(results):
            pct = (won / total * 100) if total else 0
            bg = {"backgroundColor": STRIPE_BG} if i % 2 == 1 else {}
            rows.append(
                html.Tr(
                    [
                        html.Td(f"{first} {last}", style={**NAME_CELL_STYLE, **bg}),
                        html.Td(gp, style={**CELL_STYLE, **bg}),
                        html.Td(total, style={**CELL_STYLE, **bg}),
                        html.Td(won, style={**CELL_STYLE, **bg}),
                        html.Td(lost, style={**CELL_STYLE, **bg}),
                        html.Td(f"{pct:.1f}%", style={**CELL_STYLE, **bg}),
                    ]
                )
            )

        return html.Table(
            [thead, html.Tbody(rows)],
            style={"width": "100%", "borderCollapse": "collapse"},
        )
