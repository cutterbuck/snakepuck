# GCP setup (Phase 2)

One-time setup for project `snakepuck`, recorded so it can be codified in
Terraform later. Everything lives in `us-central1`.

## Cost guardrails

```bash
# $10/month budget: email at 50%, 90%, 100% actual and 100% forecast (alerts only)
gcloud billing budgets create --billing-account=<BILLING_ACCOUNT> \
  --display-name="snakepuck monthly" --budget-amount=10USD \
  --filter-projects=projects/snakepuck --calendar-period=month \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0 --threshold-rule=percent=1.0,basis=forecasted-spend

# Hard cap: BigQuery query usage 50 GiB/day, per project and per user (default was 200 TiB/day)
for q in QueryUsagePerDay QueryUsagePerUserPerDay; do
  gcloud beta quotas preferences create --service=bigquery.googleapis.com \
    --project=snakepuck --quota-id=$q --preferred-value=51200 \
    --allow-high-percentage-quota-decrease
done
```

Per-query cap: `~/.bigqueryrc` sets `--maximum_bytes_billed=5000000000` (5 GB)
for the `bq` CLI. dbt sets `maximum_bytes_billed` in its profile (Phase 3).
For scale, a full scan of `raw.tracking` is about 2 GB.

## Storage and identity

```bash
gcloud storage buckets create gs://snakepuck-data --location=us-central1 \
  --uniform-bucket-level-access --public-access-prevention

# Keyless service account for the pipeline, Cloud Run, and CI
gcloud iam service-accounts create snakepuck-pipeline --display-name="SnakePuck data pipeline"
SA=serviceAccount:snakepuck-pipeline@snakepuck.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding snakepuck --member=$SA --role=roles/bigquery.jobUser
gcloud projects add-iam-policy-binding snakepuck --member=$SA --role=roles/bigquery.dataEditor
gcloud storage buckets add-iam-policy-binding gs://snakepuck-data --member=$SA --role=roles/storage.objectAdmin
```

The bucket holds licensed HALO data and must stay private. Never commit
anything from it to this public repo.

## Loading data

```bash
gcloud storage cp data/*.parquet gs://snakepuck-data/raw/
gcloud storage cp golden/* gs://snakepuck-data/golden/
./infra/load_raw.sh
```

| Table | Rows | Clustered by |
|---|---|---|
| `raw.games` | 480 | |
| `raw.players` | 1,172 | |
| `raw.events` | 1,800,464 | game_id, sl_event_id |
| `raw.stints` | 2,212,064 | game_id, player_id |
| `raw.tracking` | 13,529,224 | game_id, sl_event_id |
| `golden.player_stats` | 1,232 | |
| `golden.player_game_stats` | 18,279 | game_id, player_id |
| `golden.team_stats` | 32 | |
| `golden.stints` | 2,212,064 | game_id, player_id |

Row counts match Postgres exactly (checked 2026-10-25).
Tables are clustered rather than partitioned: `game_id` is a string, and every
table is far below the size where partitioning pays off.
