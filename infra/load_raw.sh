#!/bin/bash
# Load raw HALO Parquet and Phase 0 golden snapshots from GCS into BigQuery.
# Re-runnable: each load replaces its table. Upload first with:
#   gcloud storage cp data/*.parquet gs://snakepuck-data/raw/
#   gcloud storage cp golden/* gs://snakepuck-data/golden/
# golden/defense_lpr.parquet comes from scripts/export_golden_defense_lpr.py (Phase 4).
set -euo pipefail

PROJECT=snakepuck
LOCATION=us-central1
BUCKET=gs://snakepuck-data

# game_id is a string, so tables are clustered (not partitioned) by it.
# They are also well under the size where partitioning pays off.
TABLES=(
  "raw games"
  "raw players"
  "raw events game_id,sl_event_id"
  "raw stints game_id,player_id"
  "raw tracking game_id,sl_event_id"
  "golden player_stats"
  "golden player_game_stats game_id,player_id"
  "golden team_stats"
  "golden stints game_id,player_id"
  "golden defense_lpr"
)

for dataset in raw golden; do
  bq --project_id="$PROJECT" show "$dataset" >/dev/null 2>&1 ||
    bq --project_id="$PROJECT" mk --location="$LOCATION" --dataset "$dataset"
done

for spec in "${TABLES[@]}"; do
  read -r dataset table cluster <<<"$spec"
  echo "Loading $dataset.$table"
  bq --headless --project_id="$PROJECT" --location="$LOCATION" load \
    --replace \
    --source_format=PARQUET \
    ${cluster:+--clustering_fields="$cluster"} \
    "$dataset.$table" "$BUCKET/$dataset/$table.parquet"
done
