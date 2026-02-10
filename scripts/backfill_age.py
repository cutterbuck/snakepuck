"""Backfill the age column on player_stats without re-seeding.

Adds the column if it doesn't exist, then computes age as:
    (most recent game date) - player.birthDate

Usage:
    python -m scripts.backfill_age
"""

from sqlalchemy import text

from app import create_app
from app.extensions import db


def backfill():
    app = create_app()
    with app.app_context():
        # Add the column if it doesn't already exist
        db.session.execute(
            text("ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS age INTEGER")
        )
        db.session.commit()

        # Compute age = most_recent_game_date - birthDate for each player
        db.session.execute(
            text("""
            UPDATE player_stats ps
            SET age = EXTRACT(YEAR FROM AGE(
                (SELECT MAX(date) FROM games),
                p."birthDate"
            ))::INTEGER
            FROM players p
            WHERE ps.player_id = p."playerId"
              AND p."birthDate" IS NOT NULL
        """)
        )
        db.session.commit()

        count = db.session.execute(
            text("SELECT COUNT(*) FROM player_stats WHERE age IS NOT NULL")
        ).scalar()
        print(f"Backfilled age for {count} player_stats rows.")


if __name__ == "__main__":
    backfill()
