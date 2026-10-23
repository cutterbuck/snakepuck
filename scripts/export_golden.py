"""Export "golden" snapshots of the derived stats tables.

These are the reference numbers the dbt rebuild (migration Phase 3) must
reproduce. Postgres surrogate ids (team_id, season_id, division_id) are
swapped for natural keys so the snapshots can be joined from BigQuery.

Usage:
    python -m scripts.export_golden [output_dir]   # default: golden/
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from app.config import Config

# Natural-key columns substituted for surrogate ids, in front of each table
TEAM_KEYS = "t.source_team_id, t.abbrev AS team_abbr, s.name AS season"

QUERIES = {
    "player_stats": (
        f"""
        SELECT x.player_id, {TEAM_KEYS}, x.*
        FROM player_stats x
        JOIN teams t ON t.id = x.team_id
        JOIN seasons s ON s.id = x.season_id
        """,
        ["player_id", "source_team_id", "season"],
    ),
    "player_game_stats": (
        f"""
        SELECT x.player_id, x.game_id, {TEAM_KEYS}, x.*
        FROM player_game_stats x
        JOIN teams t ON t.id = x.team_id
        JOIN seasons s ON s.id = x.season_id
        """,
        ["player_id", "game_id", "source_team_id"],
    ),
    "team_stats": (
        f"""
        SELECT {TEAM_KEYS}, d.name AS division, x.*
        FROM team_stats x
        JOIN teams t ON t.id = x.team_id
        JOIN seasons s ON s.id = x.season_id
        LEFT JOIN divisions d ON d.id = x.division_id
        """,
        ["source_team_id", "season"],
    ),
    "stints": (
        "SELECT x.* FROM stints x",
        ["game_id", "player_id", "period", "period_time_start", "game_stint"],
    ),
}

SURROGATE_COLUMNS = ["id", "team_id", "season_id", "division_id"]


def _git_commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return None


def export(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "tables": {},
    }

    for name, (sql, sort_keys) in QUERIES.items():
        df = pd.read_sql(sql, engine)
        # x.* repeats player_id/game_id; keep the first copy of each column
        df = df.loc[:, ~df.columns.duplicated()]
        df = df.drop(columns=[c for c in SURROGATE_COLUMNS if c in df.columns])
        df = df.sort_values(sort_keys, kind="stable").reset_index(drop=True)
        path = out_dir / f"{name}.parquet"
        df.to_parquet(path, index=False)

        numeric = df.select_dtypes("number")
        manifest["tables"][name] = {
            "rows": len(df),
            "key": sort_keys,
            "duplicate_keys": int(df.duplicated(sort_keys).sum()),
            # Column sums: a quick fingerprint for reconciliation
            "column_sums": {c: round(float(numeric[c].sum()), 6) for c in numeric},
        }
        print(
            f"{name}: {len(df):,} rows -> {path} ({path.stat().st_size / 1e6:.1f} MB)"
        )

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"manifest -> {out_dir / 'manifest.json'}")


if __name__ == "__main__":
    export(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("golden"))
