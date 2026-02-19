from collections import defaultdict

from dash import Input, Output, State, callback_context, html, no_update
from sqlalchemy import func

from app.extensions import db
from app.models import Event, Player, PlayerStats
from app.models.stint import Stint

MIN_GP = 20
MIN_LPR = 15
NEXT_PLAY_WINDOW = 5.0
NEXT_PLAY_SUCCESS_TYPES = {
    "pass",
    "puckprotection",
    "dumpout",
    "assist",
    "penaltydrawn",
    "controlledbreakout",
}
NEXT_PLAY_FAILURE_TYPES = {"failedpasslocation"}

LPR_DESCRIPTIONS = {
    "high": ["HI PRESS DUMP IN LPR+", "CONT HI PRESS DUMP IN LPR+"],
    "low": ["DUMP IN LPR+"],
}

HEADERS = ["Player", "GP", "LPR", "Avg oixGF", "Avg oixGA", "oixGF", "oixGA", "xG%"]

SORTABLE_COLUMNS = {"Avg oixGF", "Avg oixGA", "oixGF", "oixGA", "xG%"}

# Maps header -> index in table_data tuple
SORT_INDEX = {
    "Avg oixGF": 4,
    "Avg oixGA": 5,
    "oixGF": 6,
    "oixGA": 7,
    "xG%": 8,
}

HEADER_STYLE = {
    "backgroundColor": "#343a40",
    "color": "white",
    "fontWeight": "bold",
    "textAlign": "center",
    "padding": "4px 8px",
    "whiteSpace": "nowrap",
}

HEADER_STYLE_SORTABLE = {
    **HEADER_STYLE,
    "cursor": "pointer",
    "userSelect": "none",
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

NAME_CELL_STYLE = {
    "textAlign": "left",
    "padding": "4px 8px",
    "whiteSpace": "nowrap",
}

STRIPE_BG = "#f8f9fa"


def _build_thead(sort_col, sort_dir):
    cells = []
    for h in HEADERS:
        if h in SORTABLE_COLUMNS:
            is_active = sort_col == h
            indicator = ""
            if is_active:
                indicator = " \u25bc" if sort_dir == "desc" else " \u25b2"
            cells.append(
                html.Th(
                    h + indicator,
                    id=f"pa-lpr-sort-{h}",
                    n_clicks=0,
                    style=ACTIVE_HEADER_STYLE if is_active else HEADER_STYLE_SORTABLE,
                )
            )
        else:
            cells.append(html.Th(h, style=HEADER_STYLE))
    return html.Thead(html.Tr(cells))


RATE_HEADERS = ["Player", "GP", "Success", "Failure", "Success Rate"]
RATE_SORTABLE = {"Success", "Failure", "Success Rate"}
RATE_SORT_INDEX = {"Success": 3, "Failure": 4, "Success Rate": 5}


def _classify_next_play(lpr_events, lpr_game_ids):
    """Classify each LPR as success or failure based on next play within 5s.

    Returns dict: player_id -> {"success": int, "failure": int}
    """
    all_events = (
        Event.query.filter(Event.game_id.in_(lpr_game_ids))
        .order_by(Event.game_id, Event.period, Event.period_time, Event.id)
        .all()
    )

    player_game_events = defaultdict(list)
    for ev in all_events:
        if ev.player_id:
            player_game_events[(ev.game_id, ev.player_id)].append(ev)

    player_evt_idx = {}
    for key, evts in player_game_events.items():
        for i, ev in enumerate(evts):
            player_evt_idx[(key[0], key[1], ev.id)] = i

    counts = defaultdict(lambda: {"success": 0, "failure": 0})

    for e in lpr_events:
        idx = player_evt_idx.get((e.game_id, e.player_id, e.id))
        if idx is None:
            counts[e.player_id]["failure"] += 1
            continue

        evts = player_game_events[(e.game_id, e.player_id)]
        has_success = False
        has_failure = False

        for j in range(idx + 1, len(evts)):
            nxt = evts[j]
            if nxt.period != e.period:
                break
            if e.period_time is None or nxt.period_time is None:
                break
            if nxt.period_time - e.period_time > NEXT_PLAY_WINDOW:
                break
            if nxt.event_type in NEXT_PLAY_FAILURE_TYPES:
                has_failure = True
            if (
                nxt.event_type in NEXT_PLAY_SUCCESS_TYPES
                and nxt.outcome == "successful"
            ):
                has_success = True

        if has_success and not has_failure:
            counts[e.player_id]["success"] += 1
        else:
            counts[e.player_id]["failure"] += 1

    return counts


def _filter_by_next_play(lpr_events, lpr_game_ids, selection):
    """Filter LPR events based on whether the player's next play within 5s was successful."""
    all_events = (
        Event.query.filter(Event.game_id.in_(lpr_game_ids))
        .order_by(Event.game_id, Event.period, Event.period_time, Event.id)
        .all()
    )

    # Index by (game_id, player_id) -> sorted event list
    player_game_events = defaultdict(list)
    for ev in all_events:
        if ev.player_id:
            player_game_events[(ev.game_id, ev.player_id)].append(ev)

    # Reverse lookup: (game_id, player_id, event.id) -> index
    player_evt_idx = {}
    for key, evts in player_game_events.items():
        for i, ev in enumerate(evts):
            player_evt_idx[(key[0], key[1], ev.id)] = i

    keep_if_success = selection == "high_next_success"
    filtered = []

    for e in lpr_events:
        idx = player_evt_idx.get((e.game_id, e.player_id, e.id))
        if idx is None:
            if not keep_if_success:
                filtered.append(e)
            continue

        evts = player_game_events[(e.game_id, e.player_id)]
        has_success = False
        has_failure = False

        for j in range(idx + 1, len(evts)):
            nxt = evts[j]
            if nxt.period != e.period:
                break
            if e.period_time is None or nxt.period_time is None:
                break
            if nxt.period_time - e.period_time > NEXT_PLAY_WINDOW:
                break
            if nxt.event_type in NEXT_PLAY_FAILURE_TYPES:
                has_failure = True
            if (
                nxt.event_type in NEXT_PLAY_SUCCESS_TYPES
                and nxt.outcome == "successful"
            ):
                has_success = True

        # Failure types override success
        is_success = has_success and not has_failure
        if is_success == keep_if_success:
            filtered.append(e)

    return filtered


def register_player_analysis_callbacks(dash_app):
    # ── Sort state callback ────────────────────────────────────────
    @dash_app.callback(
        Output("pa-lpr-sort", "data"),
        [Input(f"pa-lpr-sort-{h}", "n_clicks") for h in SORTABLE_COLUMNS],
        State("pa-lpr-sort", "data"),
    )
    def update_lpr_sort(*args):
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]["prop_id"] == ".":
            return no_update

        prop_id = ctx.triggered[0]["prop_id"]
        triggered_value = ctx.triggered[0]["value"]
        if triggered_value is None or triggered_value == 0:
            return no_update

        col_name = prop_id.replace("pa-lpr-sort-", "").replace(".n_clicks", "")
        current = args[-1]
        if current["column"] == col_name:
            new_dir = "asc" if current["direction"] == "desc" else "desc"
        else:
            new_dir = "desc"

        return {"column": col_name, "direction": new_dir}

    # ── Subtitle callback ─────────────────────────────────────────
    @dash_app.callback(
        Output("pa-dmen-lpr-subtitle", "children"),
        Input("pa-dmen-lpr-dropdown", "value"),
    )
    def update_lpr_subtitle(selection):
        if selection == "high_next_success":
            return "Expected goals after high-pressure LPRs where the defenseman's next play within 5s was successful (5-on-5, min. 20 GP, min. 15 LPRs)"
        if selection == "high_next_failure":
            return "Expected goals after high-pressure LPRs where the defenseman had no successful next play within 5s (5-on-5, min. 20 GP, min. 15 LPRs)"
        if selection == "high_next_rate":
            return "Next play success rate after high-pressure LPRs (5-on-5, min. 20 GP, min. 15 LPRs)"
        return "Expected goals for the rest of the defenseman's shift or until a faceoff occurs (5-on-5, min. 20 GP, min. 15 LPRs)"

    # ── Main table callback ────────────────────────────────────────
    @dash_app.callback(
        Output("player-analysis-dmen-lpr", "children"),
        Input("url", "pathname"),
        Input("pa-lpr-sort", "data"),
        Input("pa-dmen-lpr-dropdown", "value"),
    )
    def update_dmen_lpr(pathname, sort_data, lpr_selection):
        if pathname != "/player-analysis":
            return no_update

        sort_col = sort_data.get("column", "xG%") if sort_data else "xG%"
        sort_dir = sort_data.get("direction", "desc") if sort_data else "desc"

        # ── Step 1: Get qualifying defensemen (>= MIN_GP) ──────────
        gp_rows = (
            db.session.query(
                PlayerStats.player_id,
                func.sum(PlayerStats.games_played).label("total_gp"),
            )
            .join(Player, PlayerStats.player_id == Player.playerId)
            .filter(Player.position == "D")
            .group_by(PlayerStats.player_id)
            .having(func.sum(PlayerStats.games_played) >= MIN_GP)
            .all()
        )
        if not gp_rows:
            return html.P("No data available.", className="text-muted")

        qualifying_players = {row.player_id: row.total_gp for row in gp_rows}
        player_ids = list(qualifying_players.keys())

        # ── Step 2: Get 5v5 game_stint set ─────────────────────────
        ev5_rows = (
            db.session.query(Stint.game_id, Stint.game_stint)
            .filter(Stint.n_home_skaters == 5, Stint.n_away_skaters == 5)
            .distinct()
            .all()
        )
        ev5_set = {(r.game_id, r.game_stint) for r in ev5_rows}

        # ── Step 3: Get all qualifying LPR events ──────────────────
        if lpr_selection in (
            "high_next_success",
            "high_next_failure",
            "high_next_rate",
        ):
            descriptions = LPR_DESCRIPTIONS["high"]
        else:
            descriptions = LPR_DESCRIPTIONS.get(lpr_selection, LPR_DESCRIPTIONS["high"])
        lpr_events = Event.query.filter(
            Event.event_type == "lpr",
            Event.description.in_(descriptions),
            Event.player_id.in_(player_ids),
        ).all()
        # Filter to 5v5 only
        lpr_events = [e for e in lpr_events if (e.game_id, e.game_stint) in ev5_set]

        if not lpr_events:
            return html.P("No data available.", className="text-muted")

        # Collect game_ids and player_ids involved
        lpr_game_ids = {e.game_id for e in lpr_events}
        lpr_player_ids = {e.player_id for e in lpr_events}

        # ── Success Rate table (separate rendering) ────────────────
        if lpr_selection == "high_next_rate":
            counts = _classify_next_play(lpr_events, lpr_game_ids)

            player_name_rows = Player.query.filter(
                Player.playerId.in_(lpr_player_ids)
            ).all()
            player_names = {
                p.playerId: (p.firstName, p.lastName) for p in player_name_rows
            }

            table_data = []
            for pid, c in counts.items():
                total = c["success"] + c["failure"]
                if total < MIN_LPR:
                    continue
                first, last = player_names.get(pid, ("Unknown", ""))
                gp = qualifying_players.get(pid, 0)
                rate = c["success"] / total * 100 if total > 0 else 0
                table_data.append((first, last, gp, c["success"], c["failure"], rate))

            # Sort
            rate_sort_col = sort_col if sort_col in RATE_SORTABLE else "Success Rate"
            rate_sort_idx = RATE_SORT_INDEX.get(rate_sort_col, 5)
            table_data.sort(
                key=lambda r: r[rate_sort_idx], reverse=(sort_dir == "desc")
            )

            # Header
            cells = []
            for h in RATE_HEADERS:
                if h in RATE_SORTABLE:
                    is_active = rate_sort_col == h
                    indicator = ""
                    if is_active:
                        indicator = " \u25bc" if sort_dir == "desc" else " \u25b2"
                    cells.append(
                        html.Th(
                            h + indicator,
                            id=f"pa-lpr-sort-{h}",
                            n_clicks=0,
                            style=(
                                ACTIVE_HEADER_STYLE
                                if is_active
                                else HEADER_STYLE_SORTABLE
                            ),
                        )
                    )
                else:
                    cells.append(html.Th(h, style=HEADER_STYLE))
            thead = html.Thead(html.Tr(cells))

            # Totals
            n_players = len(table_data)
            total_success = sum(r[3] for r in table_data)
            total_failure = sum(r[4] for r in table_data)
            avg_rate = sum(r[5] for r in table_data) / n_players if n_players else 0

            # Rows
            rows = []
            for i, (first, last, gp, succ, fail, rate) in enumerate(table_data):
                bg = {"backgroundColor": STRIPE_BG} if i % 2 == 1 else {}
                cells = [
                    html.Td(f"{first} {last}", style={**NAME_CELL_STYLE, **bg}),
                    html.Td(gp, style={**CELL_STYLE, **bg}),
                    html.Td(
                        succ,
                        style={
                            **(
                                ACTIVE_CELL_STYLE
                                if rate_sort_col == "Success"
                                else CELL_STYLE
                            ),
                            **bg,
                        },
                    ),
                    html.Td(
                        fail,
                        style={
                            **(
                                ACTIVE_CELL_STYLE
                                if rate_sort_col == "Failure"
                                else CELL_STYLE
                            ),
                            **bg,
                        },
                    ),
                    html.Td(
                        f"{rate:.1f}%",
                        style={
                            **(
                                ACTIVE_CELL_STYLE
                                if rate_sort_col == "Success Rate"
                                else CELL_STYLE
                            ),
                            **bg,
                        },
                    ),
                ]
                rows.append(html.Tr(cells))

            # Total row
            total_style = {
                **CELL_STYLE,
                "fontWeight": "bold",
                "borderBottom": "2px solid #343a40",
            }
            total_name_style = {
                **NAME_CELL_STYLE,
                "fontWeight": "bold",
                "borderBottom": "2px solid #343a40",
            }
            total_row = html.Tr(
                [
                    html.Td("Total", style=total_name_style),
                    html.Td("", style=total_style),
                    html.Td(total_success, style=total_style),
                    html.Td(total_failure, style=total_style),
                    html.Td(f"{avg_rate:.1f}%", style=total_style),
                ]
            )
            rows.insert(0, total_row)

            return html.Table(
                [thead, html.Tbody(rows)],
                style={"width": "100%", "borderCollapse": "collapse"},
            )

        # ── Step 3b: Filter by next play if needed ─────────────────
        if lpr_selection in ("high_next_success", "high_next_failure"):
            lpr_events = _filter_by_next_play(lpr_events, lpr_game_ids, lpr_selection)
            if not lpr_events:
                return html.P("No data available.", className="text-muted")
            lpr_game_ids = {e.game_id for e in lpr_events}
            lpr_player_ids = {e.player_id for e in lpr_events}

        # ── Step 4: Batch-fetch all stints for these players/games ─
        all_stints = Stint.query.filter(
            Stint.game_id.in_(lpr_game_ids),
            Stint.player_id.in_(lpr_player_ids),
        ).all()
        # Index: (game_id, player_id, shift) -> sorted list of stints
        shift_stints = defaultdict(list)
        stint_lookup = {}
        for s in all_stints:
            if s.shift is not None:
                shift_stints[(s.game_id, s.player_id, s.shift)].append(s)
            stint_lookup[(s.game_id, s.player_id, s.game_stint)] = s

        for key in shift_stints:
            shift_stints[key].sort(key=lambda s: s.game_stint)

        # ── Step 5: Batch-fetch all faceoff events for these games ─
        faceoff_events = Event.query.filter(
            Event.event_type == "faceoff",
            Event.game_id.in_(lpr_game_ids),
        ).all()
        # Index: (game_id, game_stint) -> True
        faceoff_stints = set()
        for fo in faceoff_events:
            faceoff_stints.add((fo.game_id, fo.game_stint))

        # ── Step 6: Calculate post-LPR xGF/xGA per event ──────────
        player_data = defaultdict(
            lambda: {"lpr_count": 0, "total_xgf": 0.0, "total_xga": 0.0}
        )

        for e in lpr_events:
            stint = stint_lookup.get((e.game_id, e.player_id, e.game_stint))
            if not stint or stint.shift is None:
                continue

            shift_key = (e.game_id, e.player_id, stint.shift)
            stints_in_shift = shift_stints.get(shift_key, [])

            post_lpr_xgf = 0.0
            post_lpr_xga = 0.0

            for s in stints_in_shift:
                if s.game_stint < e.game_stint:
                    continue

                post_lpr_xgf += s.tot_oi_xgf or 0.0
                post_lpr_xga += s.tot_oi_xga or 0.0

                if (s.game_id, s.game_stint) in faceoff_stints:
                    break

            pd = player_data[e.player_id]
            pd["lpr_count"] += 1
            pd["total_xgf"] += post_lpr_xgf
            pd["total_xga"] += post_lpr_xga

        # ── Step 7: Get player names ───────────────────────────────
        player_name_rows = Player.query.filter(
            Player.playerId.in_(lpr_player_ids)
        ).all()
        player_names = {p.playerId: (p.firstName, p.lastName) for p in player_name_rows}

        # ── Step 8: Build table data ───────────────────────────────
        table_data = []
        for pid, pd in player_data.items():
            if pd["lpr_count"] < MIN_LPR:
                continue
            first, last = player_names.get(pid, ("Unknown", ""))
            gp = qualifying_players.get(pid, 0)
            avg_xgf = pd["total_xgf"] / pd["lpr_count"]
            avg_xga = pd["total_xga"] / pd["lpr_count"]
            cum_xgf = pd["total_xgf"]
            cum_xga = pd["total_xga"]
            xg_pct = (
                (cum_xgf / (cum_xgf + cum_xga) * 100) if (cum_xgf + cum_xga) > 0 else 0
            )
            table_data.append(
                (
                    first,
                    last,
                    gp,
                    pd["lpr_count"],
                    avg_xgf,
                    avg_xga,
                    cum_xgf,
                    cum_xga,
                    xg_pct,
                )
            )

        # ── Sort ───────────────────────────────────────────────────
        sort_idx = SORT_INDEX.get(sort_col, 8)
        table_data.sort(key=lambda r: r[sort_idx], reverse=(sort_dir == "desc"))

        # ── Totals ─────────────────────────────────────────────────
        total_lpr = sum(r[3] for r in table_data)
        total_cum_xgf = sum(r[6] for r in table_data)
        total_cum_xga = sum(r[7] for r in table_data)
        n_players = len(table_data)
        avg_avg_xgf = sum(r[4] for r in table_data) / n_players if n_players else 0
        avg_avg_xga = sum(r[5] for r in table_data) / n_players if n_players else 0
        avg_xg_pct = sum(r[8] for r in table_data) / n_players if n_players else 0

        # ── Render ─────────────────────────────────────────────────
        thead = _build_thead(sort_col, sort_dir)

        rows = []
        for i, (
            first,
            last,
            gp,
            lpr,
            avg_xgf,
            avg_xga,
            cum_xgf,
            cum_xga,
            xg_pct,
        ) in enumerate(table_data):
            bg = {"backgroundColor": STRIPE_BG} if i % 2 == 1 else {}
            is_active_col = [h in SORTABLE_COLUMNS and h == sort_col for h in HEADERS]
            cells = [
                html.Td(f"{first} {last}", style={**NAME_CELL_STYLE, **bg}),
                html.Td(gp, style={**CELL_STYLE, **bg}),
                html.Td(lpr, style={**CELL_STYLE, **bg}),
                html.Td(
                    f"{avg_xgf:.3f}",
                    style={
                        **(ACTIVE_CELL_STYLE if is_active_col[3] else CELL_STYLE),
                        **bg,
                    },
                ),
                html.Td(
                    f"{avg_xga:.3f}",
                    style={
                        **(ACTIVE_CELL_STYLE if is_active_col[4] else CELL_STYLE),
                        **bg,
                    },
                ),
                html.Td(
                    f"{cum_xgf:.2f}",
                    style={
                        **(ACTIVE_CELL_STYLE if is_active_col[5] else CELL_STYLE),
                        **bg,
                    },
                ),
                html.Td(
                    f"{cum_xga:.2f}",
                    style={
                        **(ACTIVE_CELL_STYLE if is_active_col[6] else CELL_STYLE),
                        **bg,
                    },
                ),
                html.Td(
                    f"{xg_pct:.1f}%",
                    style={
                        **(ACTIVE_CELL_STYLE if is_active_col[7] else CELL_STYLE),
                        **bg,
                    },
                ),
            ]
            rows.append(html.Tr(cells))

        # ── Total row ─────────────────────────────────────────────
        total_style = {
            **CELL_STYLE,
            "fontWeight": "bold",
            "borderBottom": "2px solid #343a40",
        }
        total_name_style = {
            **NAME_CELL_STYLE,
            "fontWeight": "bold",
            "borderBottom": "2px solid #343a40",
        }
        total_row = html.Tr(
            [
                html.Td("Total", style=total_name_style),
                html.Td("", style=total_style),
                html.Td(total_lpr, style=total_style),
                html.Td(f"{avg_avg_xgf:.3f}", style=total_style),
                html.Td(f"{avg_avg_xga:.3f}", style=total_style),
                html.Td(f"{total_cum_xgf:.2f}", style=total_style),
                html.Td(f"{total_cum_xga:.2f}", style=total_style),
                html.Td(f"{avg_xg_pct:.1f}%", style=total_style),
            ]
        )
        rows.insert(0, total_row)

        return html.Table(
            [thead, html.Tbody(rows)],
            style={"width": "100%", "borderCollapse": "collapse"},
        )
