"""Backfill situation-specific goals/assists/points for PlayerGameStats and PlayerStats.

Aggregates from pre-computed Stint columns.

Usage:
    python -m scripts.backfill_oi_gap
"""

import sys
from collections import defaultdict

from app import create_app
from app.extensions import db
from app.models import PlayerGameStats, PlayerStats, Stint

GAP_FIELDS = [
    "tot_goals",
    "tot_assists",
    "tot_points",
    "es_goals",
    "es_assists",
    "es_points",
    "ev5_goals",
    "ev5_assists",
    "ev5_points",
    "pp_goals",
    "pp_assists",
    "pp_points",
    "pk_goals",
    "pk_assists",
    "pk_points",
]


def _progress(msg):
    print(msg)
    sys.stdout.flush()


def backfill():
    app = create_app()
    with app.app_context():
        # Pre-load all stint GAP values into memory
        _progress("Loading stint GAP data into memory...")
        all_stints = db.session.query(
            Stint.player_id,
            Stint.game_id,
            *[getattr(Stint, f) for f in GAP_FIELDS],
        ).all()
        # Aggregate by (player_id, game_id)
        stint_agg = defaultdict(lambda: {f: 0 for f in GAP_FIELDS})
        for row in all_stints:
            key = (row.player_id, row.game_id)
            for f in GAP_FIELDS:
                stint_agg[key][f] += getattr(row, f) or 0
        _progress(
            f"  Loaded {len(all_stints)} stints, {len(stint_agg)} player-game pairs."
        )
        del all_stints

        # --- PlayerGameStats ---
        all_pgs = PlayerGameStats.query.all()
        total = len(all_pgs)
        _progress(f"Backfilling GAP columns for {total} PlayerGameStats records...")
        for idx, pgs in enumerate(all_pgs, 1):
            if idx % 100 == 0 or idx == total:
                _progress(f"  PlayerGameStats: {idx}/{total} ({idx * 100 // total}%)")

            agg = stint_agg.get((pgs.player_id, pgs.game_id))
            if agg:
                for f in GAP_FIELDS:
                    setattr(pgs, f, agg[f])
            else:
                for f in GAP_FIELDS:
                    setattr(pgs, f, 0)

            # Recompute shooting_pct based on tot_goals
            total_shots = pgs.shots or 0
            pgs.shooting_pct = (
                round(pgs.tot_goals / total_shots, 3) if total_shots > 0 else None
            )

        db.session.commit()
        _progress("Backfilled PlayerGameStats.")

        # --- PlayerStats (aggregate from PlayerGameStats) ---
        _progress("Aggregating GAP columns for PlayerStats...")
        agg_results = (
            db.session.query(
                PlayerGameStats.player_id,
                PlayerGameStats.team_id,
                PlayerGameStats.season_id,
                *[
                    db.func.coalesce(db.func.sum(getattr(PlayerGameStats, f)), 0)
                    for f in GAP_FIELDS
                ],
            )
            .group_by(
                PlayerGameStats.player_id,
                PlayerGameStats.team_id,
                PlayerGameStats.season_id,
            )
            .all()
        )
        agg_map = {}
        for row in agg_results:
            key = (row[0], row[1], row[2])
            agg_map[key] = {f: int(row[3 + i]) for i, f in enumerate(GAP_FIELDS)}

        all_ps = PlayerStats.query.all()
        total = len(all_ps)
        for idx, ps in enumerate(all_ps, 1):
            if idx % 100 == 0 or idx == total:
                _progress(f"  PlayerStats: {idx}/{total} ({idx * 100 // total}%)")

            agg = agg_map.get((ps.player_id, ps.team_id, ps.season_id), {})
            for f in GAP_FIELDS:
                setattr(ps, f, agg.get(f, 0))

            # Recompute shooting_pct based on tot_goals
            total_shots = ps.shots or 0
            ps.shooting_pct = (
                round(ps.tot_goals / total_shots, 3) if total_shots > 0 else None
            )

        db.session.commit()
        _progress("Backfilled PlayerStats.")
        _progress("Backfill complete.")


if __name__ == "__main__":
    backfill()
