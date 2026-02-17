"""Backfill i_xg, oi_xgf, oi_xga on each Stint row.

Loads all events with xG into memory for fast in-memory filtering.

Usage:
    python -m scripts.backfill_stint_xg
"""

import sys
from collections import defaultdict

from app import create_app
from app.extensions import db
from app.models import Event, Stint


def _progress(msg):
    print(msg)
    sys.stdout.flush()


def backfill():
    app = create_app()
    with app.app_context():
        # Pre-load all events with xG into memory
        _progress("Loading events with xG into memory...")
        xg_events = (
            db.session.query(
                Event.game_id,
                Event.period,
                Event.period_time,
                Event.team_abbr,
                Event.xg,
                Event.player_id,
            )
            .filter(Event.xg.isnot(None))
            .all()
        )
        xg_by_game_period = defaultdict(list)
        for game_id, period, pt, team_abbr, xg, pid in xg_events:
            xg_by_game_period[(game_id, period)].append((pt, team_abbr, xg, pid))
        _progress(f"  Loaded {len(xg_events)} events.")
        del xg_events

        # Process all stints
        all_stints = Stint.query.all()
        total = len(all_stints)
        _progress(f"Backfilling i_xg, oi_xgf, oi_xga for {total} stints...")

        for idx, stint in enumerate(all_stints, 1):
            if idx % 500 == 0 or idx == total:
                _progress(f"  Stints: {idx}/{total} ({idx * 100 // total}%)")

            i_xg = 0.0
            oi_xgf = 0.0
            oi_xga = 0.0

            if (
                stint.period_time_start is not None
                and stint.period_time_end is not None
            ):
                for evt_time, evt_team, evt_xg, evt_pid in xg_by_game_period.get(
                    (stint.game_id, stint.period), []
                ):
                    if (
                        evt_time is not None
                        and stint.period_time_start <= evt_time < stint.period_time_end
                    ):
                        if evt_team == stint.team_abbr:
                            oi_xgf += evt_xg
                            if evt_pid == stint.player_id:
                                i_xg += evt_xg
                        else:
                            oi_xga += evt_xg

            stint.i_xg = round(i_xg, 3)
            stint.oi_xgf = round(oi_xgf, 3)
            stint.oi_xga = round(oi_xga, 3)

        db.session.commit()
        _progress("Backfill complete.")


if __name__ == "__main__":
    backfill()
