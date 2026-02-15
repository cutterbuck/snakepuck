"""Backfill Team.source_team_id from stints data without re-seeding.

Matches stints.team_abbr to teams.abbrev to populate teams.source_team_id.
Also converts the column type to VARCHAR(36) if needed.

Usage:
    python -m scripts.backfill_team_source_id
"""

from sqlalchemy import text

from app import create_app
from app.extensions import db


def backfill():
    app = create_app()
    with app.app_context():
        # Ensure column type is VARCHAR(36)
        db.session.execute(
            text(
                "ALTER TABLE teams "
                "ALTER COLUMN source_team_id TYPE VARCHAR(36) "
                "USING source_team_id::VARCHAR(36)"
            )
        )
        db.session.commit()

        # Populate source_team_id by matching team_abbr from stints
        db.session.execute(
            text("""
                UPDATE teams t
                SET source_team_id = sub.source_team_id
                FROM (
                    SELECT DISTINCT team_abbr, source_team_id
                    FROM stints
                    WHERE team_abbr IS NOT NULL
                      AND source_team_id IS NOT NULL
                ) sub
                WHERE t.abbrev = sub.team_abbr
                  AND t.source_team_id IS NULL
            """)
        )
        db.session.commit()

        updated = db.session.execute(
            text("SELECT COUNT(*) FROM teams WHERE source_team_id IS NOT NULL")
        ).scalar()
        total = db.session.execute(text("SELECT COUNT(*) FROM teams")).scalar()
        print(f"Backfilled source_team_id for {updated}/{total} teams.")

        missing = db.session.execute(
            text("SELECT abbrev, name FROM teams WHERE source_team_id IS NULL")
        ).fetchall()
        if missing:
            print(f"Teams without source_team_id: {[(r[0], r[1]) for r in missing]}")


if __name__ == "__main__":
    backfill()
