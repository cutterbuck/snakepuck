"""Drive each page's data callbacks against the local database.

These walk the same callback chain the browser does (URL -> ids -> dropdowns
-> tables) and check that real data comes back.
"""

import json

import pytest

from app.models import Game, Player, PlayerGameStats, Stint

pytestmark = pytest.mark.db

DEFAULT_SORT = {"column": "PTS", "direction": "desc"}


def _text(value):
    return json.dumps(value)


@pytest.fixture(scope="module")
def sample_ids(server, db_available):
    """A player/game pair with stats, plus a stint in that game."""
    if not db_available:
        pytest.skip("local Postgres unreachable")
    with server.app_context():
        pgs = PlayerGameStats.query.order_by(PlayerGameStats.id).first()
        player = Player.query.filter_by(playerId=pgs.player_id).one()
        game = Game.query.filter_by(game_id=pgs.game_id).one()
        stint = (
            Stint.query.filter_by(player_id=player.playerId, game_id=game.game_id)
            .order_by(Stint.id)
            .first()
        )
        return {
            "player_id": player.id,
            "game_pk": game.id,
            "game_id": game.game_id,
            "team_pk": pgs.team_id,
            "stint_id": stint.id,
        }


def _league_and_season(dash, prefix):
    league = dash.call(
        [f"{prefix}-league.options", f"{prefix}-league.value"],
        {"url.pathname": "/"},
    )
    league_id = league[f"{prefix}-league.value"]
    assert league_id is not None
    season = dash.call(
        [f"{prefix}-season.options", f"{prefix}-season.value"],
        {f"{prefix}-league.value": league_id},
    )
    season_id = season[f"{prefix}-season.value"]
    assert season_id is not None
    return league_id, season_id


def test_standings_table(dash):
    league_id, season_id = _league_and_season(dash, "standings")
    result = dash.call(
        ["standings-table.children"],
        {
            "standings-league.value": league_id,
            "standings-season.value": season_id,
            "standings-sort.data": DEFAULT_SORT,
            "standings-view.data": "division",
        },
    )
    assert _text(result).count('"standings-row"') >= 30


def test_player_stats_table(dash):
    league_id, season_id = _league_and_season(dash, "ps")
    result = dash.call(
        ["ps-table.children", "ps-pagination.children"],
        {
            "ps-league.value": league_id,
            "ps-season.value": season_id,
            "ps-sort.data": DEFAULT_SORT,
            "ps-situation.data": "tot",
            "ps-page.data": 1,
        },
    )
    assert _text(result["ps-table.children"]).count('"ps-player-row"') >= 10


def test_team_detail(dash, sample_ids):
    team_id = dash.call(
        ["team-detail-id.data"], {"url.pathname": f"/team/{sample_ids['team_pk']}"}
    )["team-detail-id.data"]
    assert team_id == sample_ids["team_pk"]
    season = dash.call(
        ["season-selector.options", "season-selector.value"],
        {"team-detail-id.data": team_id},
    )
    result = dash.call(
        ["team-detail-table.children"],
        {
            "team-detail-sort.data": DEFAULT_SORT,
            "season-selector.value": season["season-selector.value"],
            "team-detail-situation.data": "tot",
        },
    )
    assert _text(result).count('"team-roster-row"') >= 10


def test_player_detail(dash, sample_ids):
    player_id = dash.call(
        ["player-detail-id.data"],
        {"url.pathname": f"/player/{sample_ids['player_id']}"},
    )["player-detail-id.data"]
    assert player_id == sample_ids["player_id"]
    inputs = {"player-detail-id.data": player_id, "player-detail-situation.data": "tot"}
    assert dash.call(["player-detail-stats.children"], inputs)[
        "player-detail-stats.children"
    ]
    log = dash.call(["player-detail-game-log.children"], inputs)
    assert '"game-log-row"' in _text(log)


def test_game_report(dash, sample_ids):
    ids = dash.call(
        [
            "game-report-player-id.data",
            "game-report-game-id.data",
            "game-report-breadcrumb.children",
        ],
        {
            "url.pathname": f"/player/{sample_ids['player_id']}/game/{sample_ids['game_pk']}"
        },
    )
    assert ids["game-report-player-id.data"] == sample_ids["player_id"]
    assert ids["game-report-game-id.data"] == sample_ids["game_id"]

    stats = dash.call(
        ["game-report-stats.children"],
        {
            "game-report-player-id.data": sample_ids["player_id"],
            "game-report-game-id.data": sample_ids["game_id"],
            "game-report-situation.data": "tot",
        },
    )
    assert stats["game-report-stats.children"]

    stints = dash.call(
        ["game-report-stints.children", "game-report-merged-stints.data"],
        {
            "game-report-player-id.data": sample_ids["player_id"],
            "game-report-game-id.data": sample_ids["game_id"],
            "game-report-stint-period.data": 1,
        },
    )
    assert '"stint-row"' in _text(stints["game-report-stints.children"])

    rink = dash.call(
        ["game-report-rink-base.data"],
        {"game-report-game-id.data": sample_ids["game_id"]},
    )["game-report-rink-base.data"]
    assert rink["data"] and rink["layout"]["shapes"]


def test_stint_frames(dash, sample_ids):
    result = dash.call(
        [
            "game-report-stint-events.data",
            "game-report-frame-slider.max",
            "game-report-frame-slider.value",
            "game-report-frame-slider.marks",
            "game-report-frame-index.data",
            "game-report-playback-controls.style",
            "game-report-interval.disabled",
            "game-report-play-btn.children",
            "game-report-frame-delays.data",
        ],
        {"game-report-selected-stint.data": sample_ids["stint_id"]},
        {
            "game-report-player-id.data": sample_ids["player_id"],
            "game-report-game-id.data": sample_ids["game_id"],
            "game-report-merged-stints.data": {},
        },
    )
    frames = result["game-report-stint-events.data"]["frames"]
    delays = result["game-report-frame-delays.data"]
    assert frames
    assert len(delays) == len(frames) - 1
    assert all(800 <= d <= 3000 for d in delays)
    # Unidentified skaters (no player_id) are kept and labelled by team
    tracking = [t for f in frames for t in f["tracking"]]
    assert tracking
    unidentified = [t for t in tracking if not t["player_id"]]
    assert unidentified
    assert all(t["player_name"].startswith("Unidentified") for t in unidentified)


def test_blog_posts(dash):
    listing = dash.call(["blog-posts-list.children"], {"url.pathname": "/blog-posts"})
    assert "Randomness" in _text(listing)
    post = dash.call(
        ["blog-post-content.children"],
        {"url.pathname": "/blog/consequences-of-randomness-in-hockey"},
    )
    assert "Hockey Gods" in _text(post)


@pytest.mark.parametrize("view", ["games", "players", "events", "stints", "tracking"])
def test_sample_data(dash, view):
    result = dash.call(
        ["sample-data-content.children"], {"sample-data-view.data": view}
    )
    assert result["sample-data-content.children"]


def test_player_analysis(dash):
    result = dash.call(
        ["player-analysis-dmen-lpr.children"],
        {
            "url.pathname": "/player-analysis",
            "pa-lpr-sort.data": {"column": "xG%", "direction": "desc"},
            "pa-dmen-lpr-dropdown.value": None,
        },
    )
    assert result["player-analysis-dmen-lpr.children"]
