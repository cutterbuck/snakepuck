"""Snapshot the Player Analysis page's defensemen LPR table, for every dropdown view,
as the Dash site displays it. It's the answer key for dbt's fct_defense_lpr.

The page computes these per request (no table holds them), so the snapshot drives the
real callback through Flask's test client against the local database and reads the
rendered table. Values are as displayed, rounded: averages to 3 decimals, totals to
2, percentages to 1. They're stored in the mart's units, so percentages become
fractions.

Usage:
    python -m scripts.export_golden_defense_lpr [output_dir]   # default: golden/
"""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from app import create_app
from app.config import Config

VIEWS = ["low", "high", "high_next_success", "high_next_failure", "high_next_rate"]


def render(client, view: str) -> list[list]:
    """The table's body rows for one view, as cell values, without the Total row."""
    body = {
        "output": "player-analysis-dmen-lpr.children",
        "outputs": {"id": "player-analysis-dmen-lpr", "property": "children"},
        "inputs": [
            {"id": "url", "property": "pathname", "value": "/player-analysis"},
            {
                "id": "pa-lpr-sort",
                "property": "data",
                "value": {"column": "xG%", "direction": "desc"},
            },
            {"id": "pa-dmen-lpr-dropdown", "property": "value", "value": view},
        ],
        "state": [],
        "changedPropIds": ["pa-dmen-lpr-dropdown.value"],
    }
    response = client.post("/_dash-update-component", json=body)
    assert response.status_code == 200, (view, response.status_code)
    table = response.json["response"]["player-analysis-dmen-lpr"]["children"]
    _, tbody = table["props"]["children"]
    rows = [
        [td["props"]["children"] for td in tr["props"]["children"]]
        for tr in tbody["props"]["children"]
    ]
    assert rows[0][0] == "Total", rows[0]
    return rows[1:]


def pct(cell: str) -> float:
    return round(float(cell.rstrip("%")) / 100, 4)


def export(out_dir: Path) -> None:
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    with engine.connect() as db:
        defensemen = db.execute(
            text(
                """select "playerId", "firstName" || ' ' || "lastName" from players
                where position = 'D'"""
            )
        ).all()
    ids_by_name: dict[str, list[str]] = {}
    for player_id, name in defensemen:
        ids_by_name.setdefault(name, []).append(player_id)

    client = create_app().test_client()
    records = []
    for view in VIEWS:
        for row in render(client, view):
            ids = ids_by_name.get(row[0], [])
            assert len(ids) == 1, f"{view}: {row[0]!r} matches {len(ids)} defensemen"
            record = {"player_id": ids[0], "view": view, "games_played": int(row[1])}
            if view == "high_next_rate":
                successes, failures = int(row[2]), int(row[3])
                record |= {
                    "lpr_count": successes + failures,
                    "successes": successes,
                    "failures": failures,
                    "success_rate": pct(row[4]),
                }
            else:
                record |= {
                    "lpr_count": int(row[2]),
                    "avg_oi_xgf": float(row[3]),
                    "avg_oi_xga": float(row[4]),
                    "total_oi_xgf": float(row[5]),
                    "total_oi_xga": float(row[6]),
                    "xg_pct": pct(row[7]),
                }
            records.append(record)
        print(f"{view}: {sum(r['view'] == view for r in records)} defensemen")

    df = pd.DataFrame.from_records(records).sort_values(["view", "player_id"])
    for column in ("successes", "failures"):
        df[column] = df[column].astype("Int64")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "defense_lpr.parquet"
    df.to_parquet(path, index=False)
    print(f"defense_lpr: {len(df)} rows -> {path}")


if __name__ == "__main__":
    export(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("golden"))
