"""Seed the database from parquet files.

Usage:
    python -m scripts.seed_db
"""

import os

import pandas as pd

from app import create_app
from app.extensions import db
from app.models import Game, League, Organization, Player, Season, Team, User

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        # --- Leagues ---
        leagues = {}
        for league_name, league_abbrev in [
            ("National Hockey League", "NHL"),
            ("American Hockey League", "AHL"),
        ]:
            league_obj = League.query.filter_by(abbrev=league_abbrev).first()
            if not league_obj:
                league_obj = League(name=league_name, abbrev=league_abbrev)
                db.session.add(league_obj)
                db.session.flush()
                print(f"Created league: {league_name} ({league_abbrev})")
            leagues[league_abbrev] = league_obj

        ahl = leagues["AHL"]

        # --- Season ---
        season = Season.query.filter_by(name="2023-24").first()
        if not season:
            season = Season(name="2023-24", league="AHL")
            db.session.add(season)
            db.session.flush()
            print("Created season: 2023-24 AHL")

        # --- Organizations & Teams ---
        players_df = pd.read_parquet(os.path.join(DATA_DIR, "players.parquet"))
        games_df = pd.read_parquet(os.path.join(DATA_DIR, "games.parquet"))

        # Get unique team abbreviations from both parquets
        game_teams = set(games_df["home_team"].dropna().unique()) | set(
            games_df["away_team"].dropna().unique()
        )
        all_team_abbrs = sorted(game_teams)
        team_map = {}  # team abbreviation -> Team ORM object

        for abbr in all_team_abbrs:
            # Organization
            org = Organization.query.filter_by(abbreviation=abbr).first()
            if not org:
                org = Organization(name=abbr, abbreviation=abbr)
                db.session.add(org)
                db.session.flush()
                print(f"Created organization: {abbr}")

            # Team (season-specific)
            team_obj = Team.query.filter_by(
                organization_id=org.id, season_id=season.id
            ).first()
            if not team_obj:
                team_obj = Team(
                    organization_id=org.id,
                    season_id=season.id,
                    league_id=ahl.id,
                    name=abbr,
                    source_team_id=None,
                )
                db.session.add(team_obj)
                db.session.flush()
                print(f"Created team: {abbr}")

            team_map[abbr] = team_obj
        # --- Players ---
        existing_player_ids = {
            p.playerId for p in Player.query.with_entities(Player.playerId).all()
        }

        new_players = 0
        for _, row in players_df.iterrows():
            if row["playerId"] in existing_player_ids:
                continue
            # Map the team abbreviation to a Team ORM object if possible
            team_abbr = row.get("team")
            team_obj = team_map.get(team_abbr) if pd.notna(team_abbr) else None
            player = Player(
                team_id=team_obj.id if team_obj else None,
                playerId=row["playerId"],
                firstName=row["firstName"],
                lastName=row["lastName"],
                nationality=row.get("nationality")
                if pd.notna(row.get("nationality"))
                else None,
                birthDate=row.get("birthDate")
                if pd.notna(row.get("birthDate"))
                else None,
                height=int(row["height"]) if pd.notna(row.get("height")) else None,
                weight=int(row["weight"]) if pd.notna(row.get("weight")) else None,
                position=row.get("position") if pd.notna(row.get("position")) else None,
                shootsCatches=row.get("shootsCatches")
                if pd.notna(row.get("shootsCatches"))
                else None,
                team=team_abbr if pd.notna(team_abbr) else None,
            )
            db.session.add(player)
            new_players += 1

        if new_players:
            db.session.flush()
            print(f"Created {new_players} players")

        # --- Games ---
        existing_game_ids = {
            g.source_game_id
            for g in Game.query.with_entities(Game.source_game_id).all()
        }

        new_games = 0
        for _, row in games_df.iterrows():
            if row["id"] in existing_game_ids:
                continue
            home_team = team_map.get(row["home_team_abbrev"])
            away_team = team_map.get(row["away_team_abbrev"])
            if not home_team or not away_team:
                print(
                    f"Skipping game {row['id']}: "
                    f"missing team mapping for {row['home_team_abbrev']} or {row['away_team_abbrev']}"
                )
                continue
            game = Game(
                league_id=ahl.id,
                date=pd.to_datetime(row["game_date"]).date(),
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_team_score=row["home_team_score"],
                away_team_score=row["away_team_score"],
                last_period=row["period"],
                source_game_id=row["id"],
            )
            db.session.add(game)
            new_games += 1

        if new_games:
            db.session.flush()
            print(f"Created {new_games} games")

        # --- Default User ---
        user = User.query.filter_by(username="snakepuck").first()
        if not user:
            user = User(username="snakepuck")
            user.set_password("operationwincups")
            db.session.add(user)
            print("Created user: snakepuck")

        db.session.commit()
        print("Seed complete.")


if __name__ == "__main__":
    seed()
