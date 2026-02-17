"""Add i_xg, oi_xgf, oi_xga columns to stints table.

Skips columns that already exist.

Usage:
    python -m scripts.migrate_stint_xg
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
            for col in ["i_xg", "oi_xgf", "oi_xga"]:
                if not _column_exists(conn, "stints", col):
                    conn.execute(text(f"ALTER TABLE stints ADD COLUMN {col} FLOAT"))
                    print(f"  stints: added {col}")
                else:
                    print(f"  stints: {col} already exists, skipping")

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
