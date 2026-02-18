"""Backfill situation-specific shots/faceoffs/blocks/checks/TOI on each Stint row.

Loads all relevant events into memory for fast in-memory filtering.
Builds a game_id -> (home_abbr, away_abbr) mapping for PP/PK determination.

Usage:
    python -m scripts.backfill_stint_stats
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

        # Load shot/goal events (shots on net = shot + goal)
        _progress("Loading shot/goal events into memory...")
        shot_events = (
            db.session.query(
                Event.game_id,
                Event.period,
                Event.period_time,
                Event.player_id,
            )
            .filter(Event.event_type.in_(["shot", "goal"]))
            .all()
        )
        shots_by_game_period = defaultdict(list)
        for gid, period, pt, pid in shot_events:
            shots_by_game_period[(gid, period)].append((pt, pid))
        _progress(f"  Loaded {len(shot_events)} shot/goal events.")
        del shot_events

        # Load faceoff events
        _progress("Loading faceoff events into memory...")
        faceoff_events = (
            db.session.query(
                Event.game_id,
                Event.period,
                Event.period_time,
                Event.player_id,
                Event.outcome,
            )
            .filter(Event.event_type == "faceoff")
            .all()
        )
        faceoffs_by_game_period = defaultdict(list)
        for gid, period, pt, pid, outcome in faceoff_events:
            faceoffs_by_game_period[(gid, period)].append((pt, pid, outcome))
        _progress(f"  Loaded {len(faceoff_events)} faceoff events.")
        del faceoff_events

        # Load block events
        _progress("Loading block events into memory...")
        block_events = (
            db.session.query(
                Event.game_id,
                Event.period,
                Event.period_time,
                Event.player_id,
            )
            .filter(Event.event_type == "block")
            .all()
        )
        blocks_by_game_period = defaultdict(list)
        for gid, period, pt, pid in block_events:
            blocks_by_game_period[(gid, period)].append((pt, pid))
        _progress(f"  Loaded {len(block_events)} block events.")
        del block_events

        # Load check events
        _progress("Loading check events into memory...")
        check_events = (
            db.session.query(
                Event.game_id,
                Event.period,
                Event.period_time,
                Event.player_id,
            )
            .filter(Event.event_type == "check")
            .all()
        )
        checks_by_game_period = defaultdict(list)
        for gid, period, pt, pid in check_events:
            checks_by_game_period[(gid, period)].append((pt, pid))
        _progress(f"  Loaded {len(check_events)} check events.")
        del check_events

        # Process all stints
        all_stints = Stint.query.all()
        total = len(all_stints)
        _progress(f"Backfilling stat/TOI columns for {total} stints...")

        for idx, stint in enumerate(all_stints, 1):
            if idx % 500 == 0 or idx == total:
                _progress(f"  Stints: {idx}/{total} ({idx * 100 // total}%)")

            tot_shots = 0
            tot_faceoffs_won = 0
            tot_faceoffs_lost = 0
            tot_blocks = 0
            tot_checks = 0

            has_times = (
                stint.period_time_start is not None
                and stint.period_time_end is not None
            )

            if has_times:
                # Shots
                for evt_time, evt_pid in shots_by_game_period.get(
                    (stint.game_id, stint.period), []
                ):
                    if (
                        evt_time is not None
                        and evt_pid == stint.player_id
                        and stint.period_time_start <= evt_time < stint.period_time_end
                    ):
                        tot_shots += 1

                # Faceoffs
                for evt_time, evt_pid, outcome in faceoffs_by_game_period.get(
                    (stint.game_id, stint.period), []
                ):
                    if (
                        evt_time is not None
                        and evt_pid == stint.player_id
                        and stint.period_time_start <= evt_time < stint.period_time_end
                    ):
                        if outcome == "successful":
                            tot_faceoffs_won += 1
                        elif outcome == "failed":
                            tot_faceoffs_lost += 1

                # Blocks
                for evt_time, evt_pid in blocks_by_game_period.get(
                    (stint.game_id, stint.period), []
                ):
                    if (
                        evt_time is not None
                        and evt_pid == stint.player_id
                        and stint.period_time_start <= evt_time < stint.period_time_end
                    ):
                        tot_blocks += 1

                # Checks
                for evt_time, evt_pid in checks_by_game_period.get(
                    (stint.game_id, stint.period), []
                ):
                    if (
                        evt_time is not None
                        and evt_pid == stint.player_id
                        and stint.period_time_start <= evt_time < stint.period_time_end
                    ):
                        tot_checks += 1

            # Set totals
            stint.tot_shots = tot_shots
            stint.tot_faceoffs_won = tot_faceoffs_won
            stint.tot_faceoffs_lost = tot_faceoffs_lost
            stint.tot_blocks = tot_blocks
            stint.tot_checks = tot_checks

            # TOI
            duration = (
                (stint.period_time_end - stint.period_time_start) if has_times else 0.0
            )
            stint.tot_toi = duration

            # Situation flags
            n_home = stint.n_home_skaters
            n_away = stint.n_away_skaters
            has_skaters = n_home is not None and n_away is not None

            is_even = has_skaters and n_home == n_away
            is_5v5 = is_even and n_home == 5

            home_away = game_home_away.get(stint.game_id)
            is_pp = False
            is_pk = False
            if has_skaters and home_away and stint.team_abbr:
                is_home = stint.team_abbr == home_away[0]
                player_sk = n_home if is_home else n_away
                opp_sk = n_away if is_home else n_home
                is_pp = player_sk > opp_sk
                is_pk = player_sk < opp_sk

            # Situation splits for stats
            stint.es_shots = tot_shots if is_even else 0
            stint.ev5_shots = tot_shots if is_5v5 else 0
            stint.pp_shots = tot_shots if is_pp else 0
            stint.pk_shots = tot_shots if is_pk else 0

            stint.es_faceoffs_won = tot_faceoffs_won if is_even else 0
            stint.ev5_faceoffs_won = tot_faceoffs_won if is_5v5 else 0
            stint.pp_faceoffs_won = tot_faceoffs_won if is_pp else 0
            stint.pk_faceoffs_won = tot_faceoffs_won if is_pk else 0

            stint.es_faceoffs_lost = tot_faceoffs_lost if is_even else 0
            stint.ev5_faceoffs_lost = tot_faceoffs_lost if is_5v5 else 0
            stint.pp_faceoffs_lost = tot_faceoffs_lost if is_pp else 0
            stint.pk_faceoffs_lost = tot_faceoffs_lost if is_pk else 0

            stint.es_blocks = tot_blocks if is_even else 0
            stint.ev5_blocks = tot_blocks if is_5v5 else 0
            stint.pp_blocks = tot_blocks if is_pp else 0
            stint.pk_blocks = tot_blocks if is_pk else 0

            stint.es_checks = tot_checks if is_even else 0
            stint.ev5_checks = tot_checks if is_5v5 else 0
            stint.pp_checks = tot_checks if is_pp else 0
            stint.pk_checks = tot_checks if is_pk else 0

            # TOI splits
            stint.es_toi = duration if is_even else 0.0
            stint.ev5_toi = duration if is_5v5 else 0.0
            stint.pp_toi = duration if is_pp else 0.0
            stint.pk_toi = duration if is_pk else 0.0

        db.session.commit()
        _progress("Backfill complete.")


if __name__ == "__main__":
    backfill()
