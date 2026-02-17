"""Backfill oi_xgf and oi_xga for existing PlayerGameStats and PlayerStats.

Loads all events and stints into memory to avoid per-stint SQL queries.

Usage:
    python -m scripts.backfill_oi_xg
"""

import sys
from collections import defaultdict

from app import create_app
from app.extensions import db
from app.models import Event, PlayerGameStats, PlayerStats, Stint


def _progress(msg):
    print(msg)
    sys.stdout.flush()


def backfill():
    app = create_app()
    with app.app_context():
        # --- Pre-load all events with xG into memory ---
        _progress("Loading events with xG into memory...")
        xg_events = (
            db.session.query(
                Event.game_id,
                Event.period,
                Event.period_time,
                Event.team_abbr,
                Event.xg,
            )
            .filter(Event.xg.isnot(None))
            .all()
        )
        # Index by (game_id, period) for fast lookup
        events_by_game_period = defaultdict(list)
        for game_id, period, period_time, team_abbr, xg in xg_events:
            events_by_game_period[(game_id, period)].append(
                (period_time, team_abbr, xg)
            )
        _progress(f"  Loaded {len(xg_events)} events with xG values.")
        del xg_events  # free memory

        # --- Pre-load all stints into memory ---
        _progress("Loading stints into memory...")
        all_stints = db.session.query(
            Stint.player_id,
            Stint.game_id,
            Stint.period,
            Stint.period_time_start,
            Stint.period_time_end,
            Stint.team_abbr,
        ).all()
        # Index by (player_id, game_id)
        stints_by_player_game = defaultdict(list)
        for pid, gid, period, pt_start, pt_end, team_abbr in all_stints:
            stints_by_player_game[(pid, gid)].append(
                (period, pt_start, pt_end, team_abbr)
            )
        _progress(f"  Loaded {len(all_stints)} stints.")
        del all_stints

        # --- PlayerGameStats ---
        all_pgs = PlayerGameStats.query.all()
        total = len(all_pgs)
        _progress(
            f"Backfilling oi_xgf and oi_xga for {total} PlayerGameStats records..."
        )
        for idx, pgs in enumerate(all_pgs, 1):
            if idx % 100 == 0 or idx == total:
                _progress(f"  PlayerGameStats: {idx}/{total} ({idx * 100 // total}%)")

            stints = stints_by_player_game.get((pgs.player_id, pgs.game_id), [])
            if not stints:
                pgs.oi_xgf = 0.0
                pgs.oi_xga = 0.0
                continue

            player_team = stints[0][3]  # team_abbr from first stint
            oi_xgf = 0.0
            oi_xga = 0.0
            for period, pt_start, pt_end, _ in stints:
                for evt_time, evt_team, evt_xg in events_by_game_period.get(
                    (pgs.game_id, period), []
                ):
                    if (
                        evt_time is not None
                        and pt_start is not None
                        and pt_end is not None
                    ):
                        if pt_start <= evt_time < pt_end:
                            if evt_team == player_team:
                                oi_xgf += evt_xg
                            else:
                                oi_xga += evt_xg

            pgs.oi_xgf = round(oi_xgf, 3)
            pgs.oi_xga = round(oi_xga, 3)

        db.session.commit()
        _progress("Backfilled PlayerGameStats.")

        # --- PlayerStats (aggregate from PlayerGameStats) ---
        # Single query to sum oi_xgf/oi_xga grouped by player+team+season
        _progress("Backfilling oi_xgf, oi_xga, and xg_percentage for PlayerStats...")
        agg_results = (
            db.session.query(
                PlayerGameStats.player_id,
                PlayerGameStats.team_id,
                PlayerGameStats.season_id,
                db.func.coalesce(db.func.sum(PlayerGameStats.oi_xgf), 0.0),
                db.func.coalesce(db.func.sum(PlayerGameStats.oi_xga), 0.0),
            )
            .group_by(
                PlayerGameStats.player_id,
                PlayerGameStats.team_id,
                PlayerGameStats.season_id,
            )
            .all()
        )
        agg_map = {}
        for pid, tid, sid, xgf, xga in agg_results:
            agg_map[(pid, tid, sid)] = (float(xgf), float(xga))

        all_ps = PlayerStats.query.all()
        total = len(all_ps)
        for idx, ps in enumerate(all_ps, 1):
            if idx % 100 == 0 or idx == total:
                _progress(f"  PlayerStats: {idx}/{total} ({idx * 100 // total}%)")

            xgf, xga = agg_map.get((ps.player_id, ps.team_id, ps.season_id), (0.0, 0.0))
            ps.oi_xgf = round(xgf, 3)
            ps.oi_xga = round(xga, 3)
            total_oi_xg = ps.oi_xgf + ps.oi_xga
            ps.xg_percentage = (
                round(ps.oi_xgf / total_oi_xg, 3) if total_oi_xg > 0 else None
            )

        db.session.commit()
        _progress("Backfilled PlayerStats.")
        _progress("Backfill complete.")


if __name__ == "__main__":
    backfill()
