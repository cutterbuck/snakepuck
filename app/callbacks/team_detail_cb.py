from dash import Input, Output, State, callback_context, dcc, html, no_update

from app.models import Player, PlayerStats, Team

HEADER_STYLE = {
    "backgroundColor": "#343a40",
    "color": "white",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "4px 8px",
    "cursor": "pointer",
    "userSelect": "none",
    "whiteSpace": "nowrap",
}

HEADER_STYLE_NO_SORT = {
    "backgroundColor": "#343a40",
    "color": "white",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "4px 8px",
}

ACTIVE_HEADER_STYLE = {
    "backgroundColor": "#4a6fa5",
    "color": "white",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "4px 8px",
    "cursor": "pointer",
    "userSelect": "none",
    "whiteSpace": "nowrap",
}

CELL_STYLE = {
    "textAlign": "center",
    "padding": "4px 8px",
}

ACTIVE_CELL_STYLE = {
    "textAlign": "center",
    "padding": "4px 8px",
    "backgroundColor": "rgba(74, 111, 165, 0.1)",
}

HEADERS = [
    "Name",
    "Age",
    "Pos",
    "GP",
    "G",
    "A",
    "PTS",
    "S",
    "S%",
    "FOW",
    "FOL",
    "FO%",
    "PIM",
    "PD",
    "BLK",
    "HIT",
    "xG",
]

SORTABLE_COLUMNS = [
    "Age",
    "Pos",
    "GP",
    "G",
    "A",
    "PTS",
    "S",
    "S%",
    "FOW",
    "FOL",
    "FO%",
    "PIM",
    "PD",
    "BLK",
    "HIT",
    "xG",
]

COLUMN_TO_FIELD = {
    "Age": "age",
    "Pos": "position",
    "GP": "games_played",
    "G": "goals",
    "A": "assists",
    "PTS": "points",
    "S": "shots",
    "S%": "shooting_pct",
    "FOW": "faceoffs_won",
    "FOL": "faceoffs_lost",
    "FO%": "faceoff_pct",
    "PIM": "penalties",
    "PD": "penalties_drawn",
    "BLK": "blocks",
    "HIT": "checks",
    "xG": "xg",
}


def _fmt_pct(val):
    if val is None:
        return ""
    return f"{val:.3f}"


def _build_thead(sort_col, sort_dir):
    header_cells = []
    for h in HEADERS:
        if h in SORTABLE_COLUMNS:
            is_active = sort_col == h
            indicator = ""
            if is_active:
                indicator = " \u25bc" if sort_dir == "desc" else " \u25b2"
            header_cells.append(
                html.Th(
                    h + indicator,
                    id=f"td-sort-{h}",
                    n_clicks=0,
                    style=ACTIVE_HEADER_STYLE if is_active else HEADER_STYLE,
                )
            )
        else:
            header_cells.append(html.Th(h, style=HEADER_STYLE_NO_SORT))
    return html.Thead(html.Tr(header_cells))


def register_team_detail_callbacks(dash_app):
    @dash_app.callback(
        Output("team-detail-id", "data"),
        Input("url", "pathname"),
    )
    def store_team_id(pathname):
        if pathname and pathname.startswith("/team/"):
            try:
                return int(pathname.split("/team/")[1])
            except (ValueError, IndexError):
                return None
        return None

    @dash_app.callback(
        Output("team-detail-header", "children"),
        Input("team-detail-id", "data"),
    )
    def update_header(team_id):
        if not team_id:
            return html.Div()
        team = Team.query.get(team_id)
        if not team:
            return html.H2("Team not found")
        children = []
        if team.logo:
            children.append(
                html.Img(
                    src=team.logo,
                    style={
                        "width": "48px",
                        "height": "48px",
                        "verticalAlign": "middle",
                        "marginRight": "12px",
                    },
                )
            )
        children.append(
            html.Span(
                team.name,
                style={
                    "fontSize": "24px",
                    "fontWeight": "bold",
                    "verticalAlign": "middle",
                },
            )
        )
        return html.Div(children, style={"display": "flex", "alignItems": "center"})

    # Sort state callback
    @dash_app.callback(
        Output("team-detail-sort", "data"),
        [Input(f"td-sort-{h}", "n_clicks") for h in SORTABLE_COLUMNS],
        State("team-detail-sort", "data"),
    )
    def update_sort(*args):
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]["prop_id"] == ".":
            return no_update

        prop_id = ctx.triggered[0]["prop_id"]

        # Ignore freshly rendered headers (n_clicks=0)
        triggered_value = ctx.triggered[0]["value"]
        if triggered_value is None or triggered_value == 0:
            return no_update

        col_name = prop_id.replace("td-sort-", "").replace(".n_clicks", "")

        current = args[-1]
        if current["column"] == col_name:
            new_dir = "asc" if current["direction"] == "desc" else "desc"
        else:
            new_dir = "desc"

        return {"column": col_name, "direction": new_dir}

    @dash_app.callback(
        Output("team-detail-table", "children"),
        [Input("team-detail-id", "data"), Input("team-detail-sort", "data")],
    )
    def update_roster(team_id, sort_data):
        if not team_id:
            return html.Div()

        sort_col = sort_data.get("column", "PTS") if sort_data else "PTS"
        sort_dir = sort_data.get("direction", "desc") if sort_data else "desc"

        query = (
            PlayerStats.query.join(Player, PlayerStats.player_id == Player.playerId)
            .filter(PlayerStats.team_id == team_id)
            .add_columns(Player.id, Player.firstName, Player.lastName, Player.position)
        )

        # Apply sort — push NULL to the bottom
        field = COLUMN_TO_FIELD.get(sort_col, "points")
        if field == "position":
            order_col = getattr(Player, field)
        else:
            order_col = getattr(PlayerStats, field)

        if sort_dir == "desc":
            order_col = order_col.desc()
        query = query.order_by(order_col.nulls_last())

        results = query.all()

        thead = _build_thead(sort_col, sort_dir)

        rows = []
        for i, (ps, pid, first_name, last_name, pos) in enumerate(results):
            row_style = (
                {"backgroundColor": "rgb(245, 245, 245)"}
                if i % 2 == 1
                else {"backgroundColor": "rgb(255, 255, 255)"}
            )
            values = [
                ps.age,
                pos,
                ps.games_played,
                ps.goals,
                ps.assists,
                ps.points,
                ps.shots,
                _fmt_pct(ps.shooting_pct),
                ps.faceoffs_won,
                ps.faceoffs_lost,
                _fmt_pct(ps.faceoff_pct),
                ps.penalties,
                ps.penalties_drawn,
                ps.blocks,
                ps.checks,
                ps.xg,
            ]
            stat_cols = HEADERS[1:]  # all columns except Name
            cells = [
                html.Td(
                    dcc.Link(
                        f"{first_name} {last_name}",
                        href=f"/player/{pid}",
                        className="team-link",
                        style={"display": "block", "padding": "4px 8px"},
                    ),
                    style={**CELL_STYLE, "textAlign": "left", "padding": "0"},
                )
            ]
            for col, v in zip(stat_cols, values):
                cells.append(
                    html.Td(
                        v, style=ACTIVE_CELL_STYLE if col == sort_col else CELL_STYLE
                    )
                )
            rows.append(html.Tr(cells, style=row_style))

        return html.Table(
            [thead, html.Tbody(rows)],
            style={"overflowX": "auto", "width": "100%", "borderCollapse": "collapse"},
        )
