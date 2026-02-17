"""Backfill tot_/es_/ev5_/pp_/pk_ xG columns for PlayerGameStats and PlayerStats.

Loads all stints into memory for fast aggregation.

Usage:
    python -m scripts.backfill_oi_xg
"""

import sys
from collections import defaultdict

from app import create_app
from app.extensions import db
from app.models import PlayerGameStats, PlayerStats, Stint


def _progress(msg):
    print(msg)
    sys.stdout.flush()


XG_FIELDS = [
    "tot_i_xg",
    "tot_oi_xgf",
    "tot_oi_xga",
    "es_i_xg",
    "es_oi_xgf",
    "es_oi_xga",
    "ev5_i_xg",
    "ev5_oi_xgf",
    "ev5_oi_xga",
    "pp_i_xg",
    "pp_oi_xgf",
    "pp_oi_xga",
    "pk_i_xg",
    "pk_oi_xgf",
    "pk_oi_xga",
]


def backfill():
    app = create_app()
    with app.app_context():
        # Pre-load all stint xG values into memory
        _progress("Loading stint xG data into memory...")
        all_stints = db.session.query(
            Stint.player_id,
            Stint.game_id,
            *[getattr(Stint, f) for f in XG_FIELDS],
        ).all()
        # Aggregate by (player_id, game_id)
        stint_agg = defaultdict(lambda: {f: 0.0 for f in XG_FIELDS})
        for row in all_stints:
            key = (row.player_id, row.game_id)
            for f in XG_FIELDS:
                stint_agg[key][f] += getattr(row, f) or 0.0
        _progress(
            f"  Loaded {len(all_stints)} stints, {len(stint_agg)} player-game pairs."
        )
        del all_stints

        # --- PlayerGameStats ---
        all_pgs = PlayerGameStats.query.all()
        total = len(all_pgs)
        _progress(f"Backfilling xG columns for {total} PlayerGameStats records...")
        for idx, pgs in enumerate(all_pgs, 1):
            if idx % 100 == 0 or idx == total:
                _progress(f"  PlayerGameStats: {idx}/{total} ({idx * 100 // total}%)")

            agg = stint_agg.get((pgs.player_id, pgs.game_id))
            if agg:
                for f in XG_FIELDS:
                    setattr(pgs, f, round(agg[f], 3))
            else:
                for f in XG_FIELDS:
                    setattr(pgs, f, 0.0)

        db.session.commit()
        _progress("Backfilled PlayerGameStats.")

        # --- PlayerStats (aggregate from PlayerGameStats) ---
        _progress("Aggregating xG columns for PlayerStats...")
        # Single query to sum all xG fields grouped by player+team+season
        agg_results = (
            db.session.query(
                PlayerGameStats.player_id,
                PlayerGameStats.team_id,
                PlayerGameStats.season_id,
                *[
                    db.func.coalesce(db.func.sum(getattr(PlayerGameStats, f)), 0.0)
                    for f in XG_FIELDS
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
            agg_map[key] = {f: float(row[3 + i]) for i, f in enumerate(XG_FIELDS)}

        all_ps = PlayerStats.query.all()
        total = len(all_ps)
        for idx, ps in enumerate(all_ps, 1):
            if idx % 100 == 0 or idx == total:
                _progress(f"  PlayerStats: {idx}/{total} ({idx * 100 // total}%)")

            agg = agg_map.get((ps.player_id, ps.team_id, ps.season_id), {})
            for f in XG_FIELDS:
                setattr(ps, f, round(agg.get(f, 0.0), 3))

            # Compute xg_pct for each situation
            for prefix in ["tot", "es", "ev5", "pp", "pk"]:
                xgf = getattr(ps, f"{prefix}_oi_xgf")
                xga = getattr(ps, f"{prefix}_oi_xga")
                total_xg = xgf + xga
                setattr(
                    ps,
                    f"{prefix}_xg_pct",
                    round(xgf / total_xg, 3) if total_xg > 0 else None,
                )

        db.session.commit()
        _progress("Backfilled PlayerStats.")
        _progress("Backfill complete.")


if __name__ == "__main__":
    backfill()
