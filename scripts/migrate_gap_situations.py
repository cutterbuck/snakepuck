"""Rename goals/assists/points to tot_ prefix and add situation-specific columns.

Adds es_, ev5_, pp_, pk_ GAP columns plus pp_/pk_ xG columns.
Skips steps that have already been applied.

Usage:
    python -m scripts.migrate_gap_situations
"""

from sqlalchemy import text

from app import create_app
from app.extensions import db


def _column_exists(conn, table, column):
    result = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.fetchone() is not None


def _rename_col(conn, table, old, new):
    if _column_exists(conn, table, old) and not _column_exists(conn, table, new):
        conn.execute(text(f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}"))
        print(f"  {table}: renamed {old} -> {new}")
    elif _column_exists(conn, table, new):
        print(f"  {table}: {new} already exists, skipping rename")


def _add_col(conn, table, col, col_type="INTEGER"):
    if not _column_exists(conn, table, col):
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
        print(f"  {table}: added {col}")
    else:
        print(f"  {table}: {col} already exists, skipping")


def migrate():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()
        trans = conn.begin()
        try:
            # --- Renames: goals -> tot_goals, etc. on PGS and PlayerStats ---
            for table in ["player_game_stats", "player_stats"]:
                _rename_col(conn, table, "goals", "tot_goals")
                _rename_col(conn, table, "assists", "tot_assists")
                _rename_col(conn, table, "points", "tot_points")

            # --- Add GAP situation columns to all 3 tables ---
            gap_prefixes = ["tot", "es", "ev5", "pp", "pk"]
            gap_metrics = ["goals", "assists", "points"]
            for table in ["stints", "player_game_stats", "player_stats"]:
                for prefix in gap_prefixes:
                    for metric in gap_metrics:
                        _add_col(conn, table, f"{prefix}_{metric}", "INTEGER")

            # --- Add pp_/pk_ xG columns ---
            xg_metrics = ["i_xg", "oi_xgf", "oi_xga"]
            for table in ["stints", "player_game_stats", "player_stats"]:
                for prefix in ["pp", "pk"]:
                    for metric in xg_metrics:
                        _add_col(conn, table, f"{prefix}_{metric}", "FLOAT")

            # pp_/pk_ xg_pct on player_stats only
            _add_col(conn, "player_stats", "pp_xg_pct", "FLOAT")
            _add_col(conn, "player_stats", "pk_xg_pct", "FLOAT")

            trans.commit()
            print("Migration complete.")
        except Exception as e:
            trans.rollback()
            print(f"Migration failed: {e}")
            raise
        finally:
            conn.close()


if __name__ == "__main__":
    migrate()
