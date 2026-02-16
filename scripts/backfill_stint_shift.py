"""Backfill the shift column on stints without re-seeding.

Groups consecutive stints (where one's end time equals the next's start time)
for each player/game and assigns sequential shift numbers.

Usage:
    python -m scripts.backfill_stint_shift
"""

from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.models import Player, Stint


def backfill():
    app = create_app()
    with app.app_context():
        # Add the column if it doesn't already exist
        db.session.execute(
            text("ALTER TABLE stints ADD COLUMN IF NOT EXISTS shift INTEGER")
        )
        db.session.commit()

        # Get distinct player/game pairs, excluding goalies
        pairs = (
            db.session.query(Stint.player_id, Stint.game_id)
            .join(Player, Player.playerId == Stint.player_id)
            .filter(Player.position != "G")
            .distinct()
            .all()
        )

        # Clear shift for goalies
        goalie_ids = [p.playerId for p in Player.query.filter_by(position="G").all()]
        if goalie_ids:
            Stint.query.filter(Stint.player_id.in_(goalie_ids)).update(
                {Stint.shift: None}, synchronize_session=False
            )
            print(f"Cleared shift values for {len(goalie_ids)} goalies")

        total_pairs = len(pairs)
        updated = 0
        for i, (player_id, game_id) in enumerate(pairs):
            stints = (
                Stint.query.filter_by(player_id=player_id, game_id=game_id)
                .order_by(Stint.game_stint)
                .all()
            )
            if not stints:
                continue

            shift_num = 1
            stints[0].shift = shift_num

            for j in range(1, len(stints)):
                prev = stints[j - 1]
                curr = stints[j]
                if (
                    prev.period_time_end is not None
                    and curr.period_time_start is not None
                    and prev.period_time_end == curr.period_time_start
                ):
                    curr.shift = shift_num
                else:
                    shift_num += 1
                    curr.shift = shift_num

            updated += len(stints)

            if (i + 1) % 50 == 0 or (i + 1) == total_pairs:
                print(
                    f"  Processed {i + 1}/{total_pairs} player/game pairs ({updated} stints)"
                )

        db.session.commit()

        count = db.session.execute(
            text("SELECT COUNT(*) FROM stints WHERE shift IS NOT NULL")
        ).scalar()
        print(
            f"Done! Backfilled shift for {count} stint rows ({total_pairs} player/game pairs, goalies excluded)."
        )


if __name__ == "__main__":
    backfill()
