from collections import OrderedDict

from dash import Input, Output, State, callback_context, html, no_update

from app.models import Division, League, Season, Team, TeamStats

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

ACTIVE_HEADER_STYLE = {
    "backgroundColor": "#4a6fa5",
    "color": "white",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "8px",
    "cursor": "pointer",
    "userSelect": "none",
    "whiteSpace": "nowrap",
}

ACTIVE_CELL_STYLE = {
    "textAlign": "center",
    "padding": "8px",
    "backgroundColor": "rgba(74, 111, 165, 0.1)",
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
    "backgroundColor": "#1a1a2e",
    "color": "white",
    "fontWeight": "bold",
    "fontSize": "16px",
    "padding": "10px 8px",
}


def _build_team_cell(team_name, team_logo):
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
    return html.Td(
        html.Div(children=team_children),
        style={
            "paddingTop": "5px",
            "paddingBottom": "5px",
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


def _build_stat_cells(ts, sort_col=None):
    values = [
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
    return [
        html.Td(v, style=ACTIVE_CELL_STYLE if col == sort_col else CELL_STYLE)
        for col, v in zip(STAT_COLUMNS, values)
    ]


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
        options = [{"label": l.name, "value": l.id} for l in leagues]
        default = None
        for l in leagues:
            if l.abbrev == "AHL":
                default = l.id
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

        results = (
            TeamStats.query.join(Team, TeamStats.team_id == Team.id)
            .outerjoin(Division, TeamStats.division_id == Division.id)
            .filter(Team.league_id == league_id, TeamStats.season_id == season_id)
            .add_columns(Team.name, Team.logo, Division.name.label("division_name"))
            .order_by(order_col)
            .all()
        )

        if view_mode == "division":
            return _render_division_view(results, sort_col, sort_dir)
        else:
            return _render_league_view(results, sort_col, sort_dir)


def _render_league_view(results, sort_col, sort_dir):
    thead = _build_thead(LEAGUE_HEADERS, sort_col, sort_dir)

    rows = []
    for i, (ts, team_name, team_logo, division_name) in enumerate(results):
        row_style = (
            {"backgroundColor": "rgb(245, 245, 245)"}
            if i % 2 == 1
            else {"backgroundColor": "rgb(255, 255, 255)"}
        )
        team_cell = _build_team_cell(team_name, team_logo)
        stat_cells = _build_stat_cells(ts, sort_col)
        rows.append(html.Tr([team_cell] + stat_cells, style=row_style))

    return html.Table(
        [thead, html.Tbody(rows)],
        style={"overflowX": "auto", "width": "100%", "borderCollapse": "collapse"},
    )


DIVISION_ORDER = ["Atlantic", "North", "Central", "Pacific"]


def _render_division_view(results, sort_col, sort_dir):
    # Group results by division
    divisions = {}
    for ts, team_name, team_logo, division_name in results:
        div_key = division_name or "Other"
        if div_key not in divisions:
            divisions[div_key] = []
        divisions[div_key].append((ts, team_name, team_logo))

    # Sort divisions into fixed order
    ordered_keys = [d for d in DIVISION_ORDER if d in divisions]
    for d in divisions:
        if d not in ordered_keys:
            ordered_keys.append(d)
    divisions = OrderedDict((k, divisions[k]) for k in ordered_keys)

    tables = []
    for div_name, teams in divisions.items():
        # Division title
        tables.append(
            html.Div(
                div_name + " Division",
                style=DIVISION_TITLE_STYLE,
            )
        )

        thead = _build_thead(DIVISION_HEADERS, sort_col, sort_dir)

        rows = []
        for i, (ts, team_name, team_logo) in enumerate(teams):
            row_style = (
                {"backgroundColor": "rgb(245, 245, 245)"}
                if i % 2 == 1
                else {"backgroundColor": "rgb(255, 255, 255)"}
            )
            team_cell = _build_team_cell(team_name, team_logo)
            stat_cells = _build_stat_cells(ts, sort_col)
            rows.append(html.Tr([team_cell] + stat_cells, style=row_style))

        tables.append(
            html.Table(
                [thead, html.Tbody(rows)],
                style={
                    "overflowX": "auto",
                    "width": "100%",
                    "borderCollapse": "collapse",
                    "marginBottom": "24px",
                },
            )
        )

    return html.Div(tables)
