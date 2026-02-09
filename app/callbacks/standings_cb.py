from dash import Input, Output, State, callback_context, html, no_update

from app.models import Team, TeamStats

HEADER_STYLE = {
    "backgroundColor": "#343a40",
    "color": "white",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "8px",
    "cursor": "pointer",
    "userSelect": "none",
    "whiteSpace": "nowrap",
}

HEADER_STYLE_NO_SORT = {
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

SORTABLE_COLUMNS = ["GP", "W", "L", "OTL", "PTS", "P%", "RW", "ROW", "GF", "GA", "DIFF"]

COLUMN_TO_FIELD = {
    "GP": "games_played",
    "W": "wins",
    "L": "losses",
    "OTL": "ot_losses",
    "PTS": "points",
    "P%": "points_percentage",
    "RW": "regulation_wins",
    "ROW": "regulation_or_ot_wins",
    "GF": "goals_forward",
    "GA": "goals_against",
    "DIFF": "goal_diff",
}

ALL_HEADERS = [
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


def register_standings_callbacks(dash_app):
    @dash_app.callback(
        Output("standings-sort", "data"),
        [Input(f"sort-{h}", "n_clicks") for h in SORTABLE_COLUMNS],
        State("standings-sort", "data"),
    )
    def update_sort(*args):
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]["prop_id"] == ".":
            return no_update

        prop_id = ctx.triggered[0]["prop_id"]
        col_name = prop_id.replace("sort-", "").replace(".n_clicks", "")

        current = args[-1]
        if current["column"] == col_name:
            new_dir = "asc" if current["direction"] == "desc" else "desc"
        else:
            new_dir = "desc"

        return {"column": col_name, "direction": new_dir}

    @dash_app.callback(
        Output("standings-table", "children"),
        [Input("url", "pathname"), Input("standings-sort", "data")],
    )
    def update_standings(pathname, sort_data):
        if pathname != "/":
            return no_update

        sort_col = sort_data.get("column", "PTS") if sort_data else "PTS"
        sort_dir = sort_data.get("direction", "desc") if sort_data else "desc"

        # Build header row with sort indicators
        header_cells = []
        for h in ALL_HEADERS:
            if h in SORTABLE_COLUMNS:
                indicator = ""
                if sort_col == h:
                    indicator = " \u25bc" if sort_dir == "desc" else " \u25b2"
                header_cells.append(
                    html.Th(
                        h + indicator,
                        id=f"sort-{h}",
                        n_clicks=0,
                        style=HEADER_STYLE,
                    )
                )
            else:
                header_cells.append(html.Th(h, style=HEADER_STYLE_NO_SORT))

        thead = html.Thead(html.Tr(header_cells))

        # Query and sort
        field = COLUMN_TO_FIELD.get(sort_col, "points")
        order_col = getattr(TeamStats, field)
        if sort_dir == "desc":
            order_col = order_col.desc()

        results = (
            TeamStats.query.join(Team, TeamStats.team_id == Team.id)
            .add_columns(Team.name, Team.logo)
            .order_by(order_col)
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
