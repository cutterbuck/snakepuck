"""Backfill the tracking table without re-seeding.

Creates the table if it doesn't exist, then loads tracking.parquet
and inserts rows in batches of 5000.

Usage:
    python -m scripts.backfill_tracking
"""

import os

import pandas as pd

from app import create_app
from app.extensions import db
from app.models import Tracking

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def backfill():
    app = create_app()
    with app.app_context():
        Tracking.__table__.create(db.engine, checkfirst=True)

        existing = Tracking.query.count()
        if existing > 0:
            print(f"Tracking table already has {existing} rows. Skipping.")
            return

        print("Loading tracking.parquet...")
        df = pd.read_parquet(os.path.join(DATA_DIR, "tracking.parquet"))
        print(f"Loaded {len(df)} rows. Inserting...")

        records = []
        for i, (_, row) in enumerate(df.iterrows()):
            records.append(
                Tracking(
                    game_id=row["game_id"],
                    sl_event_id=str(row["sl_event_id"])
                    if pd.notna(row.get("sl_event_id"))
                    else None,
                    team_id=str(row["team_id"])
                    if pd.notna(row.get("team_id"))
                    else None,
                    team_name=row["team_name"]
                    if pd.notna(row.get("team_name"))
                    else None,
                    player_id=str(row["player_id"])
                    if pd.notna(row.get("player_id"))
                    else None,
                    player_name=row["player_name"]
                    if pd.notna(row.get("player_name"))
                    else None,
                    tracking_x=float(row["tracking_x"])
                    if pd.notna(row.get("tracking_x"))
                    else None,
                    tracking_y=float(row["tracking_y"])
                    if pd.notna(row.get("tracking_y"))
                    else None,
                    tracking_vel_x=float(row["tracking_vel_x"])
                    if pd.notna(row.get("tracking_vel_x"))
                    else None,
                    tracking_vel_y=float(row["tracking_vel_y"])
                    if pd.notna(row.get("tracking_vel_y"))
                    else None,
                )
            )
            if len(records) >= 5000:
                db.session.bulk_save_objects(records)
                db.session.flush()
                print(f"  Inserted {i + 1} rows...")
                records = []

        if records:
            db.session.bulk_save_objects(records)
            db.session.flush()

        db.session.commit()
        total = Tracking.query.count()
        print(f"Done. Inserted {total} tracking rows.")


if __name__ == "__main__":
    backfill()
