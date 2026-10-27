"""Export the dbt marts from BigQuery to Parquet in GCS, where the Rust API reads them.

    python infra/export_serving.py <dataset> <gcs_prefix>
    CI, after the prod deploy: python infra/export_serving.py marts gs://snakepuck-data/serving/prod
    Dev:                       python infra/export_serving.py dbt_dev_marts gs://snakepuck-data/serving/dev

Layout under <gcs_prefix>:
    marts/<table>/*.parquet               small marts, loaded at API startup
    games/<table>/<game_id>.parquet       large per-game marts (PER_GAME), loaded on demand

Uses extract jobs, which are free (EXPORT DATA would bill the query, ~2.5 GB for
tracking). Each table's old files are deleted just before its new ones land; the
API only reads at startup, so a running instance is unaffected.

Uses the BigQuery and Storage clients that dbt-bigquery installs, authenticated by
Application Default Credentials (the same credentials dbt uses, locally and in CI).
"""

import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq
from google.cloud import bigquery, storage

PROJECT = "snakepuck"
LOCATION = "us-central1"

# Too large to hold in the API's memory; a page only ever needs one game.
# Table -> sort order within each game's file.
PER_GAME = {
    "fct_game_events": ["sl_event_id"],
    "fct_stints": ["game_stint", "player_id"],
    "fct_tracking_snapshots": ["sl_event_id"],
}


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
        split_per_game(bucket, tmp(table), f"{prefix}/games/{table}", sort)


def split_per_game(
    bucket: storage.Bucket, src: str, dest: str, sort: list[str]
) -> None:
    """Replace dest/ with one file per game from the shards under src/, then delete src/."""
    with tempfile.TemporaryDirectory() as local:
        shards = list(bucket.list_blobs(prefix=f"{src}/"))
        paths = [Path(local) / Path(b.name).name for b in shards]
        with ThreadPoolExecutor(16) as pool:
            list(pool.map(lambda b, p: b.download_to_filename(p), shards, paths))
        games = write_games(paths, Path(local) / "games", sort)

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


def write_games(paths: list[Path], out_dir: Path, sort: list[str]) -> list[Path]:
    """Write one Parquet file per game, rows in `sort` order."""
    table = pq.read_table(paths)
    table = table.sort_by([(c, "ascending") for c in ["game_id", *sort]])

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
