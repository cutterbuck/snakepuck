"""Export the dbt marts from BigQuery to Parquet in GCS, where the Rust API reads them.

    python infra/export_serving.py <dataset> <gcs_prefix>
    CI, after the prod deploy: python infra/export_serving.py marts gs://snakepuck-data/serving/prod
    Dev:                       python infra/export_serving.py dbt_dev_marts gs://snakepuck-data/serving/dev

Layout under <gcs_prefix>:
    marts/<table>/*.parquet               small marts, loaded at API startup
    games/<table>/<game_id>.parquet       large per-game marts (PER_GAME), loaded on demand
    samples/<name>.parquet                fixed 100-row samples (SAMPLES) for the Sample Data page

Uses extract jobs, which are free (EXPORT DATA would bill the query, ~2.5 GB for
tracking). Each table's old files are deleted just before its new ones land; the
API only reads at startup, so a running instance is unaffected.

Uses the BigQuery and Storage clients that dbt-bigquery installs, authenticated by
Application Default Credentials (the same credentials dbt uses, locally and in CI).
"""

import random
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from google.cloud import bigquery, storage

PROJECT = "snakepuck"
LOCATION = "us-central1"

# Too large to hold in the API's memory; a page only ever needs one game.
# Table -> sort order within each game's file.
PER_GAME = {
    "fct_game_events": ["sl_event_id"],
    "fct_shifts": ["player_id", "shift"],
    "fct_stints": ["game_stint", "player_id"],
    "fct_tracking_snapshots": ["sl_event_id"],
}

# Sample Data page: name -> (mart, columns shown).
SAMPLES = {
    "players": (
        "dim_players",
        [
            "player_id",
            "first_name",
            "last_name",
            "handed",
            "birth_date",
            "position_group",
            "primary_position",
        ],
    ),
    "games": (
        "dim_games",
        [
            "game_id",
            "game_date",
            "league",
            "season",
            "home_team_abbr",
            "away_team_abbr",
            "home_score",
            "away_score",
            "game_outcome",
            "home_start_net",
        ],
    ),
    "stints": (
        "fct_stints",
        [
            "game_id",
            "player_id",
            "team_abbr",
            "period",
            "period_time_start",
            "period_time_end",
            "game_stint",
            "n_home_skaters",
            "n_away_skaters",
            "is_home_net_empty",
            "is_away_net_empty",
            "home_score",
            "away_score",
        ],
    ),
    "events": (
        "fct_game_events",
        [
            "game_id",
            "player_id",
            "period",
            "period_time",
            "event_type",
            "outcome",
            "flags",
            "team_abbr",
            "opp_team_abbr",
            "description",
            "detail",
            "xg",
            "x",
            "y",
        ],
    ),
    "tracking": (
        "fct_tracking_snapshots",
        [
            "game_id",
            "sl_event_id",
            "team_abbr",
            "player_id",
            "display_name",
            "tracking_x",
            "tracking_y",
            "tracking_vel_x",
            "tracking_vel_y",
        ],
    ),
}
SAMPLE_ROWS = 100


def main(dataset: str, gcs_prefix: str) -> None:
    bucket_name, _, prefix = gcs_prefix.removeprefix("gs://").rstrip("/").partition("/")
    bq = bigquery.Client(project=PROJECT, location=LOCATION)
    bucket = storage.Client(project=PROJECT).bucket(bucket_name)

    def extract(table: str, path: str) -> bigquery.ExtractJob:
        bucket.delete_blobs(list(bucket.list_blobs(prefix=f"{path}/")))
        return bq.extract_table(
            f"{PROJECT}.{dataset}.{table}",
            f"gs://{bucket_name}/{path}/*.parquet",
            job_config=bigquery.ExtractJobConfig(
                destination_format="PARQUET", compression="ZSTD"
            ),
        )

    def tmp(table: str) -> str:
        return f"{prefix}/_tmp/{table}"

    tables = [t.table_id for t in bq.list_tables(dataset) if t.table_type == "TABLE"]
    jobs = {
        t: extract(t, tmp(t) if t in PER_GAME else f"{prefix}/marts/{t}")
        for t in tables
    }
    for table, job in jobs.items():
        job.result()
        print(f"Exported {dataset}.{table}")

    for table, sort in PER_GAME.items():
        full = split_per_game(bucket, tmp(table), f"{prefix}/games/{table}", sort)
        write_samples(bucket, prefix, table, full)
        del full
    for table in {mart for mart, _ in SAMPLES.values()} - PER_GAME.keys():
        write_samples(
            bucket, prefix, table, read_blobs(bucket, f"{prefix}/marts/{table}")
        )

    # Remove files left by tables that were dropped or moved to games/.
    current = tuple(f"{prefix}/marts/{t}/" for t in tables if t not in PER_GAME)
    leftover = [
        b
        for b in bucket.list_blobs(prefix=f"{prefix}/marts/")
        if not b.name.startswith(current)
    ]
    bucket.delete_blobs(leftover)
    print(f"Removed {len(leftover)} leftover mart files")


def read_blobs(bucket: storage.Bucket, path: str) -> pa.Table:
    with tempfile.TemporaryDirectory() as local:
        paths = []
        for blob in bucket.list_blobs(prefix=f"{path}/"):
            paths.append(Path(local) / Path(blob.name).name)
            blob.download_to_filename(paths[-1])
        return pq.read_table(paths)


def write_samples(
    bucket: storage.Bucket, prefix: str, mart: str, table: pa.Table
) -> None:
    """Write a fixed random sample of `table` for each SAMPLES entry drawn from `mart`."""
    for name, (source, columns) in SAMPLES.items():
        if source != mart:
            continue
        rows = sorted(random.Random(0).sample(range(table.num_rows), SAMPLE_ROWS))
        with tempfile.NamedTemporaryFile(suffix=".parquet") as f:
            pq.write_table(table.select(columns).take(rows), f.name, compression="zstd")
            bucket.blob(f"{prefix}/samples/{name}.parquet").upload_from_filename(f.name)
        print(f"Wrote sample {name} from {mart}")


def split_per_game(
    bucket: storage.Bucket, src: str, dest: str, sort: list[str]
) -> pa.Table:
    """Replace dest/ with one file per game from the shards under src/, then delete src/.

    Returns the whole table, sorted.
    """
    with tempfile.TemporaryDirectory() as local:
        shards = list(bucket.list_blobs(prefix=f"{src}/"))
        paths = [Path(local) / Path(b.name).name for b in shards]
        with ThreadPoolExecutor(16) as pool:
            list(pool.map(lambda b, p: b.download_to_filename(p), shards, paths))
        table = pq.read_table(paths)
        table = table.sort_by([(c, "ascending") for c in ["game_id", *sort]])
        games = write_games(table, Path(local) / "games")

        names = {g.name for g in games}
        stale = [
            b
            for b in bucket.list_blobs(prefix=f"{dest}/")
            if Path(b.name).name not in names
        ]
        with ThreadPoolExecutor(16) as pool:
            list(
                pool.map(
                    lambda g: bucket.blob(f"{dest}/{g.name}").upload_from_filename(g),
                    games,
                )
            )
        bucket.delete_blobs(stale + shards)
    print(f"Wrote {dest}: {len(games)} games, removed {len(stale)} stale")
    return table


def write_games(table: pa.Table, out_dir: Path) -> list[Path]:
    """Write one Parquet file per game from `table`, which is sorted by game_id."""
    # After sorting, each game is one contiguous run of rows.
    runs = pc.run_end_encode(table["game_id"].combine_chunks())
    out_dir.mkdir()
    games, start = [], 0
    for game_id, end in zip(runs.values.to_pylist(), runs.run_ends.to_pylist()):
        games.append(out_dir / f"{game_id}.parquet")
        pq.write_table(table.slice(start, end - start), games[-1], compression="zstd")
        start = end
    return games


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
