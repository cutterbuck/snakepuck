"""Rename shots/faceoffs/blocks/checks to tot_ prefix and add situation columns.

Adds es_, ev5_, pp_, pk_ columns for shots, shooting_pct, faceoffs_won,
faceoffs_lost, faceoff_pct, blocks, checks.
Adds TOI columns to stints/player_game_stats and ATOI to player_stats.
Skips steps that have already been applied.

Usage:
    python -m scripts.migrate_stat_situations
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
            # --- Renames on PGS and PlayerStats ---
            for table in ["player_game_stats", "player_stats"]:
                _rename_col(conn, table, "shots", "tot_shots")
                _rename_col(conn, table, "shooting_pct", "tot_shooting_pct")
                _rename_col(conn, table, "faceoffs_won", "tot_faceoffs_won")
                _rename_col(conn, table, "faceoffs_lost", "tot_faceoffs_lost")
                _rename_col(conn, table, "faceoff_pct", "tot_faceoff_pct")
                _rename_col(conn, table, "blocks", "tot_blocks")
                _rename_col(conn, table, "checks", "tot_checks")

            # --- Add situation count columns to all 3 tables ---
            prefixes = ["tot", "es", "ev5", "pp", "pk"]
            count_stats = ["shots", "faceoffs_won", "faceoffs_lost", "blocks", "checks"]
            for table in ["stints", "player_game_stats", "player_stats"]:
                for prefix in prefixes:
                    for stat in count_stats:
                        _add_col(conn, table, f"{prefix}_{stat}", "INTEGER")

            # --- Add situation percentage columns to PGS and PlayerStats only ---
            pct_stats = ["shooting_pct", "faceoff_pct"]
            for table in ["player_game_stats", "player_stats"]:
                for prefix in prefixes:
                    for stat in pct_stats:
                        _add_col(conn, table, f"{prefix}_{stat}", "FLOAT")

            # --- Add TOI columns to stints and PGS ---
            for table in ["stints", "player_game_stats"]:
                for prefix in prefixes:
                    _add_col(conn, table, f"{prefix}_toi", "FLOAT")

            # --- Add ATOI columns to PlayerStats ---
            for prefix in prefixes:
                _add_col(conn, "player_stats", f"{prefix}_atoi", "FLOAT")

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
