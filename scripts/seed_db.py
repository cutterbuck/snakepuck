"""Seed the database from parquet files.

Usage:
    python -m scripts.seed_db
"""

import os

import pandas as pd

from app import create_app
from app.extensions import db
from app.models import Game, League, Organization, Player, Season, Team, TeamStats, User

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
            p[0] for p in Player.query.with_entities(Player.playerId).all()
        }
        new_players = 0
        for _, row in players_df.iterrows():
            if row["player_id"] in existing_player_ids:
                continue

            # Map the team abbreviation to a Team ORM object if possible
            team_abbr = row.get("team")
            team_obj = team_map.get(team_abbr) if pd.notna(team_abbr) else None
            player = Player(
                team_id=team_obj.id if team_obj else None,
                playerId=row["player_id"],
                firstName=row["first_name"],
                lastName=row["last_name"],
                birthDate=pd.to_datetime(row.get("birth_date")).date()
                if pd.notna(row.get("birth_date"))
                else None,
                position=row.get("primary_position")
                if pd.notna(row.get("primary_position"))
                else None,
                position_group=row.get("position_group")
                if pd.notna(row.get("position_group"))
                else None,
                handed=row.get("handed") if pd.notna(row.get("handed")) else None,
                team=team_abbr if pd.notna(team_abbr) else None,
            )
            db.session.add(player)
            new_players += 1

        if new_players:
            db.session.flush()
            print(f"Created {new_players} players")

        # --- Games ---
        existing_game_ids = {g[0] for g in Game.query.with_entities(Game.game_id).all()}
        new_games = 0
        for _, row in games_df.iterrows():
            if row["game_id"] in existing_game_ids:
                continue
            home_team = team_map.get(row["home_team"])
            away_team = team_map.get(row["away_team"])
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
                home_score=row["home_score"],
                away_score=row["away_score"],
                game_id=row["game_id"],
                game_outcome=row["game_outcome"],
                home_start_net=row["home_start_net"],
            )
            db.session.add(game)
            new_games += 1

        if new_games:
            db.session.flush()
            print(f"Created {new_games} games")

        # --- TeamStats ---
        print("Computing team stats...")
        team_stats_map = {}

        for team_obj in team_map.values():
            team_stats_map[team_obj.id] = {
                "team_id": team_obj.id,
                "season_id": season.id,
                "games_played": 0,
                "wins": 0,
                "losses": 0,
                "ot_losses": 0,
                "points": 0,
                "regulation_wins": 0,
                "regulation_or_ot_wins": 0,
                "goals_forward": 0,
                "goals_against": 0,
                "so_wins": 0,
                "so_losses": 0,
            }

        all_games = Game.query.filter_by(league_id=ahl.id).all()
        for game in all_games:
            home_id = game.home_team_id
            away_id = game.away_team_id
            outcome = (game.game_outcome or "").lower().strip()

            # Outcome values: home_win, away_win, home_ot_win, away_ot_win,
            #                 home_so_win, away_so_win
            is_overtime = "_ot_" in outcome
            is_shootout = "_so_" in outcome
            is_regulation = not is_overtime and not is_shootout

            if outcome.startswith("home"):
                winner_id, loser_id = home_id, away_id
            else:
                winner_id, loser_id = away_id, home_id

            for tid in [home_id, away_id]:
                if tid in team_stats_map:
                    team_stats_map[tid]["games_played"] += 1

            if home_id in team_stats_map:
                team_stats_map[home_id]["goals_forward"] += game.home_score
                team_stats_map[home_id]["goals_against"] += game.away_score
            if away_id in team_stats_map:
                team_stats_map[away_id]["goals_forward"] += game.away_score
                team_stats_map[away_id]["goals_against"] += game.home_score

            # Winner gets 2 points
            if winner_id in team_stats_map:
                team_stats_map[winner_id]["wins"] += 1
                team_stats_map[winner_id]["points"] += 2
                if is_regulation:
                    team_stats_map[winner_id]["regulation_wins"] += 1
                    team_stats_map[winner_id]["regulation_or_ot_wins"] += 1
                elif is_overtime:
                    team_stats_map[winner_id]["regulation_or_ot_wins"] += 1
                elif is_shootout:
                    team_stats_map[winner_id]["so_wins"] += 1

            # Loser: regulation loss (0 pts) or OT/SO loss (1 pt)
            if loser_id in team_stats_map:
                if is_regulation:
                    team_stats_map[loser_id]["losses"] += 1
                else:
                    team_stats_map[loser_id]["ot_losses"] += 1
                    team_stats_map[loser_id]["points"] += 1
                    if is_shootout:
                        team_stats_map[loser_id]["so_losses"] += 1

        new_team_stats = 0
        for tid, s in team_stats_map.items():
            gp = s["games_played"]
            possible_points = gp * 2 if gp > 0 else 1
            pts_pct = round(s["points"] / possible_points, 3) if gp > 0 else 0.0
            goal_diff = s["goals_forward"] - s["goals_against"]
            so_record = f"{s['so_wins']}-{s['so_losses']}"

            ts = TeamStats.query.filter_by(team_id=tid, season_id=season.id).first()
            if not ts:
                ts = TeamStats(team_id=tid, season_id=season.id)
                db.session.add(ts)

            ts.games_played = gp
            ts.wins = s["wins"]
            ts.losses = s["losses"]
            ts.ot_losses = s["ot_losses"]
            ts.points = s["points"]
            ts.points_percentage = pts_pct
            ts.regulation_wins = s["regulation_wins"]
            ts.regulation_or_ot_wins = s["regulation_or_ot_wins"]
            ts.goals_forward = s["goals_forward"]
            ts.goals_against = s["goals_against"]
            ts.goal_diff = goal_diff
            ts.so_record = so_record
            new_team_stats += 1

        if new_team_stats:
            db.session.flush()
            print(f"Upserted {new_team_stats} team stats records")

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
