#!/bin/bash
# Export the dbt marts from BigQuery to Parquet in GCS, where the Rust API reads them.
#
#   infra/export_serving.sh <dataset> <gcs_prefix>
#   CI, after the prod deploy: infra/export_serving.sh marts gs://snakepuck-data/serving/prod
#   Dev:                       infra/export_serving.sh dbt_dev_marts gs://snakepuck-data/serving/dev
#
# Layout under <gcs_prefix>:
#   marts/<table>/*.parquet       every mart except tracking, loaded at API startup
#   tracking/<game_id>.parquet    one file per game, loaded on demand
#
# Uses extract jobs, which are free (EXPORT DATA would bill the query, ~2.5 GB for tracking).
# Each table's old files are deleted just before its new ones land; the API only reads
# at startup, so a running instance is unaffected.
set -euo pipefail

PROJECT=snakepuck
LOCATION=us-central1
TRACKING=fct_tracking_snapshots
PYTHON=${PYTHON:-python}

DATASET=$1
PREFIX=${2%/}
TMP_GCS="$PREFIX/_tmp"
TMP_LOCAL=$(mktemp -d)
trap 'rm -rf "$TMP_LOCAL"' EXIT

bq_() { bq --headless --project_id="$PROJECT" --location="$LOCATION" "$@"; }

extract() { # <table> <gcs_dir>
  gcloud storage rm --quiet "$2/**" >/dev/null 2>&1 || true
  bq_ extract --destination_format=PARQUET --compression=ZSTD \
    "$DATASET.$1" "$2/*.parquet"
}

tables=$(bq_ ls --format=json --max_results=1000 "$DATASET" |
  "$PYTHON" -c "import json, sys; print(*(t['tableReference']['tableId'] for t in json.load(sys.stdin) if t['type'] == 'TABLE'))")

for table in $tables; do
  [[ $table == "$TRACKING" ]] && continue
  echo "Exporting $DATASET.$table"
  extract "$table" "$PREFIX/marts/$table"
done

echo "Exporting $DATASET.$TRACKING, split per game"
extract "$TRACKING" "$TMP_GCS/$TRACKING"
gcloud storage cp --quiet "$TMP_GCS/$TRACKING/*.parquet" "$TMP_LOCAL/"
"$PYTHON" "$(dirname "$0")/split_tracking.py" "$TMP_LOCAL" "$TMP_LOCAL/games"
gcloud storage rsync --quiet --recursive --delete-unmatched-destination-objects \
  "$TMP_LOCAL/games" "$PREFIX/tracking"
gcloud storage rm --quiet --recursive "$TMP_GCS" >/dev/null 2>&1
