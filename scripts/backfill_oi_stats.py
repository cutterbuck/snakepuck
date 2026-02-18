"""Backfill situation-specific stats for PlayerGameStats and PlayerStats.

Aggregates shots/faceoffs/blocks/checks/TOI from pre-computed Stint columns.
Computes shooting_pct, faceoff_pct per situation, and ATOI for PlayerStats.

Usage:
    python -m scripts.backfill_oi_stats
"""

import sys
from collections import defaultdict

from app import create_app
from app.extensions import db
from app.models import PlayerGameStats, PlayerStats, Stint

COUNT_FIELDS = [
    "tot_shots",
    "es_shots",
    "ev5_shots",
    "pp_shots",
    "pk_shots",
    "tot_faceoffs_won",
    "es_faceoffs_won",
    "ev5_faceoffs_won",
    "pp_faceoffs_won",
    "pk_faceoffs_won",
    "tot_faceoffs_lost",
    "es_faceoffs_lost",
    "ev5_faceoffs_lost",
    "pp_faceoffs_lost",
    "pk_faceoffs_lost",
    "tot_blocks",
    "es_blocks",
    "ev5_blocks",
    "pp_blocks",
    "pk_blocks",
    "tot_checks",
    "es_checks",
    "ev5_checks",
    "pp_checks",
    "pk_checks",
]

TOI_FIELDS = [
    "tot_toi",
    "es_toi",
    "ev5_toi",
    "pp_toi",
    "pk_toi",
]

ALL_FIELDS = COUNT_FIELDS + TOI_FIELDS

PREFIXES = ["tot", "es", "ev5", "pp", "pk"]


def _progress(msg):
    print(msg)
    sys.stdout.flush()


def _compute_pcts(obj, prefix):
    """Compute shooting_pct and faceoff_pct for a given situation prefix."""
    shots = getattr(obj, f"{prefix}_shots") or 0
    goals = getattr(obj, f"{prefix}_goals") or 0
    setattr(
        obj,
        f"{prefix}_shooting_pct",
        round(goals / shots, 3) if shots > 0 else None,
    )

    fow = getattr(obj, f"{prefix}_faceoffs_won") or 0
    fol = getattr(obj, f"{prefix}_faceoffs_lost") or 0
    total_fo = fow + fol
    setattr(
        obj,
        f"{prefix}_faceoff_pct",
        round(fow / total_fo, 3) if total_fo > 0 else None,
    )


def backfill():
    app = create_app()
    with app.app_context():
        # Pre-load all stint stat values into memory
        _progress("Loading stint stat data into memory...")
        all_stints = db.session.query(
            Stint.player_id,
            Stint.game_id,
            *[getattr(Stint, f) for f in ALL_FIELDS],
        ).all()

        # Aggregate by (player_id, game_id)
        stint_agg = defaultdict(
            lambda: {f: 0.0 if f.endswith("_toi") else 0 for f in ALL_FIELDS}
        )
        for row in all_stints:
            key = (row.player_id, row.game_id)
            for f in ALL_FIELDS:
                stint_agg[key][f] += getattr(row, f) or 0
        _progress(
            f"  Loaded {len(all_stints)} stints, {len(stint_agg)} player-game pairs."
        )
        del all_stints

        # --- PlayerGameStats ---
        all_pgs = PlayerGameStats.query.all()
        total = len(all_pgs)
        _progress(f"Backfilling stat columns for {total} PlayerGameStats records...")

        for idx, pgs in enumerate(all_pgs, 1):
            if idx % 100 == 0 or idx == total:
                _progress(f"  PlayerGameStats: {idx}/{total} ({idx * 100 // total}%)")

            agg = stint_agg.get((pgs.player_id, pgs.game_id))
            if agg:
                for f in ALL_FIELDS:
                    setattr(pgs, f, agg[f])
            else:
                for f in ALL_FIELDS:
                    setattr(pgs, f, 0.0 if f.endswith("_toi") else 0)

            # Compute percentages per situation
            for prefix in PREFIXES:
                _compute_pcts(pgs, prefix)

        db.session.commit()
        _progress("Backfilled PlayerGameStats.")

        # --- PlayerStats (aggregate from PlayerGameStats) ---
        _progress("Aggregating stat columns for PlayerStats...")

        # Aggregate count fields
        agg_results = (
            db.session.query(
                PlayerGameStats.player_id,
                PlayerGameStats.team_id,
                PlayerGameStats.season_id,
                *[
                    db.func.coalesce(db.func.sum(getattr(PlayerGameStats, f)), 0)
                    for f in ALL_FIELDS
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
            agg_map[key] = {}
            for i, f in enumerate(ALL_FIELDS):
                if f.endswith("_toi"):
                    agg_map[key][f] = float(row[3 + i])
                else:
                    agg_map[key][f] = int(row[3 + i])

        all_ps = PlayerStats.query.all()
        total = len(all_ps)

        for idx, ps in enumerate(all_ps, 1):
            if idx % 100 == 0 or idx == total:
                _progress(f"  PlayerStats: {idx}/{total} ({idx * 100 // total}%)")

            agg = agg_map.get((ps.player_id, ps.team_id, ps.season_id), {})

            # Set count fields
            for f in COUNT_FIELDS:
                setattr(ps, f, agg.get(f, 0))

            # Compute percentages per situation
            for prefix in PREFIXES:
                _compute_pcts(ps, prefix)

            # Compute ATOI from summed TOI
            gp = ps.games_played or 0
            for prefix in PREFIXES:
                toi_field = f"{prefix}_toi"
                summed_toi = agg.get(toi_field, 0.0)
                setattr(
                    ps,
                    f"{prefix}_atoi",
                    round(summed_toi / gp, 1) if gp > 0 else None,
                )

        db.session.commit()
        _progress("Backfilled PlayerStats.")
        _progress("Backfill complete.")


if __name__ == "__main__":
    backfill()
