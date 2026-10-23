"""Smoke tests that need no database: the app boots and every route renders."""

import json

import pytest

ROUTES = [
    "/about",
    "/team-standings",
    "/player-stats",
    "/player-analysis",
    "/sample-data",
    "/blog-posts",
    "/blog/some-post",
    "/team/1",
    "/player/1",
    "/player/1/game/1",
]


def test_index_serves(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"SnakePuck" in resp.data


def test_dependencies_registered(dash):
    outputs = {p for d in dash.deps for p in d["output"].strip(".").split("...")}
    for expected in [
        "page-content.children",
        "standings-table.children",
        "game-report-rink-graph.figure",
        "blog-post-content.children",
    ]:
        assert expected in outputs


@pytest.mark.parametrize("pathname", ROUTES)
def test_route_renders_layout(dash, pathname):
    result = dash.call(["page-content.children"], {"url.pathname": pathname})
    assert result["page-content.children"]


def test_unknown_route_falls_back_to_about(dash):
    about = dash.call(["page-content.children"], {"url.pathname": "/about"})
    unknown = dash.call(["page-content.children"], {"url.pathname": "/nope"})
    assert json.dumps(unknown) == json.dumps(about)
