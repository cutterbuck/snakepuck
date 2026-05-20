from dash import ALL, Input, Output, State, callback_context, ctx, dcc, html, no_update

from app.models import Player, PlayerStats, Season, Team

HEADER_STYLE = {
    "backgroundColor": "#163d5c",
    "color": "#d0e8f7",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "6px 10px",
    "cursor": "pointer",
    "userSelect": "none",
    "whiteSpace": "nowrap",
    "borderBottom": "2px solid #4fc3f7",
}

HEADER_STYLE_NO_SORT = {
    "backgroundColor": "#163d5c",
    "color": "#d0e8f7",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "6px 10px",
    "borderBottom": "2px solid #4fc3f7",
}

ACTIVE_HEADER_STYLE = {
    "backgroundColor": "#1a6fa8",
    "color": "white",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "6px 10px",
    "cursor": "pointer",
    "userSelect": "none",
    "whiteSpace": "nowrap",
    "borderBottom": "2px solid #4fc3f7",
}

CELL_STYLE = {
    "textAlign": "center",
    "padding": "5px 10px",
}

ACTIVE_CELL_STYLE = {
    "textAlign": "center",
    "padding": "5px 10px",
    "backgroundColor": "rgba(79, 195, 247, 0.08)",
}

TABLE_STYLE = {
    "width": "100%",
    "borderCollapse": "collapse",
    "tableLayout": "fixed",
}

STAT_COL_WIDTH = "60px"


def _build_colgroup():
    cols = [html.Col(style={"width": "180px"})]  # Name column
    for _ in HEADERS[1:]:
        cols.append(html.Col(style={"width": STAT_COL_WIDTH}))
    return html.Colgroup(cols)

HEADERS = [
    "Name",
    "Age",
    "Pos",
    "GP",
    "ATOI",
    "G",
    "A",
    "PTS",
    "S",
    "S%",
    "FOW",
    "FOL",
    "FO%",
    "BLK",
    "HIT",
    "ixG",
    "oixGF",
    "oixGA",
    "xG%",
]

SORTABLE_COLUMNS = [
    "Age",
    "Pos",
    "GP",
    "ATOI",
    "G",
    "A",
    "PTS",
    "S",
    "S%",
    "FOW",
    "FOL",
    "FO%",
    "BLK",
    "HIT",
    "ixG",
    "oixGF",
    "oixGA",
    "xG%",
]

# Maps header name -> field suffix (will be prefixed with situation prefix)
COLUMN_TO_FIELD = {
    "Age": "age",
    "Pos": "position",
    "GP": "games_played",
    "ATOI": "_atoi",
    "G": "_goals",
    "A": "_assists",
    "PTS": "_points",
    "S": "_shots",
    "S%": "_shooting_pct",
    "FOW": "_faceoffs_won",
    "FOL": "_faceoffs_lost",
    "FO%": "_faceoff_pct",
    "BLK": "_blocks",
    "HIT": "_checks",
    "ixG": "_i_xg",
    "oixGF": "_oi_xgf",
    "oixGA": "_oi_xga",
    "xG%": "_xg_pct",
}

# Fields that are NOT situation-dependent
STATIC_FIELDS = {"age", "position", "games_played", "penalties", "penalties_drawn"}

SITUATIONS = [
    ("tot", "All"),
    ("es", "Even Strength"),
    ("ev5", "5-on-5"),
    ("pp", "Power Play"),
    ("pk", "Short-Handed"),
]

SITUATION_BTN_BASE = {
    "padding": "4px 12px",
    "border": "1px solid #ccc",
    "cursor": "pointer",
    "fontSize": "14px",
    "fontWeight": "bold",
}


def _fmt_pct(val):
    if val is None:
        return ""
    return f"{val:.3f}"


def _seconds_to_mmss(seconds):
    """Convert seconds (float) to M:SS format."""
    if seconds is None:
        return ""
    total = int(seconds)
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


def _resolve_field(col_name, prefix):
    """Return the actual model field name for a column, applying prefix for situational fields."""
    raw = COLUMN_TO_FIELD.get(col_name, "_points")
    if raw.startswith("_"):
        return f"{prefix}{raw}"
    return raw


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
        Output("team-detail-breadcrumb", "children"),
        Input("team-detail-id", "data"),
    )
    def update_team_breadcrumb(team_id):
        crumbs = [
            dcc.Link("Team Standings", href="/team-standings", className="breadcrumb-link"),
            html.Span(" / ", className="breadcrumb-sep"),
        ]
        team_name = "Team"
        if team_id:
            team = Team.query.get(team_id)
            if team:
                team_name = team.name
        crumbs.append(html.Span(team_name, className="breadcrumb-current"))
        return html.Div(crumbs, className="breadcrumb-nav")

    @dash_app.callback(
        Output("team-detail-id", "data"),
        Input("url", "pathname"),
    )
    def store_team_id(pathname):
        if pathname and pathname.startswith("/team/"):
            parts = pathname.strip("/").split(
                "/"
            )  # ["team", id] or ["team", id, season]
            try:
                return int(parts[1])
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

    @dash_app.callback(
        Output("season-selector", "options"),
        Output("season-selector", "value"),
        Input("team-detail-id", "data"),
    )
    def update_season_dropdown(team_id):
        if not team_id:
            return [], None
        team = Team.query.get(team_id)
        if not team:
            return [], None
        # Find all teams for the same organization (one per season)
        org_teams = (
            Team.query.filter_by(organization_id=team.organization_id)
            .join(Season, Team.season_id == Season.id)
            .add_columns(Season.name.label("season_name"))
            .order_by(Season.name.desc())
            .all()
        )
        options = [
            {"label": season_name, "value": t.id} for t, season_name in org_teams
        ]
        return options, team_id

    @dash_app.callback(
        Output("team-detail-situation-toggle", "children"),
        Input("team-detail-id", "data"),
        Input("team-detail-situation", "data"),
    )
    def update_situation_toggle(team_id, selected_situation):
        if not team_id:
            return html.Div()

        selected = selected_situation or "tot"
        buttons = []
        for idx, (value, label) in enumerate(SITUATIONS):
            active = selected == value
            if idx == 0:
                radius = "4px 0 0 4px"
            elif idx == len(SITUATIONS) - 1:
                radius = "0 4px 4px 0"
            else:
                radius = "0"
            style = {
                **SITUATION_BTN_BASE,
                "backgroundColor": "#1a6fa8" if active else "#fff",
                "color": "#fff" if active else "#333",
                "borderRadius": radius,
            }
            buttons.append(
                html.Button(
                    label,
                    id={"type": "td-situation-btn", "index": value},
                    n_clicks=0,
                    style=style,
                )
            )

        return html.Div(
            [
                html.Span(
                    "Situation:",
                    style={
                        "fontWeight": "bold",
                        "marginRight": "8px",
                        "fontSize": "14px",
                    },
                ),
                html.Div(buttons, style={"display": "flex"}),
            ],
            style={"display": "flex", "alignItems": "center"},
        )

    @dash_app.callback(
        Output("team-detail-situation", "data"),
        Input({"type": "td-situation-btn", "index": ALL}, "n_clicks"),
        State("team-detail-situation", "data"),
        prevent_initial_call=True,
    )
    def toggle_situation(n_clicks, current_situation):
        if not ctx.triggered_id or not any(n for n in n_clicks if n):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        return ctx.triggered_id["index"]

    # Sort state callback
    @dash_app.callback(
        Output("team-detail-sort", "data"),
        [Input(f"td-sort-{h}", "n_clicks") for h in SORTABLE_COLUMNS],
        State("team-detail-sort", "data"),
    )
    def update_sort(*args):
        cb_ctx = callback_context
        if not cb_ctx.triggered or cb_ctx.triggered[0]["prop_id"] == ".":
            return no_update

        prop_id = cb_ctx.triggered[0]["prop_id"]

        # Ignore freshly rendered headers (n_clicks=0)
        triggered_value = cb_ctx.triggered[0]["value"]
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
        [
            Input("team-detail-sort", "data"),
            Input("season-selector", "value"),
            Input("team-detail-situation", "data"),
        ],
    )
    def update_roster(sort_data, active_team_id, situation=None):
        if not active_team_id:
            return html.Div()

        prefix = situation or "tot"
        sort_col = sort_data.get("column", "PTS") if sort_data else "PTS"
        sort_dir = sort_data.get("direction", "desc") if sort_data else "desc"

        query = (
            PlayerStats.query.join(Player, PlayerStats.player_id == Player.playerId)
            .filter(PlayerStats.team_id == active_team_id)
            .add_columns(Player.id, Player.firstName, Player.lastName, Player.position)
        )

        # Apply sort — push NULL to the bottom
        field = _resolve_field(sort_col, prefix)
        if field == "position":
            order_col = getattr(Player, field)
        else:
            order_col = getattr(PlayerStats, field)

        if sort_dir == "desc":
            order_col = order_col.desc()
        query = query.order_by(order_col.nulls_last())

        results = query.all()

        # Partition into skaters and goalies so goalies always appear at bottom
        skaters = [r for r in results if r[-1] != "G"]
        goalies = [r for r in results if r[-1] == "G"]
        goalies.sort(key=lambda r: r[0].games_played or 0, reverse=True)
        results = skaters + goalies

        thead = _build_thead(sort_col, sort_dir)

        num_skaters = len(skaters)
        rows = []
        for i, (ps, pid, first_name, last_name, pos) in enumerate(results):
            # Insert a separator row between skaters and goalies
            if i == num_skaters and goalies:
                rows.append(
                    html.Tr(
                        html.Td(
                            colSpan=len(HEADERS),
                            style={
                                "borderTop": "2px solid #163d5c",
                                "padding": "0",
                                "height": "0",
                            },
                        )
                    )
                )
            row_style = (
                {"backgroundColor": "#e8f4fb"}
                if i % 2 == 1
                else {"backgroundColor": "#ffffff"}
            )
            values = [
                ps.age,
                pos,
                ps.games_played,
                _seconds_to_mmss(getattr(ps, f"{prefix}_atoi")),
                getattr(ps, f"{prefix}_goals"),
                getattr(ps, f"{prefix}_assists"),
                getattr(ps, f"{prefix}_points"),
                getattr(ps, f"{prefix}_shots"),
                _fmt_pct(getattr(ps, f"{prefix}_shooting_pct")),
                getattr(ps, f"{prefix}_faceoffs_won"),
                getattr(ps, f"{prefix}_faceoffs_lost"),
                _fmt_pct(getattr(ps, f"{prefix}_faceoff_pct")),
                getattr(ps, f"{prefix}_blocks"),
                getattr(ps, f"{prefix}_checks"),
                getattr(ps, f"{prefix}_i_xg"),
                getattr(ps, f"{prefix}_oi_xgf"),
                getattr(ps, f"{prefix}_oi_xga"),
                _fmt_pct(getattr(ps, f"{prefix}_xg_pct")),
            ]
            stat_cols = HEADERS[1:]  # all columns except Name
            cells = [
                html.Td(
                    f"{first_name} {last_name}",
                    style={**CELL_STYLE, "textAlign": "left"},
                )
            ]
            for col, v in zip(stat_cols, values):
                cells.append(
                    html.Td(
                        v, style=ACTIVE_CELL_STYLE if col == sort_col else CELL_STYLE
                    )
                )
            rows.append(
                html.Tr(
                    cells,
                    style={**row_style, "cursor": "pointer"},
                    className="game-log-row",
                    id={"type": "team-roster-row", "index": pid},
                    n_clicks=0,
                )
            )

        colgroup = _build_colgroup()
        return html.Table(
            [colgroup, thead, html.Tbody(rows)],
            style=TABLE_STYLE,
        )

    @dash_app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Input({"type": "team-roster-row", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def navigate_to_player(n_clicks):
        if not ctx.triggered_id or not any(n for n in n_clicks if n):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        player_id = ctx.triggered_id["index"]
        return f"/player/{player_id}"
