"""Seed the database from parquet files.

Usage:
    python -m scripts.seed_db
"""

import os

import pandas as pd
from sqlalchemy import case

from app import create_app
from app.extensions import db
from app.models import (
    Division,
    Event,
    Game,
    League,
    Organization,
    Player,
    PlayerGameStats,
    PlayerStats,
    Season,
    Stint,
    Team,
    TeamStats,
    Tracking,
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

            player = Player(
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
            total_stints = len(stints_df)
            stint_records = []
            for row_idx, (_, row) in enumerate(stints_df.iterrows(), 1):
                stint_records.append(
                    Stint(
                        game_id=row["game_id"],
                        player_id=row["player_id"],
                        period=int(row["period"])
                        if pd.notna(row.get("period"))
                        else None,
                        period_time_start=float(row["period_time_start"])
                        if pd.notna(row.get("period_time_start"))
                        else None,
                        period_time_end=float(row["period_time_end"])
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
                    print(f"  Stints: {row_idx}/{total_stints} rows")
                    stint_records = []
            if stint_records:
                db.session.bulk_save_objects(stint_records)
                db.session.flush()
            print(f"  Stints: {total_stints}/{total_stints} rows")
            print(f"Seeded stints")

            # Compute shift numbers for each player/game (skip goalies)
            print("Computing shift numbers...")
            pairs = (
                db.session.query(Stint.player_id, Stint.game_id)
                .join(Player, Player.playerId == Stint.player_id)
                .filter(Player.position != "G")
                .distinct()
                .all()
            )
            for player_id, game_id in pairs:
                stints = (
                    Stint.query.filter_by(player_id=player_id, game_id=game_id)
                    .order_by(Stint.game_stint)
                    .all()
                )
                if not stints:
                    continue
                shift_num = 1
                stints[0].shift = shift_num
                for i in range(1, len(stints)):
                    prev = stints[i - 1]
                    curr = stints[i]
                    if (
                        prev.period_time_end is not None
                        and curr.period_time_start is not None
                        and prev.period_time_end == curr.period_time_start
                    ):
                        curr.shift = shift_num
                    else:
                        shift_num += 1
                        curr.shift = shift_num
            db.session.commit()
            print("Computed shift numbers")
        else:
            print(f"Stints already seeded ({existing_stint_count} rows)")

        # --- Events ---
        existing_event_count = Event.query.count()
        if existing_event_count == 0:
            print("Seeding events...")
            events_df = pd.read_parquet(os.path.join(DATA_DIR, "events.parquet"))
            total_events = len(events_df)
            event_records = []
            for row_idx, (_, row) in enumerate(events_df.iterrows(), 1):
                event_records.append(
                    Event(
                        game_id=row["game_id"],
                        player_id=str(row["player_id"])
                        if pd.notna(row.get("player_id"))
                        else None,
                        period=int(row["period"])
                        if pd.notna(row.get("period"))
                        else None,
                        period_time=float(row["period_time"])
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
                    print(f"  Events: {row_idx}/{total_events} rows")
                    event_records = []
            if event_records:
                db.session.bulk_save_objects(event_records)
                db.session.flush()
            print(f"  Events: {total_events}/{total_events} rows")
            print(f"Seeded events")
        else:
            print(f"Events already seeded ({existing_event_count} rows)")

        # --- Tracking ---
        existing_tracking_count = Tracking.query.count()
        if existing_tracking_count == 0:
            print("Seeding tracking...")
            tracking_df = pd.read_parquet(os.path.join(DATA_DIR, "tracking.parquet"))
            total_tracking = len(tracking_df)
            tracking_records = []
            for row_idx, (_, row) in enumerate(tracking_df.iterrows(), 1):
                tracking_records.append(
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
                if len(tracking_records) >= 5000:
                    db.session.bulk_save_objects(tracking_records)
                    db.session.flush()
                    print(f"  Tracking: {row_idx}/{total_tracking} rows")
                    tracking_records = []
            if tracking_records:
                db.session.bulk_save_objects(tracking_records)
                db.session.flush()
            print(f"  Tracking: {total_tracking}/{total_tracking} rows")
            print("Seeded tracking")
        else:
            print(f"Tracking already seeded ({existing_tracking_count} rows)")

        # --- Stint xG + GAP (per stint) ---
        print("Computing stint xG and GAP values...")
        from collections import defaultdict

        # Build game_id -> (home_abbr, away_abbr) mapping
        from sqlalchemy.orm import aliased as sa_aliased

        HomeTeam = sa_aliased(Team)
        AwayTeam = sa_aliased(Team)
        game_rows = (
            db.session.query(
                Game.game_id,
                HomeTeam.abbrev,
                AwayTeam.abbrev,
            )
            .join(HomeTeam, Game.home_team_id == HomeTeam.id)
            .join(AwayTeam, Game.away_team_id == AwayTeam.id)
            .all()
        )
        game_home_away = {}
        for gid, home_abbr, away_abbr in game_rows:
            game_home_away[gid] = (home_abbr, away_abbr)
        del game_rows

        # Load xG events
        xg_events = (
            db.session.query(
                Event.game_id,
                Event.period,
                Event.period_time,
                Event.team_abbr,
                Event.xg,
                Event.player_id,
            )
            .filter(Event.xg.isnot(None))
            .all()
        )
        xg_by_game_period = defaultdict(list)
        for gid, period, pt, team_abbr, xg, pid in xg_events:
            xg_by_game_period[(gid, period)].append((pt, team_abbr, xg, pid))
        del xg_events

        # Load goal/assist events
        gap_events = (
            db.session.query(
                Event.game_id,
                Event.period,
                Event.period_time,
                Event.player_id,
                Event.event_type,
            )
            .filter(Event.event_type.in_(["goal", "assist"]))
            .all()
        )
        gap_by_game_period = defaultdict(list)
        for gid, period, pt, pid, etype in gap_events:
            gap_by_game_period[(gid, period)].append((pt, pid, etype))
        del gap_events

        all_stints_for_xg = Stint.query.all()
        total_stints_xg = len(all_stints_for_xg)
        for idx, stint in enumerate(all_stints_for_xg, 1):
            if idx % 500 == 0 or idx == total_stints_xg:
                print(
                    f"  Stint xG/GAP: {idx}/{total_stints_xg} ({idx * 100 // total_stints_xg}%)"
                )

            # --- xG ---
            tot_i_xg = 0.0
            tot_oi_xgf = 0.0
            tot_oi_xga = 0.0
            if (
                stint.period_time_start is not None
                and stint.period_time_end is not None
            ):
                for evt_time, evt_team, evt_xg, evt_pid in xg_by_game_period.get(
                    (stint.game_id, stint.period), []
                ):
                    if (
                        evt_time is not None
                        and stint.period_time_start <= evt_time < stint.period_time_end
                    ):
                        if evt_team == stint.team_abbr:
                            tot_oi_xgf += evt_xg
                            if evt_pid == stint.player_id:
                                tot_i_xg += evt_xg
                        else:
                            tot_oi_xga += evt_xg
            stint.tot_i_xg = round(tot_i_xg, 3)
            stint.tot_oi_xgf = round(tot_oi_xgf, 3)
            stint.tot_oi_xga = round(tot_oi_xga, 3)

            # --- GAP ---
            tot_goals = 0
            tot_assists = 0
            if (
                stint.period_time_start is not None
                and stint.period_time_end is not None
            ):
                for evt_time, evt_pid, evt_type in gap_by_game_period.get(
                    (stint.game_id, stint.period), []
                ):
                    if (
                        evt_time is not None
                        and evt_pid == stint.player_id
                        and stint.period_time_start <= evt_time < stint.period_time_end
                    ):
                        if evt_type == "goal":
                            tot_goals += 1
                        elif evt_type == "assist":
                            tot_assists += 1
            tot_points = tot_goals + tot_assists
            stint.tot_goals = tot_goals
            stint.tot_assists = tot_assists
            stint.tot_points = tot_points

            # --- Situation flags ---
            n_home = stint.n_home_skaters
            n_away = stint.n_away_skaters
            has_skaters = n_home is not None and n_away is not None

            is_even = has_skaters and n_home == n_away
            is_5v5 = is_even and n_home == 5

            home_away = game_home_away.get(stint.game_id)
            is_pp = False
            is_pk = False
            if has_skaters and home_away and stint.team_abbr:
                is_home = stint.team_abbr == home_away[0]
                player_sk = n_home if is_home else n_away
                opp_sk = n_away if is_home else n_home
                is_pp = player_sk > opp_sk
                is_pk = player_sk < opp_sk

            # xG situations
            stint.es_i_xg = stint.tot_i_xg if is_even else 0.0
            stint.es_oi_xgf = stint.tot_oi_xgf if is_even else 0.0
            stint.es_oi_xga = stint.tot_oi_xga if is_even else 0.0
            stint.ev5_i_xg = stint.tot_i_xg if is_5v5 else 0.0
            stint.ev5_oi_xgf = stint.tot_oi_xgf if is_5v5 else 0.0
            stint.ev5_oi_xga = stint.tot_oi_xga if is_5v5 else 0.0
            stint.pp_i_xg = stint.tot_i_xg if is_pp else 0.0
            stint.pp_oi_xgf = stint.tot_oi_xgf if is_pp else 0.0
            stint.pp_oi_xga = stint.tot_oi_xga if is_pp else 0.0
            stint.pk_i_xg = stint.tot_i_xg if is_pk else 0.0
            stint.pk_oi_xgf = stint.tot_oi_xgf if is_pk else 0.0
            stint.pk_oi_xga = stint.tot_oi_xga if is_pk else 0.0

            # GAP situations
            stint.es_goals = tot_goals if is_even else 0
            stint.es_assists = tot_assists if is_even else 0
            stint.es_points = tot_points if is_even else 0
            stint.ev5_goals = tot_goals if is_5v5 else 0
            stint.ev5_assists = tot_assists if is_5v5 else 0
            stint.ev5_points = tot_points if is_5v5 else 0
            stint.pp_goals = tot_goals if is_pp else 0
            stint.pp_assists = tot_assists if is_pp else 0
            stint.pp_points = tot_points if is_pp else 0
            stint.pk_goals = tot_goals if is_pk else 0
            stint.pk_assists = tot_assists if is_pk else 0
            stint.pk_points = tot_points if is_pk else 0

        db.session.flush()
        del xg_by_game_period, gap_by_game_period, all_stints_for_xg
        print("Computed stint xG and GAP values")

        # --- PlayerStats (per team) ---
        print("Computing player stats (per team)...")
        # Get the most recent game date for age calculation
        most_recent_game_date = db.session.query(db.func.max(Game.date)).scalar()

        # Build abbreviation -> team_id mapping
        abbr_to_team_id = {abbr: t.id for abbr, t in team_map.items()}

        # Get all player_ids that have events
        player_ids_with_events = (
            db.session.query(Event.player_id)
            .filter(Event.player_id.isnot(None))
            .distinct()
            .all()
        )
        new_player_stats = 0
        for (pid,) in player_ids_with_events:
            # Find all teams this player played for (from stints)
            player_teams = (
                db.session.query(Stint.team_abbr)
                .filter(Stint.player_id == pid, Stint.team_abbr.isnot(None))
                .distinct()
                .all()
            )

            # Compute age once per player
            player_age = None
            if most_recent_game_date:
                player_obj = Player.query.filter_by(playerId=pid).first()
                if player_obj and player_obj.birthDate:
                    bd = player_obj.birthDate
                    player_age = (
                        most_recent_game_date.year
                        - bd.year
                        - (
                            (most_recent_game_date.month, most_recent_game_date.day)
                            < (bd.month, bd.day)
                        )
                    )

            for (team_abbr,) in player_teams:
                tid = abbr_to_team_id.get(team_abbr)
                if not tid:
                    continue

                ps = PlayerStats.query.filter_by(
                    player_id=pid, season_id=season.id, team_id=tid
                ).first()
                if not ps:
                    ps = PlayerStats(player_id=pid, season_id=season.id, team_id=tid)
                    db.session.add(ps)

                # Games played: distinct game_ids from stints for this team
                gp = (
                    db.session.query(Stint.game_id)
                    .filter(Stint.player_id == pid, Stint.team_abbr == team_abbr)
                    .distinct()
                    .count()
                )

                # Event counts filtered by team
                goals = Event.query.filter_by(
                    player_id=pid, event_type="goal", team_abbr=team_abbr
                ).count()
                assists = Event.query.filter_by(
                    player_id=pid, event_type="assist", team_abbr=team_abbr
                ).count()
                shots = Event.query.filter_by(
                    player_id=pid, event_type="shot", team_abbr=team_abbr
                ).count()
                faceoffs_won = Event.query.filter(
                    Event.player_id == pid,
                    Event.event_type == "faceoff",
                    Event.outcome == "successful",
                    Event.team_abbr == team_abbr,
                ).count()
                faceoffs_lost = Event.query.filter(
                    Event.player_id == pid,
                    Event.event_type == "faceoff",
                    Event.outcome == "failed",
                    Event.team_abbr == team_abbr,
                ).count()
                penalties = Event.query.filter_by(
                    player_id=pid, event_type="penalty", team_abbr=team_abbr
                ).count()
                penalties_drawn = Event.query.filter_by(
                    player_id=pid, event_type="penaltydrawn", team_abbr=team_abbr
                ).count()
                blocks = Event.query.filter_by(
                    player_id=pid, event_type="block", team_abbr=team_abbr
                ).count()
                checks = Event.query.filter_by(
                    player_id=pid, event_type="check", team_abbr=team_abbr
                ).count()

                # xG sum filtered by team
                xg_result = (
                    db.session.query(db.func.sum(Event.xg))
                    .filter(
                        Event.player_id == pid,
                        Event.xg.isnot(None),
                        Event.team_abbr == team_abbr,
                    )
                    .scalar()
                )
                total_xg = round(float(xg_result), 3) if xg_result else 0.0

                total_shots = shots + goals  # goals are also shots on net
                shooting_pct = (
                    round(goals / total_shots, 3) if total_shots > 0 else None
                )
                total_fo = faceoffs_won + faceoffs_lost
                faceoff_pct = (
                    round(faceoffs_won / total_fo, 3) if total_fo > 0 else None
                )

                ps.games_played = gp
                ps.tot_goals = goals
                ps.tot_assists = assists
                ps.tot_points = goals + assists
                ps.shots = total_shots
                ps.shooting_pct = shooting_pct
                ps.faceoffs_won = faceoffs_won
                ps.faceoffs_lost = faceoffs_lost
                ps.faceoff_pct = faceoff_pct
                ps.penalties = penalties
                ps.penalties_drawn = penalties_drawn
                ps.blocks = blocks
                ps.checks = checks
                ps.tot_i_xg = total_xg

                # Aggregate situation columns from pre-computed stint columns
                player_stints = Stint.query.filter_by(
                    player_id=pid, team_abbr=team_abbr
                ).all()
                xg_fields = [
                    "tot_oi_xgf",
                    "tot_oi_xga",
                    "es_i_xg",
                    "es_oi_xgf",
                    "es_oi_xga",
                    "ev5_i_xg",
                    "ev5_oi_xgf",
                    "ev5_oi_xga",
                    "pp_i_xg",
                    "pp_oi_xgf",
                    "pp_oi_xga",
                    "pk_i_xg",
                    "pk_oi_xgf",
                    "pk_oi_xga",
                ]
                for f in xg_fields:
                    setattr(
                        ps, f, round(sum(getattr(s, f) or 0 for s in player_stints), 3)
                    )

                for prefix in ["tot", "es", "ev5", "pp", "pk"]:
                    xgf = getattr(ps, f"{prefix}_oi_xgf")
                    xga = getattr(ps, f"{prefix}_oi_xga")
                    total_xg_sit = xgf + xga
                    setattr(
                        ps,
                        f"{prefix}_xg_pct",
                        round(xgf / total_xg_sit, 3) if total_xg_sit > 0 else None,
                    )

                # Aggregate situation GAP from pre-computed stint columns
                gap_fields = [
                    "es_goals",
                    "es_assists",
                    "es_points",
                    "ev5_goals",
                    "ev5_assists",
                    "ev5_points",
                    "pp_goals",
                    "pp_assists",
                    "pp_points",
                    "pk_goals",
                    "pk_assists",
                    "pk_points",
                ]
                for f in gap_fields:
                    setattr(ps, f, sum(getattr(s, f) or 0 for s in player_stints))
                ps.age = player_age

                new_player_stats += 1

        if new_player_stats:
            db.session.flush()
            print(f"Upserted {new_player_stats} player stats records")

        # --- PlayerGameStats (per game) ---
        existing_pgs_count = PlayerGameStats.query.count()
        if existing_pgs_count == 0:
            print("Computing player game stats...")
            pgs_records = []
            total_players = len(player_ids_with_events)
            for idx, (pid,) in enumerate(player_ids_with_events, 1):
                if idx % 50 == 0 or idx == total_players:
                    print(
                        f"  Player game stats: {idx}/{total_players} players processed"
                    )

                # Single aggregation query: all stats for all games in one pass
                game_stats = (
                    db.session.query(
                        Event.game_id,
                        Event.team_abbr,
                        db.func.count(case((Event.event_type == "goal", 1))).label(
                            "goals"
                        ),
                        db.func.count(case((Event.event_type == "assist", 1))).label(
                            "assists"
                        ),
                        db.func.count(
                            case((Event.event_type.in_(["shot", "goal"]), 1))
                        ).label("shots"),
                        db.func.count(
                            case(
                                (
                                    db.and_(
                                        Event.event_type == "faceoff",
                                        Event.outcome == "successful",
                                    ),
                                    1,
                                )
                            )
                        ).label("fow"),
                        db.func.count(
                            case(
                                (
                                    db.and_(
                                        Event.event_type == "faceoff",
                                        Event.outcome == "failed",
                                    ),
                                    1,
                                )
                            )
                        ).label("fol"),
                        db.func.count(case((Event.event_type == "penalty", 1))).label(
                            "penalties"
                        ),
                        db.func.count(
                            case((Event.event_type == "penaltydrawn", 1))
                        ).label("penalties_drawn"),
                        db.func.count(case((Event.event_type == "block", 1))).label(
                            "blocks"
                        ),
                        db.func.count(case((Event.event_type == "check", 1))).label(
                            "checks"
                        ),
                        db.func.coalesce(
                            db.func.sum(case((Event.xg.isnot(None), Event.xg))),
                            0.0,
                        ).label("xg"),
                    )
                    .filter(Event.player_id == pid)
                    .group_by(Event.game_id, Event.team_abbr)
                    .all()
                )

                # Filter to only (game, team) pairs where the player had stints
                player_game_teams = set(
                    db.session.query(Stint.game_id, Stint.team_abbr)
                    .filter(Stint.player_id == pid, Stint.team_abbr.isnot(None))
                    .distinct()
                    .all()
                )

                for row in game_stats:
                    gid = row.game_id
                    team_abbr = row.team_abbr
                    if (gid, team_abbr) not in player_game_teams:
                        continue
                    tid = abbr_to_team_id.get(team_abbr)
                    if not tid:
                        continue

                    goals = row.goals
                    assists = row.assists
                    total_shots = row.shots
                    fow = row.fow
                    fol = row.fol
                    total_xg = round(float(row.xg), 3)
                    shooting_pct = (
                        round(goals / total_shots, 3) if total_shots > 0 else None
                    )
                    total_fo = fow + fol
                    faceoff_pct = round(fow / total_fo, 3) if total_fo > 0 else None

                    # Aggregate situation columns from pre-computed stint columns
                    game_stints = Stint.query.filter_by(
                        player_id=pid, game_id=gid, team_abbr=team_abbr
                    ).all()
                    stint_agg = {}
                    for f in [
                        "tot_oi_xgf",
                        "tot_oi_xga",
                        "es_i_xg",
                        "es_oi_xgf",
                        "es_oi_xga",
                        "ev5_i_xg",
                        "ev5_oi_xgf",
                        "ev5_oi_xga",
                        "pp_i_xg",
                        "pp_oi_xgf",
                        "pp_oi_xga",
                        "pk_i_xg",
                        "pk_oi_xgf",
                        "pk_oi_xga",
                    ]:
                        stint_agg[f] = round(
                            sum(getattr(s, f) or 0 for s in game_stints), 3
                        )
                    for f in [
                        "es_goals",
                        "es_assists",
                        "es_points",
                        "ev5_goals",
                        "ev5_assists",
                        "ev5_points",
                        "pp_goals",
                        "pp_assists",
                        "pp_points",
                        "pk_goals",
                        "pk_assists",
                        "pk_points",
                    ]:
                        stint_agg[f] = sum(getattr(s, f) or 0 for s in game_stints)

                    pgs_records.append(
                        PlayerGameStats(
                            player_id=pid,
                            game_id=gid,
                            team_id=tid,
                            season_id=season.id,
                            tot_goals=goals,
                            tot_assists=assists,
                            tot_points=goals + assists,
                            shots=total_shots,
                            shooting_pct=shooting_pct,
                            faceoffs_won=fow,
                            faceoffs_lost=fol,
                            faceoff_pct=faceoff_pct,
                            penalties=row.penalties,
                            penalties_drawn=row.penalties_drawn,
                            blocks=row.blocks,
                            checks=row.checks,
                            tot_i_xg=total_xg,
                            **stint_agg,
                        )
                    )
                    if len(pgs_records) >= 5000:
                        db.session.bulk_save_objects(pgs_records)
                        db.session.flush()
                        pgs_records = []
            if pgs_records:
                db.session.bulk_save_objects(pgs_records)
                db.session.flush()
            print("Seeded player game stats")
        else:
            print(f"Player game stats already seeded ({existing_pgs_count} rows)")

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
