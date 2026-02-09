from dash import Input, Output, html

from app.models import Team, TeamStats

HEADER_STYLE = {
    "backgroundColor": "#343a40",
    "color": "white",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "8px",
}

CELL_STYLE = {
    "textAlign": "center",
    "padding": "8px",
}


def register_standings_callbacks(dash_app):
    @dash_app.callback(
        Output("standings-table", "children"),
        Input("url", "pathname"),
    )
    def update_standings(pathname):
        if pathname != "/":
            from dash import no_update

            return no_update

        headers = [
            "Team",
            "GP",
            "W",
            "L",
            "OTL",
            "PTS",
            "P%",
            "RW",
            "ROW",
            "GF",
            "GA",
            "DIFF",
            "SO",
        ]
        thead = html.Thead(html.Tr([html.Th(h, style=HEADER_STYLE) for h in headers]))

        results = (
            TeamStats.query.join(Team, TeamStats.team_id == Team.id)
            .add_columns(Team.name, Team.logo)
            .order_by(TeamStats.points.desc())
            .all()
        )

        rows = []
        for i, (ts, team_name, team_logo) in enumerate(results):
            row_style = (
                {"backgroundColor": "rgb(245, 245, 245)"}
                if i % 2 == 1
                else {"backgroundColor": "rgb(255, 255, 255)"}
            )

            team_children = []
            if team_logo:
                team_children.append(
                    html.Img(
                        src=team_logo,
                        style={
                            "width": "36px",
                            "height": "24px",
                            "verticalAlign": "middle",
                            "paddingRight": "8px",
                        },
                    )
                )
            team_children.append(html.Div(team_name, style={"display": "inline-block"}))

            team_cell = html.Td(
                html.Div(children=team_children),
                style={
                    "paddingTop": "5px",
                    "paddingBottom": "5px",
                    "width": "320px",
                    "whiteSpace": "nowrap",
                },
            )

            stat_cells = [
                html.Td(v, style=CELL_STYLE)
                for v in [
                    ts.games_played,
                    ts.wins,
                    ts.losses,
                    ts.ot_losses,
                    ts.points,
                    ts.points_percentage,
                    ts.regulation_wins,
                    ts.regulation_or_ot_wins,
                    ts.goals_forward,
                    ts.goals_against,
                    ts.goal_diff,
                    ts.so_record,
                ]
            ]

            rows.append(html.Tr([team_cell] + stat_cells, style=row_style))

        return html.Table(
            [thead, html.Tbody(rows)],
            style={"overflowX": "auto", "width": "100%", "borderCollapse": "collapse"},
        )
