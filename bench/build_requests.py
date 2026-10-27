"""Build the benchmark's request list: for each page view, the requests the Dash site
makes for its data and the Rust API requests that replace them.

    python bench/build_requests.py [dash_url] [api_url] > bench/out/requests.json

Both servers must be running. Dash requests are captured by acting as a minimal Dash
client: each page's callbacks run in order, as the browser would on page load, and each
response feeds the next callback's inputs. Only callbacks that query the database are
kept; the ones that just parse the URL or toggle buttons aren't.

Entities are looked up at run time (the top scorer, his latest game, his third shift),
so no HALO ids are written into this public repo.
"""

import json
import os
import sys

import psycopg2
import requests

DASH = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8060"
API = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8091"
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://localhost:5432/hockey_analytics"
)


def entities() -> dict:
    with psycopg2.connect(DATABASE_URL) as db, db.cursor() as cur:
        cur.execute(
            """
            select p.id, p."playerId", t.id, t.abbrev, s.name
            from player_stats ps
            join players p on p."playerId" = ps.player_id
            join teams t on t.id = ps.team_id
            join seasons s on s.id = ps.season_id
            order by ps.tot_points desc limit 1
            """
        )
        player, player_uuid, team, team_abbr, season = cur.fetchone()
        cur.execute(
            """
            select g.id, g.game_id from player_game_stats pgs
            join games g on g.game_id = pgs.game_id
            where pgs.player_id = %s order by g.date desc limit 1
            """,
            (player_uuid,),
        )
        game, game_uuid = cur.fetchone()
        cur.execute(
            """
            select min(id) from stints
            where player_id = %s and game_id = %s and shift = 3
            """,
            (player_uuid, game_uuid),
        )
        (first_stint_of_shift_3,) = cur.fetchone()
    return locals()


# Each page's Dash callbacks in the order a page load fires them, by output, and the
# store defaults from the page's layout.
PAGES = {
    "standings": {
        "path": "/team-standings",
        "defaults": {
            "standings-sort.data": {"column": "PTS", "direction": "desc"},
            "standings-view.data": "division",
        },
        "callbacks": [
            "..standings-league.options...standings-league.value..",
            "..standings-season.options...standings-season.value..",
            "standings-table.children",
        ],
        "api": ["/api/seasons", "/api/standings?league=AHL&season={season}"],
    },
    "player_stats": {
        "path": "/player-stats",
        "defaults": {
            "ps-situation.data": "tot",
            "ps-sort.data": {"column": "PTS", "direction": "desc"},
            "ps-page.data": 1,
        },
        "callbacks": [
            "..ps-league.options...ps-league.value..",
            "..ps-season.options...ps-season.value..",
            "..ps-table.children...ps-pagination.children..",
        ],
        "api": ["/api/seasons", "/api/player-stats?league=AHL&season={season}"],
    },
    "team_detail": {
        "path": "/team/{team}/{season}",
        "defaults": {
            "team-detail-situation.data": "tot",
            "team-detail-sort.data": {"column": "PTS", "direction": "desc"},
        },
        "callbacks": [
            "team-detail-id.data",
            "team-detail-breadcrumb.children",
            "team-detail-header.children",
            "..season-selector.options...season-selector.value..",
            "team-detail-table.children",
        ],
        "api": ["/api/teams/{team_abbr}/{season}"],
    },
    "player_detail": {
        "path": "/player/{player}",
        "defaults": {"player-detail-situation.data": "tot"},
        "callbacks": [
            "player-detail-id.data",
            "player-detail-breadcrumb.children",
            "player-detail-header.children",
            "player-detail-stats.children",
            "player-detail-game-log.children",
        ],
        "api": ["/api/players/{player_uuid}"],
    },
    "game_report": {
        "path": "/player/{player}/game/{game}",
        "defaults": {
            "game-report-situation.data": "tot",
            "game-report-stint-period.data": 1,
            "game-report-selected-stint.data": None,
        },
        "callbacks": [
            "..game-report-player-id.data...game-report-game-id.data...game-report-breadcrumb.children..",
            "game-report-header.children",
            "game-report-stats.children",
            "game-report-stints-header.children",
            "..game-report-stints.children...game-report-merged-stints.data..",
            "game-report-rink-base.data",
        ],
        "api": ["/api/games/{game_uuid}/players/{player_uuid}"],
    },
    # Clicking a shift: the shift table re-renders with it expanded, and the rink loads.
    "rink_shift": {
        "path": "/player/{player}/game/{game}",
        "defaults": {"game-report-stint-period.data": 1},
        "setup": [
            "..game-report-player-id.data...game-report-game-id.data...game-report-breadcrumb.children..",
            "..game-report-stints.children...game-report-merged-stints.data..",
        ],
        "select": {"game-report-selected-stint.data": "{first_stint_of_shift_3}"},
        "callbacks": [
            "..game-report-stints.children...game-report-merged-stints.data..",
            "..game-report-stint-events.data...game-report-frame-slider.max",
        ],
        "api": ["/api/games/{game_uuid}/players/{player_uuid}/shifts/3"],
    },
}

# Callbacks that only parse the URL; run for their outputs but not benchmarked.
NO_DATABASE = {"team-detail-id.data", "player-detail-id.data"}


def split_output(output: str) -> list[dict]:
    parts = output.strip(".").split("...") if output.startswith("..") else [output]
    return [dict(zip(("id", "property"), p.rsplit(".", 1))) for p in parts]


class DashClient:
    def __init__(self) -> None:
        self.deps = requests.get(f"{DASH}/_dash-dependencies", timeout=30).json()

    def find(self, prefix: str) -> dict:
        matches = [d for d in self.deps if d["output"].startswith(prefix)]
        assert len(matches) == 1, f"{prefix}: {len(matches)} callbacks"
        return matches[0]

    def run(self, prefix: str, ctx: dict) -> dict:
        dep = self.find(prefix)

        def value(i: dict) -> dict:
            key = f"{i['id']}.{i['property']}"
            return {"id": i["id"], "property": i["property"], "value": ctx.get(key)}

        outputs = split_output(dep["output"])
        body = {
            "output": dep["output"],
            "outputs": outputs if dep["output"].startswith("..") else outputs[0],
            "inputs": [value(i) for i in dep["inputs"]],
            "state": [value(s) for s in dep.get("state", [])],
            "changedPropIds": [
                f"{dep['inputs'][0]['id']}.{dep['inputs'][0]['property']}"
            ],
        }
        r = requests.post(f"{DASH}/_dash-update-component", json=body, timeout=60)
        r.raise_for_status()
        if r.status_code == 200:
            for component, props in r.json()["response"].items():
                for prop, v in props.items():
                    ctx[f"{component}.{prop}"] = v
        return {"url": f"{DASH}/_dash-update-component", "method": "POST", "body": body}


def main() -> None:
    e = entities()
    dash = DashClient()
    out = []
    for page, spec in PAGES.items():
        ctx = {"url.pathname": spec["path"].format(**e), **spec["defaults"]}
        for prefix in spec.get("setup", []):
            dash.run(prefix, ctx)
        for key, v in spec.get("select", {}).items():
            ctx[key] = int(v.format(**e))
        for prefix in spec["callbacks"]:
            request = dash.run(prefix, ctx)
            if prefix not in NO_DATABASE:
                out.append(
                    {"page": page, "side": "dash", "name": prefix.strip("."), **request}
                )
        for path in spec["api"]:
            url = f"{API}{path.format(**e)}"
            requests.get(url, timeout=30).raise_for_status()
            out.append(
                {
                    "page": page,
                    "side": "api",
                    "name": path.split("?")[0],
                    "url": url,
                    "method": "GET",
                }
            )
    json.dump(out, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
