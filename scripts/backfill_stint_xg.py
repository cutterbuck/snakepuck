"""Backfill tot_/es_/ev5_/pp_/pk_ xG columns on each Stint row.

Loads all events with xG into memory for fast in-memory filtering.

Usage:
    python -m scripts.backfill_stint_xg
"""

import sys
from collections import defaultdict

from app import create_app
from app.extensions import db
from app.models import Event, Game, Stint, Team


def _progress(msg):
    print(msg)
    sys.stdout.flush()


def backfill():
    app = create_app()
    with app.app_context():
        # Build game_id -> (home_abbr, away_abbr) mapping
        _progress("Building game home/away mapping...")
        HomeTeam = db.aliased(Team)
        AwayTeam = db.aliased(Team)
        game_rows = (
            db.session.query(
                Game.game_id,
                HomeTeam.abbrev,
                AwayTeam.abbrev,
            )
            .join(HomeTeam, Game.home_team_id == HomeTeam.id)
            .join(AwayTeam, Game.away_team_id == AwayTeam.id)
            .all()
        )
        game_home_away = {}
        for gid, home_abbr, away_abbr in game_rows:
            game_home_away[gid] = (home_abbr, away_abbr)
        _progress(f"  {len(game_home_away)} games mapped.")
        del game_rows

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
        _progress(f"Backfilling xG columns for {total} stints...")

        for idx, stint in enumerate(all_stints, 1):
            if idx % 500 == 0 or idx == total:
                _progress(f"  Stints: {idx}/{total} ({idx * 100 // total}%)")

            tot_i_xg = 0.0
            tot_oi_xgf = 0.0
            tot_oi_xga = 0.0

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
                            tot_oi_xgf += evt_xg
                            if evt_pid == stint.player_id:
                                tot_i_xg += evt_xg
                        else:
                            tot_oi_xga += evt_xg

            stint.tot_i_xg = round(tot_i_xg, 3)
            stint.tot_oi_xgf = round(tot_oi_xgf, 3)
            stint.tot_oi_xga = round(tot_oi_xga, 3)

            # Even strength: both teams have equal skaters
            is_even = (
                stint.n_home_skaters is not None
                and stint.n_away_skaters is not None
                and stint.n_home_skaters == stint.n_away_skaters
            )
            stint.es_i_xg = stint.tot_i_xg if is_even else 0.0
            stint.es_oi_xgf = stint.tot_oi_xgf if is_even else 0.0
            stint.es_oi_xga = stint.tot_oi_xga if is_even else 0.0

            # 5v5 only
            is_5v5 = is_even and stint.n_home_skaters == 5
            stint.ev5_i_xg = stint.tot_i_xg if is_5v5 else 0.0
            stint.ev5_oi_xgf = stint.tot_oi_xgf if is_5v5 else 0.0
            stint.ev5_oi_xga = stint.tot_oi_xga if is_5v5 else 0.0

            # PP/PK
            home_away = game_home_away.get(stint.game_id)
            is_pp = False
            is_pk = False
            if (
                stint.n_home_skaters is not None
                and stint.n_away_skaters is not None
                and home_away
                and stint.team_abbr
            ):
                is_home = stint.team_abbr == home_away[0]
                player_sk = stint.n_home_skaters if is_home else stint.n_away_skaters
                opp_sk = stint.n_away_skaters if is_home else stint.n_home_skaters
                is_pp = player_sk > opp_sk
                is_pk = player_sk < opp_sk

            stint.pp_i_xg = stint.tot_i_xg if is_pp else 0.0
            stint.pp_oi_xgf = stint.tot_oi_xgf if is_pp else 0.0
            stint.pp_oi_xga = stint.tot_oi_xga if is_pp else 0.0

            stint.pk_i_xg = stint.tot_i_xg if is_pk else 0.0
            stint.pk_oi_xgf = stint.tot_oi_xgf if is_pk else 0.0
            stint.pk_oi_xga = stint.tot_oi_xga if is_pk else 0.0

        db.session.commit()
        _progress("Backfill complete.")


if __name__ == "__main__":
    backfill()
