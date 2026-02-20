"""Add database indexes to speed up common queries.

Usage:
    python -m scripts.add_indexes
"""

from app import create_app
from app.extensions import db

INDEXES = [
    # events table
    ("ix_events_game_id", "events", "game_id"),
    ("ix_events_player_id", "events", "player_id"),
    ("ix_events_period", "events", "period"),
    ("ix_events_game_stint", "events", "game_stint"),
    # stints table
    ("ix_stints_game_id", "stints", "game_id"),
    ("ix_stints_player_id", "stints", "player_id"),
    ("ix_stints_game_stint", "stints", "game_stint"),
    ("ix_stints_shift", "stints", "shift"),
    # games table
    ("ix_games_game_id", "games", "game_id"),
    ("ix_games_date", "games", "date"),
    ("ix_games_home_team_id", "games", "home_team_id"),
    ("ix_games_away_team_id", "games", "away_team_id"),
    # players table
    ("ix_players_playerId", "players", '"playerId"'),
    # player_stats table
    ("ix_player_stats_player_id", "player_stats", "player_id"),
    ("ix_player_stats_team_id", "player_stats", "team_id"),
    ("ix_player_stats_season_id", "player_stats", "season_id"),
    # player_game_stats table
    ("ix_pgs_team_id", "player_game_stats", "team_id"),
    ("ix_pgs_season_id", "player_game_stats", "season_id"),
]

# Composite indexes for common join patterns
COMPOSITE_INDEXES = [
    ("ix_events_game_period_time", "events", "game_id, period, period_time"),
    ("ix_stints_player_game", "stints", "player_id, game_id"),
    ("ix_pgs_player_game", "player_game_stats", "player_id, game_id"),
]


def main():
    app = create_app()
    with app.app_context():
        for name, table, column in INDEXES:
            try:
                db.session.execute(
                    db.text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({column})")
                )
                print(f"Created index: {name}")
            except Exception as e:
                print(f"Skipped {name}: {e}")

        for name, table, columns in COMPOSITE_INDEXES:
            try:
                db.session.execute(
                    db.text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})")
                )
                print(f"Created composite index: {name}")
            except Exception as e:
                print(f"Skipped {name}: {e}")

        db.session.commit()
        print("Done.")


if __name__ == "__main__":
    main()
