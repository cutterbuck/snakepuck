"""Split the exported tracking table into one Parquet file per game.

    python infra/split_tracking.py <export_dir> <out_dir>

Reads every *.parquet in export_dir (the shards from `bq extract`) and writes
out_dir/<game_id>.parquet, rows ordered by sl_event_id. Called by export_serving.sh.
"""

import sys
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq


def main(export_dir: Path, out_dir: Path) -> None:
    table = pq.read_table(sorted(export_dir.glob("*.parquet")))
    table = table.sort_by([("game_id", "ascending"), ("sl_event_id", "ascending")])

    # After sorting, each game is one contiguous run of rows.
    runs = pc.run_end_encode(table["game_id"].combine_chunks())
    out_dir.mkdir(parents=True, exist_ok=True)
    start = 0
    for game_id, end in zip(runs.values.to_pylist(), runs.run_ends.to_pylist()):
        pq.write_table(
            table.slice(start, end - start),
            out_dir / f"{game_id}.parquet",
            compression="zstd",
        )
        start = end
    print(f"Wrote {len(runs.values)} games, {table.num_rows:,} rows")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
