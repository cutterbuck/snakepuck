"""Rename i_xg/oi_xgf/oi_xga to tot_ prefix and add es_/ev5_ situation columns.

Skips steps that have already been applied.

Usage:
    python -m scripts.migrate_xg_situations
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


def _add_col(conn, table, col, col_type="FLOAT"):
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
            # --- Renames: i_xg -> tot_i_xg, etc. ---
            for table in ["stints", "player_stats", "player_game_stats"]:
                _rename_col(conn, table, "i_xg", "tot_i_xg")
                _rename_col(conn, table, "oi_xgf", "tot_oi_xgf")
                _rename_col(conn, table, "oi_xga", "tot_oi_xga")

            # player_stats: rename xg_percentage -> tot_xg_pct
            _rename_col(conn, "player_stats", "xg_percentage", "tot_xg_pct")

            # --- Add es_ columns ---
            for table in ["stints", "player_stats", "player_game_stats"]:
                _add_col(conn, table, "es_i_xg")
                _add_col(conn, table, "es_oi_xgf")
                _add_col(conn, table, "es_oi_xga")

            _add_col(conn, "player_stats", "es_xg_pct")

            # --- Add ev5_ columns ---
            for table in ["stints", "player_stats", "player_game_stats"]:
                _add_col(conn, table, "ev5_i_xg")
                _add_col(conn, table, "ev5_oi_xgf")
                _add_col(conn, table, "ev5_oi_xga")

            _add_col(conn, "player_stats", "ev5_xg_pct")

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
