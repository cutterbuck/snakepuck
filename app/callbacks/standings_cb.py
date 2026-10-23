from collections import OrderedDict

from dash import ALL, Input, Output, State, callback_context, ctx, dcc, html, no_update

from app.models import Division, League, Season, Team, TeamStats

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

CELL_STYLE = {
    "textAlign": "center",
    "padding": "5px 10px",
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

ACTIVE_CELL_STYLE = {
    "textAlign": "center",
    "padding": "5px 10px",
    "backgroundColor": "rgba(79, 195, 247, 0.08)",
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

LEAGUE_HEADERS = [
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

DIVISION_HEADERS = [
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

DIVISION_TITLE_STYLE = {
    "backgroundColor": "#0d2137",
    "color": "#4fc3f7",
    "fontWeight": "bold",
    "fontSize": "16px",
    "padding": "10px 12px",
    "letterSpacing": "0.5px",
}


def _build_team_cell(team_name, team_logo, team_id=None):
    team_children = []
    if team_logo:
        team_children.append(
            html.Img(
                src=team_logo,
                style={
                    "width": "32px",
                    "height": "32px",
                    "verticalAlign": "middle",
                },
            )
        )
    team_children.append(
        html.Div(team_name, style={"display": "inline-block", "paddingLeft": "8px"})
    )

    if team_id:
        content = dcc.Link(
            html.Div(children=team_children),
            href=f"/team/{team_id}",
            className="team-link",
        )
    else:
        content = html.Div(children=team_children)

    return html.Td(
        content,
        style={
            "paddingTop": "2px",
            "paddingBottom": "2px",
            "width": "320px",
            "whiteSpace": "nowrap",
        },
    )


STAT_COLUMNS = [
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


def _fmt_pct(val):
    if val is None:
        return ""
    return f"{val:.3f}"


def _build_stat_cells(ts, sort_col=None):
    values = [
        ts.games_played,
        ts.wins,
        ts.losses,
        ts.ot_losses,
        ts.points,
        _fmt_pct(ts.points_percentage),
        ts.regulation_wins,
        ts.regulation_or_ot_wins,
        ts.goals_forward,
        ts.goals_against,
        ts.goal_diff,
        ts.so_record,
    ]
    return [
        html.Td(v, style=ACTIVE_CELL_STYLE if col == sort_col else CELL_STYLE)
        for col, v in zip(STAT_COLUMNS, values)
    ]


TABLE_STYLE = {
    "width": "100%",
    "borderCollapse": "collapse",
    "tableLayout": "fixed",
}

STAT_COL_WIDTH = "60px"


def _build_colgroup(headers):
    cols = []
    for h in headers:
        if h == "Team":
            cols.append(html.Col(style={"width": "260px"}))
        else:
            cols.append(html.Col(style={"width": STAT_COL_WIDTH}))
    return html.Colgroup(cols)


def _build_thead(headers, sort_col, sort_dir):
    header_cells = []
    for h in headers:
        if h in SORTABLE_COLUMNS:
            indicator = ""
            is_active = sort_col == h
            if is_active:
                indicator = " \u25bc" if sort_dir == "desc" else " \u25b2"
            header_cells.append(
                html.Th(
                    h + indicator,
                    id=f"sort-{h}",
                    n_clicks=0,
                    style=ACTIVE_HEADER_STYLE if is_active else HEADER_STYLE,
                )
            )
        else:
            header_cells.append(html.Th(h, style=HEADER_STYLE_NO_SORT))
    return html.Thead(html.Tr(header_cells))


def register_standings_callbacks(dash_app):
    # Populate League dropdown
    @dash_app.callback(
        Output("standings-league", "options"),
        Output("standings-league", "value"),
        Input("url", "pathname"),
    )
    def populate_league_dropdown(pathname):
        leagues = League.query.order_by(League.abbrev.desc()).all()
        options = [{"label": lg.name, "value": lg.id} for lg in leagues]
        default = None
        for lg in leagues:
            if lg.abbrev == "AHL":
                default = lg.id
                break
        if default is None and leagues:
            default = leagues[0].id
        return options, default

    # Populate Season dropdown based on selected league
    @dash_app.callback(
        Output("standings-season", "options"),
        Output("standings-season", "value"),
        Input("standings-league", "value"),
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

    # Toggle view and button styles
    @dash_app.callback(
        Output("standings-view", "data"),
        Output("standings-view-league", "outline"),
        Output("standings-view-division", "outline"),
        Input("standings-view-league", "n_clicks"),
        Input("standings-view-division", "n_clicks"),
        State("standings-view", "data"),
    )
    def toggle_view(league_clicks, division_clicks, current_view):
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]["prop_id"] == ".":
            return current_view, current_view != "league", current_view != "division"
        triggered = ctx.triggered[0]["prop_id"]
        if "standings-view-league" in triggered:
            return "league", False, True
        else:
            return "division", True, False

    # Sort state callback
    @dash_app.callback(
        Output("standings-sort", "data"),
        [Input(f"sort-{h}", "n_clicks") for h in SORTABLE_COLUMNS]
        + [Input("standings-league", "value"), Input("standings-season", "value")],
        State("standings-sort", "data"),
    )
    def update_sort(*args):
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]["prop_id"] == ".":
            return no_update

        prop_id = ctx.triggered[0]["prop_id"]

        # Reset to default sort when league or season changes
        if "standings-league" in prop_id or "standings-season" in prop_id:
            return {"column": "PTS", "direction": "desc"}

        col_name = prop_id.replace("sort-", "").replace(".n_clicks", "")

        # Ignore triggers from freshly rendered headers (n_clicks=0)
        triggered_value = ctx.triggered[0]["value"]
        if triggered_value is None or triggered_value == 0:
            return no_update

        current = args[-1]
        if current["column"] == col_name:
            new_dir = "asc" if current["direction"] == "desc" else "desc"
        else:
            new_dir = "desc"

        return {"column": col_name, "direction": new_dir}

    # Render standings table
    @dash_app.callback(
        Output("standings-table", "children"),
        [
            Input("standings-league", "value"),
            Input("standings-season", "value"),
            Input("standings-sort", "data"),
            Input("standings-view", "data"),
        ],
    )
    def update_standings(league_id, season_id, sort_data, view_mode):
        if not league_id or not season_id:
            return html.Div()

        sort_col = sort_data.get("column", "PTS") if sort_data else "PTS"
        sort_dir = sort_data.get("direction", "desc") if sort_data else "desc"

        field = COLUMN_TO_FIELD.get(sort_col, "points")
        order_col = getattr(TeamStats, field)
        if sort_dir == "desc":
            order_col = order_col.desc()

        # Tiebreakers when sorting by PTS: RW → ROW → W
        order_clauses = [order_col]
        if sort_col == "PTS":
            order_clauses.append(TeamStats.regulation_wins.desc())
            order_clauses.append(TeamStats.regulation_or_ot_wins.desc())
            order_clauses.append(TeamStats.wins.desc())

        results = (
            TeamStats.query.join(Team, TeamStats.team_id == Team.id)
            .join(Season, TeamStats.season_id == Season.id)
            .outerjoin(Division, TeamStats.division_id == Division.id)
            .filter(Team.league_id == league_id, TeamStats.season_id == season_id)
            .add_columns(
                Team.id.label("team_id"),
                Team.name,
                Team.logo,
                Division.name.label("division_name"),
                Season.name.label("season_name"),
            )
            .order_by(*order_clauses)
            .all()
        )

        if view_mode == "division":
            return _render_division_view(results, sort_col, sort_dir)
        else:
            return _render_league_view(results, sort_col, sort_dir)

    @dash_app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Input({"type": "standings-row", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def navigate_to_team(n_clicks):
        if not ctx.triggered_id or not any(n for n in n_clicks if n):
            from dash.exceptions import PreventUpdate

            raise PreventUpdate
        return ctx.triggered_id["index"]


def _render_league_view(results, sort_col, sort_dir):
    thead = _build_thead(LEAGUE_HEADERS, sort_col, sort_dir)

    rows = []
    for i, (ts, team_id, team_name, team_logo, division_name, season_name) in enumerate(results):
        row_style = (
            {"backgroundColor": "#e8f4fb"}
            if i % 2 == 1
            else {"backgroundColor": "#ffffff"}
        )
        team_cell = _build_team_cell(team_name, team_logo, team_id)
        stat_cells = _build_stat_cells(ts, sort_col)
        rows.append(
            html.Tr(
                [team_cell] + stat_cells,
                style={**row_style, "cursor": "pointer"},
                className="game-log-row",
                id={"type": "standings-row", "index": f"/team/{team_id}/{season_name}"},
                n_clicks=0,
            )
        )

    colgroup = _build_colgroup(LEAGUE_HEADERS)
    return html.Table(
        [colgroup, thead, html.Tbody(rows)],
        style=TABLE_STYLE,
    )


DIVISION_ORDER = ["Atlantic", "North", "Central", "Pacific"]


def _render_division_view(results, sort_col, sort_dir):
    # Group results by division
    divisions = {}
    for ts, team_id, team_name, team_logo, division_name, season_name in results:
        div_key = division_name or "Other"
        if div_key not in divisions:
            divisions[div_key] = []
        divisions[div_key].append((ts, team_id, team_name, team_logo, season_name))

    # Sort divisions into fixed order
    ordered_keys = [d for d in DIVISION_ORDER if d in divisions]
    for d in divisions:
        if d not in ordered_keys:
            ordered_keys.append(d)
    divisions = OrderedDict((k, divisions[k]) for k in ordered_keys)

    num_cols = len(DIVISION_HEADERS)
    thead = _build_thead(DIVISION_HEADERS, sort_col, sort_dir)

    rows = []
    for div_name, teams in divisions.items():
        # Division title as a full-width row
        rows.append(
            html.Tr(
                html.Td(
                    div_name + " Division",
                    colSpan=num_cols,
                    style=DIVISION_TITLE_STYLE,
                )
            )
        )

        for i, (ts, team_id, team_name, team_logo, season_name) in enumerate(teams):
            row_style = (
                {"backgroundColor": "#e8f4fb"}
                if i % 2 == 1
                else {"backgroundColor": "#ffffff"}
            )
            team_cell = _build_team_cell(team_name, team_logo, team_id)
            stat_cells = _build_stat_cells(ts, sort_col)
            rows.append(
                html.Tr(
                    [team_cell] + stat_cells,
                    style={**row_style, "cursor": "pointer"},
                    className="game-log-row",
                    id={"type": "standings-row", "index": f"/team/{team_id}/{season_name}"},
                    n_clicks=0,
                )
            )

    colgroup = _build_colgroup(DIVISION_HEADERS)
    return html.Table(
        [colgroup, thead, html.Tbody(rows)],
        style=TABLE_STYLE,
    )
