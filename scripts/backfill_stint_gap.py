"""Backfill situation-specific goals/assists/points on each Stint row.

Loads all goal/assist events into memory for fast in-memory filtering.
Builds a game_id -> (home_abbr, away_abbr) mapping for PP/PK determination.

Usage:
    python -m scripts.backfill_stint_gap
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

        # Load all goal/assist events into memory
        _progress("Loading goal/assist events into memory...")
        gap_events = (
            db.session.query(
                Event.game_id,
                Event.period,
                Event.period_time,
                Event.player_id,
                Event.event_type,
            )
            .filter(Event.event_type.in_(["goal", "assist"]))
            .all()
        )
        gap_by_game_period = defaultdict(list)
        for gid, period, pt, pid, etype in gap_events:
            gap_by_game_period[(gid, period)].append((pt, pid, etype))
        _progress(f"  Loaded {len(gap_events)} events.")
        del gap_events

        # Process all stints
        all_stints = Stint.query.all()
        total = len(all_stints)
        _progress(f"Backfilling GAP columns for {total} stints...")

        for idx, stint in enumerate(all_stints, 1):
            if idx % 500 == 0 or idx == total:
                _progress(f"  Stints: {idx}/{total} ({idx * 100 // total}%)")

            tot_goals = 0
            tot_assists = 0

            if (
                stint.period_time_start is not None
                and stint.period_time_end is not None
            ):
                for evt_time, evt_pid, evt_type in gap_by_game_period.get(
                    (stint.game_id, stint.period), []
                ):
                    if (
                        evt_time is not None
                        and evt_pid == stint.player_id
                        and stint.period_time_start <= evt_time < stint.period_time_end
                    ):
                        if evt_type == "goal":
                            tot_goals += 1
                        elif evt_type == "assist":
                            tot_assists += 1

            tot_points = tot_goals + tot_assists
            stint.tot_goals = tot_goals
            stint.tot_assists = tot_assists
            stint.tot_points = tot_points

            # Situation flags
            n_home = stint.n_home_skaters
            n_away = stint.n_away_skaters
            has_skaters = n_home is not None and n_away is not None

            is_even = has_skaters and n_home == n_away
            is_5v5 = is_even and n_home == 5

            # PP/PK: determine player's team skater advantage
            home_away = game_home_away.get(stint.game_id)
            is_pp = False
            is_pk = False
            if has_skaters and home_away and stint.team_abbr:
                is_home = stint.team_abbr == home_away[0]
                player_sk = n_home if is_home else n_away
                opp_sk = n_away if is_home else n_home
                is_pp = player_sk > opp_sk
                is_pk = player_sk < opp_sk

            stint.es_goals = tot_goals if is_even else 0
            stint.es_assists = tot_assists if is_even else 0
            stint.es_points = tot_points if is_even else 0

            stint.ev5_goals = tot_goals if is_5v5 else 0
            stint.ev5_assists = tot_assists if is_5v5 else 0
            stint.ev5_points = tot_points if is_5v5 else 0

            stint.pp_goals = tot_goals if is_pp else 0
            stint.pp_assists = tot_assists if is_pp else 0
            stint.pp_points = tot_points if is_pp else 0

            stint.pk_goals = tot_goals if is_pk else 0
            stint.pk_assists = tot_assists if is_pk else 0
            stint.pk_points = tot_points if is_pk else 0

        db.session.commit()
        _progress("Backfill complete.")


if __name__ == "__main__":
    backfill()
