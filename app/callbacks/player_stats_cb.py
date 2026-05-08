from dash import ALL, Input, Output, State, callback_context, ctx, dcc, html, no_update

from app.models import League, Player, PlayerStats, Season, Team

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
PAGE_SIZE = 25

HEADERS = [
    "Name",
    "Team",
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

STATIC_FIELDS = {"age", "position", "games_played"}

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
    if seconds is None:
        return ""
    total = int(seconds)
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


def _resolve_field(col_name, prefix):
    raw = COLUMN_TO_FIELD.get(col_name, "_points")
    if raw.startswith("_"):
        return f"{prefix}{raw}"
    return raw


def _build_colgroup():
    cols = [
        html.Col(style={"width": "180px"}),  # Name
        html.Col(style={"width": "90px"}),  # Team
    ]
    for _ in HEADERS[2:]:
        cols.append(html.Col(style={"width": STAT_COL_WIDTH}))
    return html.Colgroup(cols)


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
                    id=f"ps-sort-{h}",
                    n_clicks=0,
                    style=ACTIVE_HEADER_STYLE if is_active else HEADER_STYLE,
                )
            )
        else:
            header_cells.append(html.Th(h, style=HEADER_STYLE_NO_SORT))
    return html.Thead(html.Tr(header_cells))


def register_player_stats_callbacks(dash_app):
    @dash_app.callback(
        Output("ps-league", "options"),
        Output("ps-league", "value"),
        Input("url", "pathname"),
    )
    def populate_league_dropdown(pathname):
        leagues = League.query.order_by(League.abbrev.desc()).all()
        options = [{"label": l.name, "value": l.id} for l in leagues]
        default = None
        for l in leagues:
            if l.abbrev == "AHL":
                default = l.id
                break
        if default is None and leagues:
            default = leagues[0].id
        return options, default

    @dash_app.callback(
        Output("ps-season", "options"),
        Output("ps-season", "value"),
        Input("ps-league", "value"),
    )
    def populate_season_dropdown(league_id):
        if not league_id:
            return [], None
        seasons = (
            Season.query.join(Team, Team.season_id == Season.id)
            .filter(Team.league_id == league_id)
            .distinct()
            .order_by(Season.name.desc())
            .all()
        )
        options = [{"label": s.name, "value": s.id} for s in seasons]
        default = None
        for s in seasons:
            if s.name == "2023-24":
                default = s.id
                break
        if default is None and seasons:
            default = seasons[0].id
        return options, default

    @dash_app.callback(
        Output("ps-situation-toggle", "children"),
        Input("ps-situation", "data"),
    )
    def update_situation_toggle(selected_situation):
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
                    id={"type": "ps-situation-btn", "index": value},
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
        Output("ps-situation", "data"),
        Input({"type": "ps-situation-btn", "index": ALL}, "n_clicks"),
        State("ps-situation", "data"),
        prevent_initial_call=True,
    )
    def toggle_situation(n_clicks, current_situation):
        if not ctx.triggered_id or not any(n for n in n_clicks if n):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        return ctx.triggered_id["index"]

    @dash_app.callback(
        Output("ps-sort", "data"),
        [Input(f"ps-sort-{h}", "n_clicks") for h in SORTABLE_COLUMNS]
        + [Input("ps-league", "value"), Input("ps-season", "value")],
        State("ps-sort", "data"),
    )
    def update_sort(*args):
        cb_ctx = callback_context
        if not cb_ctx.triggered or cb_ctx.triggered[0]["prop_id"] == ".":
            return no_update

        prop_id = cb_ctx.triggered[0]["prop_id"]

        if "ps-league" in prop_id or "ps-season" in prop_id:
            return {"column": "PTS", "direction": "desc"}

        triggered_value = cb_ctx.triggered[0]["value"]
        if triggered_value is None or triggered_value == 0:
            return no_update

        col_name = prop_id.replace("ps-sort-", "").replace(".n_clicks", "")

        current = args[-1]
        if current["column"] == col_name:
            new_dir = "asc" if current["direction"] == "desc" else "desc"
        else:
            new_dir = "desc"

        return {"column": col_name, "direction": new_dir}

    # Reset page to 1 when filters change
    @dash_app.callback(
        Output("ps-page", "data"),
        [
            Input("ps-league", "value"),
            Input("ps-season", "value"),
            Input("ps-sort", "data"),
            Input("ps-situation", "data"),
            Input({"type": "ps-page-btn", "index": ALL}, "n_clicks"),
        ],
        State("ps-page", "data"),
    )
    def update_page(league_id, season_id, sort_data, situation, page_clicks, current_page):
        cb_ctx = callback_context
        if not cb_ctx.triggered or cb_ctx.triggered[0]["prop_id"] == ".":
            return 1

        prop_id = cb_ctx.triggered[0]["prop_id"]

        # If a page button was clicked
        if "ps-page-btn" in prop_id:
            triggered_value = cb_ctx.triggered[0]["value"]
            if triggered_value is None or triggered_value == 0:
                return no_update
            return ctx.triggered_id["index"]

        # Any other filter changed — reset to page 1
        return 1

    @dash_app.callback(
        Output("ps-table", "children"),
        Output("ps-pagination", "children"),
        [
            Input("ps-league", "value"),
            Input("ps-season", "value"),
            Input("ps-sort", "data"),
            Input("ps-situation", "data"),
            Input("ps-page", "data"),
        ],
    )
    def update_player_stats(league_id, season_id, sort_data, situation, page):
        if not league_id or not season_id:
            return html.Div(), html.Div()

        prefix = situation or "tot"
        sort_col = sort_data.get("column", "PTS") if sort_data else "PTS"
        sort_dir = sort_data.get("direction", "desc") if sort_data else "desc"
        page = page or 1

        query = (
            PlayerStats.query.join(Player, PlayerStats.player_id == Player.playerId)
            .join(Team, PlayerStats.team_id == Team.id)
            .filter(Team.league_id == league_id, PlayerStats.season_id == season_id)
            .add_columns(
                Player.id,
                Player.firstName,
                Player.lastName,
                Player.position,
                Team.abbrev.label("team_abbrev"),
                Team.logo.label("team_logo"),
                Team.id.label("team_id"),
            )
        )

        field = _resolve_field(sort_col, prefix)
        if field == "position":
            order_col = getattr(Player, field)
        else:
            order_col = getattr(PlayerStats, field)

        if sort_dir == "desc":
            order_col = order_col.desc()
        query = query.order_by(order_col.nulls_last())

        total = query.count()
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, total_pages)
        offset = (page - 1) * PAGE_SIZE

        results = query.offset(offset).limit(PAGE_SIZE).all()

        thead = _build_thead(sort_col, sort_dir)
        colgroup = _build_colgroup()

        rows = []
        for i, (ps, pid, first_name, last_name, pos, team_abbrev, team_logo, team_id) in enumerate(results):
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

            stat_cols = HEADERS[2:]  # all columns except Name and Team

            # Name cell
            cells = [
                html.Td(
                    html.A(
                        f"{first_name} {last_name}",
                        href=f"/player/{pid}",
                        className="team-link",
                        style={"display": "block", "padding": "4px 8px"},
                    ),
                    style={**CELL_STYLE, "textAlign": "left", "padding": "0"},
                )
            ]

            # Team cell
            team_children = []
            if team_logo:
                team_children.append(
                    html.Img(
                        src=team_logo,
                        style={
                            "width": "24px",
                            "height": "24px",
                            "verticalAlign": "middle",
                            "marginRight": "6px",
                        },
                    )
                )
            team_children.append(html.Span(team_abbrev))
            cells.append(
                html.Td(
                    dcc.Link(
                        html.Div(team_children),
                        href=f"/team/{team_id}",
                        className="team-link",
                    ),
                    style={**CELL_STYLE, "textAlign": "left", "whiteSpace": "nowrap"},
                )
            )

            # Stat cells
            for col, v in zip(stat_cols, values):
                cells.append(
                    html.Td(
                        v, style=ACTIVE_CELL_STYLE if col == sort_col else CELL_STYLE
                    )
                )
            rows.append(html.Tr(cells, style=row_style))

        table = html.Table(
            [colgroup, thead, html.Tbody(rows)],
            style=TABLE_STYLE,
        )

        # Pagination controls
        pagination = _build_pagination(page, total_pages, total)

        return table, pagination


def _build_pagination(current_page, total_pages, total):
    if total_pages <= 1:
        return html.Div()

    start = (current_page - 1) * PAGE_SIZE + 1
    end = min(current_page * PAGE_SIZE, total)

    btn_style = {
        "padding": "6px 14px",
        "border": "1px solid #ccc",
        "cursor": "pointer",
        "fontSize": "14px",
        "fontWeight": "bold",
        "backgroundColor": "#fff",
        "color": "#333",
        "borderRadius": "4px",
    }

    active_btn_style = {
        **btn_style,
        "backgroundColor": "#1a6fa8",
        "color": "#fff",
        "borderColor": "#1a6fa8",
    }

    disabled_btn_style = {
        **btn_style,
        "cursor": "default",
        "opacity": "0.5",
    }

    buttons = []

    # Previous button
    if current_page > 1:
        buttons.append(
            html.Button(
                "\u25c0 Prev",
                id={"type": "ps-page-btn", "index": current_page - 1},
                n_clicks=0,
                style=btn_style,
            )
        )
    else:
        buttons.append(
            html.Button("\u25c0 Prev", disabled=True, style=disabled_btn_style)
        )

    # Page number buttons
    for p in range(1, total_pages + 1):
        if total_pages <= 7 or abs(p - current_page) <= 2 or p == 1 or p == total_pages:
            buttons.append(
                html.Button(
                    str(p),
                    id={"type": "ps-page-btn", "index": p},
                    n_clicks=0,
                    style=active_btn_style if p == current_page else btn_style,
                )
            )
        elif buttons and not isinstance(buttons[-1], str) and getattr(buttons[-1], 'children', None) != "...":
            buttons.append(html.Span("...", style={"padding": "6px 8px", "fontSize": "14px"}))

    # Next button
    if current_page < total_pages:
        buttons.append(
            html.Button(
                "Next \u25b6",
                id={"type": "ps-page-btn", "index": current_page + 1},
                n_clicks=0,
                style=btn_style,
            )
        )
    else:
        buttons.append(
            html.Button("Next \u25b6", disabled=True, style=disabled_btn_style)
        )

    return html.Div(
        [
            html.Div(
                buttons,
                style={"display": "flex", "gap": "4px", "alignItems": "center"},
            ),
            html.Span(
                f"Showing {start}-{end} of {total} players",
                style={"fontSize": "13px", "color": "#6c757d", "marginTop": "6px"},
            ),
        ],
        style={"display": "flex", "flexDirection": "column", "alignItems": "center"},
    )
