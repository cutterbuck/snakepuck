"""Convert period_time columns from String to Float without re-seeding.

Alters the column types in-place using PostgreSQL USING clause.

Usage:
    python -m scripts.migrate_period_time_to_float
"""

from sqlalchemy import text

from app import create_app
from app.extensions import db


def migrate():
    app = create_app()
    with app.app_context():
        db.session.execute(
            text(
                "ALTER TABLE events "
                "ALTER COLUMN period_time TYPE FLOAT USING period_time::FLOAT"
            )
        )
        db.session.execute(
            text(
                "ALTER TABLE stints "
                "ALTER COLUMN period_time_start TYPE FLOAT "
                "USING period_time_start::FLOAT"
            )
        )
        db.session.execute(
            text(
                "ALTER TABLE stints "
                "ALTER COLUMN period_time_end TYPE FLOAT "
                "USING period_time_end::FLOAT"
            )
        )
        db.session.commit()
        print("Migrated period_time columns to FLOAT.")


if __name__ == "__main__":
    migrate()
