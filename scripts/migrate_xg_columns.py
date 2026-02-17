"""Rename xg -> i_xg and add oi_xgf, oi_xga, xg_percentage columns.

Skips steps that have already been applied.

Usage:
    python -m scripts.migrate_xg_columns
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


def migrate():
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()
        trans = conn.begin()
        try:
            for table in ["player_stats", "player_game_stats"]:
                # Rename xg -> i_xg (only if xg still exists)
                if _column_exists(conn, table, "xg") and not _column_exists(
                    conn, table, "i_xg"
                ):
                    conn.execute(text(f"ALTER TABLE {table} RENAME COLUMN xg TO i_xg"))
                    print(f"  {table}: renamed xg -> i_xg")
                elif _column_exists(conn, table, "i_xg"):
                    print(f"  {table}: i_xg already exists, skipping rename")

                # Add oi_xgf
                if not _column_exists(conn, table, "oi_xgf"):
                    conn.execute(
                        text(
                            f"ALTER TABLE {table} ADD COLUMN oi_xgf FLOAT NOT NULL DEFAULT 0.0"
                        )
                    )
                    print(f"  {table}: added oi_xgf")
                else:
                    print(f"  {table}: oi_xgf already exists, skipping")

                # Add oi_xga
                if not _column_exists(conn, table, "oi_xga"):
                    conn.execute(
                        text(
                            f"ALTER TABLE {table} ADD COLUMN oi_xga FLOAT NOT NULL DEFAULT 0.0"
                        )
                    )
                    print(f"  {table}: added oi_xga")
                else:
                    print(f"  {table}: oi_xga already exists, skipping")

            # Add xg_percentage (player_stats only)
            if not _column_exists(conn, "player_stats", "xg_percentage"):
                conn.execute(
                    text("ALTER TABLE player_stats ADD COLUMN xg_percentage FLOAT")
                )
                print("  player_stats: added xg_percentage")
            else:
                print("  player_stats: xg_percentage already exists, skipping")

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
