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

Temporarily raised to 200 GiB/day (2026-10-26) for the Phases 3–5 build-out, and
lowered back to 50 GiB on 2026-10-28 with the command below. No override flag is needed
going up. Going down from 200 GiB to 50 GiB needs `--allow-high-percentage-quota-decrease`,
and the per-project cap also needed `--allow-quota-decrease-below-usage`, since recent
usage was above 50 GiB:

```bash
for p in query-usage-per-day-50gib:QueryUsagePerDay query-usage-per-user-per-day-50gib:QueryUsagePerUserPerDay; do
  gcloud beta quotas preferences update ${p%%:*} --service=bigquery.googleapis.com \
    --project=snakepuck --quota-id=${p##*:} --preferred-value=51200 \
    --allow-high-percentage-quota-decrease --allow-quota-decrease-below-usage
done
```

Per-query cap: `~/.bigqueryrc` sets `--maximum_bytes_billed=5000000000` (5 GB)
for the `bq` CLI. dbt sets `maximum_bytes_billed` in its profile (Phase 3).
For scale, a full scan of `raw.tracking` is about 2 GB.

## Storage and identity

```bash
gcloud storage buckets create gs://snakepuck-data --location=us-central1 \
  --uniform-bucket-level-access --public-access-prevention

# Keyless service account for the pipeline and CI (Cloud Run runs as snakepuck-api, below)
gcloud iam service-accounts create snakepuck-pipeline --display-name="SnakePuck data pipeline"
SA=serviceAccount:snakepuck-pipeline@snakepuck.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding snakepuck --member=$SA --role=roles/bigquery.jobUser
gcloud projects add-iam-policy-binding snakepuck --member=$SA --role=roles/bigquery.dataEditor
gcloud storage buckets add-iam-policy-binding gs://snakepuck-data --member=$SA --role=roles/storage.objectAdmin
```

The bucket holds licensed HALO data and must stay private. Never commit
anything from it to this public repo.

## GitHub Actions auth (Phase 3)

Workflows authenticate as `snakepuck-pipeline` with no stored key, through Workload
Identity Federation. Only this repository's `main` branch is accepted. This was set up
in Phase 3 and is recorded here from the live configuration:

```bash
gcloud iam workload-identity-pools create github --location=global
gcloud iam workload-identity-pools providers create-oidc snakepuck-repo \
  --location=global --workload-identity-pool=github \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping=google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_id=assertion.repository_id,attribute.ref=assertion.ref \
  --attribute-condition="assertion.repository_id == '1150873071' && assertion.ref == 'refs/heads/main'"
gcloud iam service-accounts add-iam-policy-binding snakepuck-pipeline@snakepuck.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member=principalSet://iam.googleapis.com/projects/65985276875/locations/global/workloadIdentityPools/github/attribute.repository_id/1150873071
```

## Cloud Run API (Phase 4)

The API (`site/`) runs as its own service account, which can only read the bucket.
The service itself is defined in `site/service.yaml`. It mounts the bucket read-only
with only `serving/prod` visible. `.github/workflows/site.yml` builds the image and
applies that file on every push to `main`.

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
gcloud artifacts repositories create snakepuck --repository-format=docker --location=us-central1
# Keep the 5 newest images; delete the rest after a day
gcloud artifacts repositories set-cleanup-policies snakepuck --location=us-central1 --no-dry-run \
  --policy=<(echo '[{"name":"keep-recent","action":{"type":"Keep"},"mostRecentVersions":{"keepCount":5}},
                    {"name":"delete-old","action":{"type":"Delete"},"condition":{"tagState":"any","olderThan":"1d"}}]')

gcloud iam service-accounts create snakepuck-api --display-name="SnakePuck API (Cloud Run runtime)"
API=serviceAccount:snakepuck-api@snakepuck.iam.gserviceaccount.com
gcloud storage buckets add-iam-policy-binding gs://snakepuck-data --member=$API --role=roles/storage.objectViewer

# CI pushes images, deploys revisions, and runs them as snakepuck-api
CI=serviceAccount:snakepuck-pipeline@snakepuck.iam.gserviceaccount.com
gcloud artifacts repositories add-iam-policy-binding snakepuck --location=us-central1 --member=$CI --role=roles/artifactregistry.writer
gcloud projects add-iam-policy-binding snakepuck --member=$CI --role=roles/run.developer
gcloud iam service-accounts add-iam-policy-binding snakepuck-api@snakepuck.iam.gserviceaccount.com --member=$CI --role=roles/iam.serviceAccountUser

# Once, after the first deploy: make the API public. CI can't change IAM (run.developer).
gcloud run services add-iam-policy-binding snakepuck-api --region=us-central1 --member=allUsers --role=roles/run.invoker
```

## Firebase Hosting and snakepuck.com (Phase 5)

Firebase Hosting serves the domain with free HTTPS and forwards every request to the
Cloud Run service. Its config is in `infra/firebase/`: `firebase.json` rewrites `**` to
`snakepuck-api`, and `public/` is deliberately empty. The Firebase CLI works with the
gcloud application-default login, so no `firebase login` is needed.

```bash
npx -y firebase-tools@latest projects:addfirebase snakepuck   # once (2026-10-28)
cd infra/firebase && npx -y firebase-tools@latest deploy --only hosting --project snakepuck
```

The deploy only needs repeating if `infra/firebase/` changes; site deploys go to Cloud Run
(`site.yml`). Without the custom domain the site is at https://snakepuck.web.app.

**X-Forwarded-For through Firebase** (measured 2026-10-28 with
`RUST_LOG=snakepuck::server::limit=debug`): Firebase drops whatever the client sent and
the app sees `"<client>, <Firebase edge>"`, so `TRUSTED_PROXY_HOPS` is 1 in
`site/service.yaml`. Requests straight to the run.app URL arrive as
`"<anything the client sent>, <client>"`, so callers there can choose their rate-limit
key. Cloud Run's 2-instance cap bounds the cost.

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
