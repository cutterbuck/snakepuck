"""Check whether the next event after each qualifying LPR involves the same player.

Usage:
    python -m scripts.check_next_event
"""

from collections import defaultdict

from sqlalchemy import func

from app import create_app
from app.extensions import db
from app.models import Event, Player, PlayerStats
from app.models.game import Game
from app.models.stint import Stint

MIN_GP = 20
LPR_DESCRIPTIONS = [
    "HI PRESS DUMP IN LPR+",
    "CONT HI PRESS DUMP IN LPR+",
]

app = create_app()

with app.app_context():
    # Get qualifying defensemen
    gp_rows = (
        db.session.query(PlayerStats.player_id)
        .join(Player, PlayerStats.player_id == Player.playerId)
        .filter(Player.position == "D")
        .group_by(PlayerStats.player_id)
        .having(func.sum(PlayerStats.games_played) >= MIN_GP)
        .all()
    )
    player_ids = [r.player_id for r in gp_rows]

    # Get 5v5 game_stint set
    ev5_rows = (
        db.session.query(Stint.game_id, Stint.game_stint)
        .filter(Stint.n_home_skaters == 5, Stint.n_away_skaters == 5)
        .distinct()
        .all()
    )
    ev5_set = {(r.game_id, r.game_stint) for r in ev5_rows}

    # Get qualifying LPR events
    lpr_events = Event.query.filter(
        Event.event_type == "lpr",
        Event.description.in_(LPR_DESCRIPTIONS),
        Event.player_id.in_(player_ids),
    ).all()
    lpr_events = [e for e in lpr_events if (e.game_id, e.game_stint) in ev5_set]

    print(f"Total qualifying LPR events: {len(lpr_events)}")

    # Batch-fetch all events for relevant games
    lpr_game_ids = {e.game_id for e in lpr_events}
    all_events = (
        Event.query.filter(Event.game_id.in_(lpr_game_ids))
        .order_by(Event.game_id, Event.period, Event.period_time, Event.id)
        .all()
    )

    # Index: (game_id, player_id) -> list of events sorted by period, period_time, id
    player_game_events = defaultdict(list)
    for ev in all_events:
        if ev.player_id:
            player_game_events[(ev.game_id, ev.player_id)].append(ev)

    # Build lookup: (game_id, player_id, event.id) -> index
    player_evt_idx = {}
    for key, evts in player_game_events.items():
        for i, ev in enumerate(evts):
            player_evt_idx[(key[0], key[1], ev.id)] = i

    # Batch-fetch player names
    all_player_ids = {e.player_id for e in lpr_events}
    for ev in all_events:
        if ev.player_id:
            all_player_ids.add(ev.player_id)
    player_rows = Player.query.filter(Player.playerId.in_(all_player_ids)).all()
    player_names = {p.playerId: f"{p.firstName} {p.lastName}" for p in player_rows}

    # For each LPR, find the same player's events within 5 seconds
    WINDOW = 5.0
    no_next = 0
    next_event_types = defaultdict(int)
    total_followups = 0
    example = None

    for e in lpr_events:
        idx = player_evt_idx.get((e.game_id, e.player_id, e.id))
        if idx is None:
            no_next += 1
            continue

        evts = player_game_events[(e.game_id, e.player_id)]
        followups = []
        for j in range(idx + 1, len(evts)):
            nxt = evts[j]
            if nxt.period != e.period:
                break
            if e.period_time is None or nxt.period_time is None:
                break
            elapsed = nxt.period_time - e.period_time
            if elapsed > WINDOW:
                break
            followups.append((nxt, elapsed))

        if not followups:
            no_next += 1
            continue

        total_followups += len(followups)
        for nxt, _ in followups:
            next_event_types[nxt.event_type] += 1

        if example is None:
            example = (e, followups)

    print(f"\nLPRs with no follow-up within {WINDOW}s: {no_next}")
    print(f"Total follow-up events within {WINDOW}s:  {total_followups}")
    print(f"\nEvent type breakdown (within {WINDOW}s):")
    for etype, count in sorted(next_event_types.items(), key=lambda x: -x[1]):
        print(f"  {etype}: {count}")

    # Print example
    if example:
        lpr_evt, followups = example
        game = Game.query.filter_by(game_id=lpr_evt.game_id).first()
        lpr_player = player_names.get(lpr_evt.player_id, "Unknown")
        home = game.home_team.abbrev if game.home_team else "?"
        away = game.away_team.abbrev if game.away_team else "?"
        print(f"\n--- Example: LPR + events within {WINDOW}s ---")
        print(f"Player:       {lpr_player} ({lpr_evt.team_abbr})")
        print(
            f"LPR Event:    {lpr_evt.event_type} | {lpr_evt.description} | outcome: {lpr_evt.outcome}"
        )
        print(f"LPR Period:   {lpr_evt.period} | Time: {lpr_evt.period_time}")
        print(
            f"Game:         {away} @ {home} | {game.date} | Score: {game.away_score}-{game.home_score}"
        )
        for nxt, elapsed in followups:
            print(
                f"  +{elapsed:.2f}s  {nxt.event_type} | {nxt.description} | outcome: {nxt.outcome}"
            )
    else:
        print("\nNo example found.")
