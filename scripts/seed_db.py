"""Seed the database from parquet files.

Usage:
    python -m scripts.seed_db
"""

import os

import pandas as pd

from app import create_app
from app.extensions import db
from app.models import (
    Division,
    Event,
    Game,
    League,
    Organization,
    Player,
    PlayerStats,
    Season,
    Stint,
    Team,
    TeamStats,
    User,
)

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

        # --- Divisions ---
        ahl_division_names = ["Atlantic", "North", "Central", "Pacific"]
        division_map = {}  # division name -> Division ORM object
        for div_name in ahl_division_names:
            div = Division.query.filter_by(name=div_name, league_id=ahl.id).first()
            if not div:
                div = Division(name=div_name, league_id=ahl.id)
                db.session.add(div)
                db.session.flush()
                print(f"Created division: {div_name}")
            division_map[div_name] = div

        ahl_team_divisions = {
            "HER": "Atlantic",
            "PRO": "Atlantic",
            "WBS": "Atlantic",
            "CLT": "Atlantic",
            "HFD": "Atlantic",
            "LV": "Atlantic",
            "SPR": "Atlantic",
            "BRI": "Atlantic",
            "CLE": "North",
            "RCH": "North",
            "SYC": "North",
            "BEL": "North",
            "TOR": "North",
            "UTC": "North",
            "LAV": "North",
            "MIL": "Central",
            "GR": "Central",
            "RFD": "Central",
            "TEX": "Central",
            "MB": "Central",
            "IA": "Central",
            "CHI": "Central",
            "CVF": "Pacific",
            "TUC": "Pacific",
            "ONT": "Pacific",
            "COL": "Pacific",
            "ABB": "Pacific",
            "BAK": "Pacific",
            "CAL": "Pacific",
            "HEN": "Pacific",
            "SD": "Pacific",
            "SJ": "Pacific",
        }

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
        stints_df = pd.read_parquet(os.path.join(DATA_DIR, "stints.parquet"))

        # Build player_id -> team abbreviation mapping from stints
        # Use the most frequent team per player
        player_team_map = (
            stints_df[["player_id", "team"]]
            .dropna()
            .groupby("player_id")["team"]
            .agg(lambda x: x.value_counts().index[0])
            .to_dict()
        )

        # Get unique team abbreviations from both parquets
        game_teams = set(games_df["home_team"].dropna().unique()) | set(
            games_df["away_team"].dropna().unique()
        )
        team_names = {
            "ABB": [
                "Abbotsford Canucks",
                "https://assets.leaguestat.com/ahl/logos/50x50/440.png",
            ],
            "BAK": [
                "Bakersfield Condors",
                "https://assets.leaguestat.com/ahl/logos/50x50/402_81.png",
            ],
            "BEL": [
                "Belleville Senators",
                "https://assets.leaguestat.com/ahl/logos/50x50/413.png",
            ],
            "BRI": [
                "Bridgeport Islanders",
                "https://assets.leaguestat.com/ahl/logos/50x50/317_81.png",
            ],
            "CAL": [
                "Calgary Wranglers",
                "https://assets.leaguestat.com/ahl/logos/50x50/444_81.png",
            ],
            "CHI": [
                "Chicago Wolves",
                "https://assets.leaguestat.com/ahl/logos/50x50/330.png",
            ],
            "CLE": [
                "Cleveland Monsters",
                "https://assets.leaguestat.com/ahl/logos/50x50/373_81.png",
            ],
            "CLT": [
                "Charlotte Checkers",
                "https://assets.leaguestat.com/ahl/logos/50x50/384.png",
            ],
            "COL": [
                "Colorado Eagles",
                "https://assets.leaguestat.com/ahl/logos/50x50/419.png",
            ],
            "CVF": [
                "Coachella Valley Firebirds",
                "https://assets.leaguestat.com/ahl/logos/50x50/445.png",
            ],
            "GR": [
                "Grand Rapids Griffins",
                "https://assets.leaguestat.com/ahl/logos/50x50/328_81.png",
            ],
            "HER": [
                "Hershey Bears",
                "https://assets.leaguestat.com/ahl/logos/50x50/319_81.png",
            ],
            "HFD": [
                "Hartford Wolf Pack",
                "https://assets.leaguestat.com/ahl/logos/50x50/307.png",
            ],
            "HEN": [
                "Henderson Silver Knights",
                "https://assets.leaguestat.com/ahl/logos/50x50/437.png",
            ],
            "IA": [
                "Iowa Wild",
                "https://assets.leaguestat.com/ahl/logos/50x50/389.png",
            ],
            "LAV": [
                "Laval Rocket",
                "https://assets.leaguestat.com/ahl/logos/50x50/415.png",
            ],
            "LV": [
                "Lehigh Valley Phantoms",
                "https://assets.leaguestat.com/ahl/logos/50x50/313.png",
            ],
            "MB": [
                "Manitoba Moose",
                "https://assets.leaguestat.com/ahl/logos/50x50/321_81.png",
            ],
            "MIL": [
                "Milwaukee Admirals",
                "https://assets.leaguestat.com/ahl/logos/50x50/327_81.png",
            ],
            "ONT": [
                "Ontario Reign",
                "https://assets.leaguestat.com/ahl/logos/50x50/403.png",
            ],
            "PRO": [
                "Providence Bruins",
                "https://assets.leaguestat.com/ahl/logos/50x50/309.png",
            ],
            "RFD": [
                "Rockford IceHogs",
                "https://assets.leaguestat.com/ahl/logos/50x50/372_81.png",
            ],
            "RCH": [
                "Rochester Americans",
                "https://assets.leaguestat.com/ahl/logos/50x50/323_81.png",
            ],
            "SD": [
                "San Diego Gulls",
                "https://assets.leaguestat.com/ahl/logos/50x50/404.png",
            ],
            "SJ": [
                "San Jose Barracuda",
                "https://assets.leaguestat.com/ahl/logos/50x50/405_81.png",
            ],
            "SPR": [
                "Springfield Thunderbirds",
                "https://assets.leaguestat.com/ahl/logos/50x50/411_81.png",
            ],
            "SYC": [
                "Syracuse Crunch",
                "https://assets.leaguestat.com/ahl/logos/50x50/324.png",
            ],
            "TEX": [
                "Texas Stars",
                "https://assets.leaguestat.com/ahl/logos/50x50/380_81.png",
            ],
            "TOR": [
                "Toronto Marlies",
                "https://assets.leaguestat.com/ahl/logos/50x50/335_81.png",
            ],
            "TUC": [
                "Tucson Roadrunners",
                "https://assets.leaguestat.com/ahl/logos/50x50/412.png",
            ],
            "UTC": [
                "Utica Comets",
                "https://assets.leaguestat.com/ahl/logos/50x50/390_81.png",
            ],
            "WBS": [
                "Wilkes-Barre/Scranton Penguins",
                "https://assets.leaguestat.com/ahl/logos/50x50/316_81.png",
            ],
        }

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
                team_info = team_names.get(abbr, [None, None])
                team_obj = Team(
                    organization_id=org.id,
                    season_id=season.id,
                    league_id=ahl.id,
                    abbrev=abbr,
                    name=team_info[0],
                    logo=team_info[1],
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

            # Map the player to a team via stints data
            team_abbr = player_team_map.get(row["player_id"])
            team_obj = team_map.get(team_abbr) if team_abbr else None
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
                team=team_abbr,
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

        # --- Stints ---
        existing_stint_count = Stint.query.count()
        if existing_stint_count == 0:
            print("Seeding stints...")
            stint_records = []
            for _, row in stints_df.iterrows():
                stint_records.append(
                    Stint(
                        game_id=row["game_id"],
                        player_id=row["player_id"],
                        period=int(row["period"])
                        if pd.notna(row.get("period"))
                        else None,
                        period_time_start=str(row["period_time_start"])
                        if pd.notna(row.get("period_time_start"))
                        else None,
                        period_time_end=str(row["period_time_end"])
                        if pd.notna(row.get("period_time_end"))
                        else None,
                        game_stint=int(row["game_stint"])
                        if pd.notna(row.get("game_stint"))
                        else None,
                        n_home_skaters=int(row["n_home_skaters"])
                        if pd.notna(row.get("n_home_skaters"))
                        else None,
                        n_away_skaters=int(row["n_away_skaters"])
                        if pd.notna(row.get("n_away_skaters"))
                        else None,
                        is_home_net_empty=bool(row["is_home_net_empty"])
                        if pd.notna(row.get("is_home_net_empty"))
                        else None,
                        is_away_net_empty=bool(row["is_away_net_empty"])
                        if pd.notna(row.get("is_away_net_empty"))
                        else None,
                        home_score=int(row["home_score"])
                        if pd.notna(row.get("home_score"))
                        else None,
                        away_score=int(row["away_score"])
                        if pd.notna(row.get("away_score"))
                        else None,
                        source_team_id=str(row["team_id"])
                        if pd.notna(row.get("team_id"))
                        else None,
                        team_abbr=row["team"] if pd.notna(row.get("team")) else None,
                    )
                )
                if len(stint_records) >= 5000:
                    db.session.bulk_save_objects(stint_records)
                    db.session.flush()
                    stint_records = []
            if stint_records:
                db.session.bulk_save_objects(stint_records)
                db.session.flush()
            print(f"Seeded stints")
        else:
            print(f"Stints already seeded ({existing_stint_count} rows)")

        # --- Events ---
        existing_event_count = Event.query.count()
        if existing_event_count == 0:
            print("Seeding events...")
            events_df = pd.read_parquet(os.path.join(DATA_DIR, "events.parquet"))
            event_records = []
            for _, row in events_df.iterrows():
                event_records.append(
                    Event(
                        game_id=row["game_id"],
                        player_id=str(row["player_id"])
                        if pd.notna(row.get("player_id"))
                        else None,
                        period=int(row["period"])
                        if pd.notna(row.get("period"))
                        else None,
                        period_time=str(row["period_time"])
                        if pd.notna(row.get("period_time"))
                        else None,
                        game_stint=int(row["game_stint"])
                        if pd.notna(row.get("game_stint"))
                        else None,
                        sl_event_id=str(row["sl_event_id"])
                        if pd.notna(row.get("sl_event_id"))
                        else None,
                        sequence_id=int(row["sequence_id"])
                        if pd.notna(row.get("sequence_id"))
                        else None,
                        team_abbr=row["team"] if pd.notna(row.get("team")) else None,
                        source_team_id=str(row["team_id"])
                        if pd.notna(row.get("team_id"))
                        else None,
                        opp_team_abbr=row["opp_team"]
                        if pd.notna(row.get("opp_team"))
                        else None,
                        opp_source_team_id=str(row["opp_team_id"])
                        if pd.notna(row.get("opp_team_id"))
                        else None,
                        event_type=row["event_type"]
                        if pd.notna(row.get("event_type"))
                        else None,
                        outcome=row["outcome"]
                        if pd.notna(row.get("outcome"))
                        else None,
                        flags=str(row["flags"]) if pd.notna(row.get("flags")) else None,
                        description=str(row["description"])
                        if pd.notna(row.get("description"))
                        else None,
                        detail=str(row["detail"])
                        if pd.notna(row.get("detail"))
                        else None,
                        xg=float(row["sl_xg_all_shots"])
                        if pd.notna(row.get("sl_xg_all_shots"))
                        else None,
                        x=float(row["x"]) if pd.notna(row.get("x")) else None,
                        y=float(row["y"]) if pd.notna(row.get("y")) else None,
                        x_adj=float(row["x_adj"])
                        if pd.notna(row.get("x_adj"))
                        else None,
                        y_adj=float(row["y_adj"])
                        if pd.notna(row.get("y_adj"))
                        else None,
                        has_tracking_data=bool(row["has_tracking_data"])
                        if pd.notna(row.get("has_tracking_data"))
                        else None,
                        event_player_tracked=bool(row["event_player_tracked"])
                        if pd.notna(row.get("event_player_tracked"))
                        else None,
                    )
                )
                if len(event_records) >= 5000:
                    db.session.bulk_save_objects(event_records)
                    db.session.flush()
                    event_records = []
            if event_records:
                db.session.bulk_save_objects(event_records)
                db.session.flush()
            print(f"Seeded events")
        else:
            print(f"Events already seeded ({existing_event_count} rows)")

        # --- PlayerStats ---
        print("Computing player stats...")
        # Get the most recent game date for age calculation
        most_recent_game_date = db.session.query(db.func.max(Game.date)).scalar()

        # Get all player_ids that have events
        player_ids_with_events = (
            db.session.query(Event.player_id)
            .filter(Event.player_id.isnot(None))
            .distinct()
            .all()
        )
        new_player_stats = 0
        for (pid,) in player_ids_with_events:
            ps = PlayerStats.query.filter_by(player_id=pid, season_id=season.id).first()
            if not ps:
                ps = PlayerStats(player_id=pid, season_id=season.id)
                db.session.add(ps)

            # Games played: distinct game_ids from stints
            gp = (
                db.session.query(Stint.game_id)
                .filter(Stint.player_id == pid)
                .distinct()
                .count()
            )

            # Event counts
            goals = Event.query.filter_by(player_id=pid, event_type="goal").count()
            assists = Event.query.filter_by(player_id=pid, event_type="assist").count()
            shots = Event.query.filter_by(player_id=pid, event_type="shot").count()
            faceoffs_won = Event.query.filter(
                Event.player_id == pid,
                Event.event_type == "faceoff",
                Event.outcome == "successful",
            ).count()
            faceoffs_lost = Event.query.filter(
                Event.player_id == pid,
                Event.event_type == "faceoff",
                Event.outcome == "failed",
            ).count()
            penalties = Event.query.filter_by(
                player_id=pid, event_type="penalty"
            ).count()
            penalties_drawn = Event.query.filter_by(
                player_id=pid, event_type="penaltydrawn"
            ).count()
            blocks = Event.query.filter_by(player_id=pid, event_type="block").count()
            checks = Event.query.filter_by(player_id=pid, event_type="check").count()

            # xG sum
            xg_result = (
                db.session.query(db.func.sum(Event.xg))
                .filter(Event.player_id == pid, Event.xg.isnot(None))
                .scalar()
            )
            total_xg = round(float(xg_result), 3) if xg_result else 0.0

            total_shots = shots + goals  # goals are also shots on net
            shooting_pct = round(goals / total_shots, 3) if total_shots > 0 else None
            total_fo = faceoffs_won + faceoffs_lost
            faceoff_pct = round(faceoffs_won / total_fo, 3) if total_fo > 0 else None

            ps.games_played = gp
            ps.goals = goals
            ps.assists = assists
            ps.points = goals + assists
            ps.shots = total_shots
            ps.shooting_pct = shooting_pct
            ps.faceoffs_won = faceoffs_won
            ps.faceoffs_lost = faceoffs_lost
            ps.faceoff_pct = faceoff_pct
            ps.penalties = penalties
            ps.penalties_drawn = penalties_drawn
            ps.blocks = blocks
            ps.checks = checks
            ps.xg = total_xg

            # Compute age from most recent game date - birthDate
            if most_recent_game_date:
                player_obj = Player.query.filter_by(playerId=pid).first()
                if player_obj and player_obj.birthDate:
                    bd = player_obj.birthDate
                    ps.age = (
                        most_recent_game_date.year
                        - bd.year
                        - (
                            (most_recent_game_date.month, most_recent_game_date.day)
                            < (bd.month, bd.day)
                        )
                    )

            new_player_stats += 1

        if new_player_stats:
            db.session.flush()
            print(f"Upserted {new_player_stats} player stats records")

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

            # Look up division for this team
            team_abbr = None
            for abbr, t in team_map.items():
                if t.id == tid:
                    team_abbr = abbr
                    break
            div_name = ahl_team_divisions.get(team_abbr)
            if div_name:
                ts.division_id = division_map[div_name].id

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
