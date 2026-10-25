# SnakePuck Migration Plan

A living plan. We migrate piece by piece, and the current Dash site keeps
working the whole time. Each phase ships on its own and can be reordered,
reshaped, or dropped as we learn.

## Target architecture

```
raw Parquet ──► GCS ──► BigQuery (raw)
                          │
                          ▼
                 dbt: staging → intermediate → marts  (tested against BigQuery `golden`)
                          │
                          ▼
              export marts to Parquet (GCS)
                          │
                          ▼
        Rust API (Axum) on Cloud Run, marts held in memory
                          │
                          ▼
          Leptos frontend (Rust → WASM) + Markdown blog
```

Rust also takes on tracking-frame processing where SQL is awkward
(possession chains, pressure metrics). It is benchmarked against Python.

## Hosting (all GCP)

The API and frontend are a single Rust app (Axum + Leptos server rendering),
deployed as one Cloud Run service.

```
domain ──► Firebase Hosting (free HTTPS + CDN) ──► Cloud Run: Rust app
                                                       │
                                                       ▼
                                          GCS: mart + tracking Parquet
```

| Need | Service |
|---|---|
| Run the app | Cloud Run (scale to zero; min-instances=1 optional) |
| Container images | Artifact Registry |
| CI/CD | GitHub Actions (or Cloud Build) |
| Served data files | Cloud Storage |
| Warehouse + transforms | BigQuery + dbt |
| Domain, HTTPS, edge cache | Firebase Hosting rewrites → Cloud Run |

## Estimated cost (verify against current GCP pricing)

| Scenario | Est. monthly |
|---|---|
| Scale to zero, blog-level traffic | ~$0–2 (BigQuery, Cloud Run, Firebase all within free tiers) |
| One always-warm Cloud Run instance | ~$10–20 |
| Today, for comparison (DigitalOcean app + managed Postgres) | ~$20–30+ |

Guardrails: a $10/month budget alert, a BigQuery maximum-bytes-billed limit per
query, and a daily query quota. Both platforms run in parallel until the
Phase 7 cutover.

## Repo layout (decided: one repo)

GitHub repo: `cutterbuck/snakepuck`, renamed from `hockey-blog` on 2026-10-23.
The DigitalOcean source was repointed. The local folder is still `hockey-blog`.

New pieces are added beside the Dash app, and Phase 7 deletes the old ones.
CI workflows filter by path, so each stack only builds when its folder changes.

```
app/ run.py migrations/ scripts/   current Dash site (removed in Phase 7)
tests/                             Python tests (Dash + golden reconciliation)
content/blog/                      Markdown posts, shared by old and new site
infra/                             GCP setup notes + BigQuery load script (Phase 2)
dbt/                               dbt project (Phase 3)
site/                              Rust crate: Axum API + Leptos frontend (Phases 4–5)
docs/                              this plan
```

## Where things live today

| Piece | Today | Size |
|---|---|---|
| Raw data | `data/*.parquet` → Postgres via `scripts/seed_db.py` | tracking 13.5M, stints 2.2M, events 1.8M rows |
| Derived stats | `scripts/seed_db.py` (~1,500 lines) + ~20 `backfill_*`/`migrate_*` scripts | shifts, stint xG/GAP, situations, player/game/team stats |
| Serving | Dash callbacks querying Postgres directly | 9 callback modules |
| Blog | Markdown strings inside `scripts/seed_blog_posts.py` → `blog_posts` table | 1 post |
| Hosting | DigitalOcean (gunicorn) + Postgres | |
| Tests / CI | none | |

---

## Phase 0 — Safety net
*Goal: lock in today's numbers so every later phase can prove it matches them.*

- [x] Pin dependencies: `requirements.txt` is an exact lock; direct deps are in `requirements.in`
- [x] Snapshot "golden" outputs from Postgres to Parquet (`python -m scripts.export_golden`):
      `player_stats`, `player_game_stats`, `team_stats`, and all 2.2M `stints`, keyed by
      natural keys rather than Postgres ids. `golden/manifest.json` records row counts and column sums.
- [x] pytest: no-DB smoke tests, plus `db`-marked tests driving each page's callbacks
- [x] GitHub Actions: ruff check, ruff format, and pytest (db tests skip in CI)

**Done when:** CI is green and the golden snapshots are stored safely.
Snapshots are git-ignored (the repo is public and they derive from licensed HALO data).
They live locally until Phase 2 moves them to a private GCS bucket.

## Phase 1 — Blog posts as Markdown
*Goal: posts are files you write in an editor, not database rows. Small and independent.*

- [x] `content/blog/<slug>.md` with YAML front matter (title, date, summary, optional `draft: true`)
- [x] Move "The Consequences of Randomness in Hockey" out of `seed_blog_posts.py`
      (verified identical to the database copy)
- [x] Dash blog pages read the files via `app/blog.py`; removed the `BlogPost` model,
      seed script, and the `post_deploy.sh` seeding step. The `blog_posts` table is
      left in place, unused, to avoid a production schema change; it goes away with
      Postgres in Phase 7.
- [x] Draft moved to `content/blog/dzone-lpr-analysis.md` with `draft: true`.
      Drafts are hidden unless `SHOW_DRAFTS=1` (local preview only).

**Writing a post:** add `content/blog/<slug>.md`, preview with
`SHOW_DRAFTS=1 python run.py` while it's a draft, then remove `draft: true`, commit, and push.

**Done when:** the live blog renders from Markdown. The same files carry over to Leptos unchanged.

## Phase 2 — GCP foundation + raw data in BigQuery
*Setup commands are recorded in `infra/README.md`.*

- [x] GCP project `snakepuck` (us-central1), $10/month budget alert,
      keyless service account `snakepuck-pipeline`
- [x] BigQuery cost guardrails: 50 GiB/day query quota (project and per user, down
      from the 200 TiB default); 5 GB maximum bytes billed per query
- [x] Private GCS bucket `gs://snakepuck-data`; uploaded the 5 raw Parquet files and the `golden/` snapshots
- [x] BigQuery datasets `raw` and `golden`, loaded by `infra/load_raw.sh`. Tables are clustered
      by `game_id` rather than partitioned (it's a string, and the tables are too small to benefit).
- [ ] (Optional) Terraform for the above

**Done when:** `raw.tracking` etc. are queryable and row counts match Postgres.
All 9 tables match Postgres exactly (2026-10-25).

## Phase 3 — dbt rebuilds the pipeline
*Goal: replace `seed_db.py` and the backfill scripts with tested SQL models. This is the core data-engineering showcase.*

- [ ] dbt project (`dbt-bigquery`) with `staging` / `intermediate` / `marts` layers
- [ ] Staging: typed, cleaned views over each raw table
- [ ] Intermediate: shift numbering, stint xG attribution, GAP, game situations (5v5, PP, PK…)
- [ ] Marts: `player_stats`, `player_game_stats`, `team_stats`, standings, game-report tables
- [ ] dbt tests: uniqueness, not-null, relationships, accepted values, plus
      **reconciliation tests against Phase 0 golden snapshots**
- [ ] dbt docs (lineage graph) published

**Done when:** every mart matches the golden numbers (or every difference is explained as a bug fix).

## Phase 4 — Serving layer: marts → Parquet → Rust API
- [ ] Export marts to Parquet in GCS (BigQuery `EXPORT DATA`), triggered after dbt runs
- [ ] Rust (Axum) API: load marts into memory at startup; JSON endpoints per page
- [ ] Tracking for the rink: per-game files loaded on demand, not all 13.5M rows held in memory
- [ ] `cargo test` + endpoint tests; deploy to Cloud Run
- [ ] Benchmark latency and memory vs the Dash/Postgres path; publish the numbers

**Done when:** the API serves every dataset the site needs, with published benchmarks.

## Phase 5 — Leptos frontend, page by page
- [ ] Leptos app shell (navbar, footer, routing, SnakePuck styling)
- [ ] Port pages roughly in order of simplicity: About → Blog → Standings →
      Player Stats → Team Detail → Player Detail → Game Report (rink last)
- [ ] Pages not yet ported link back to the Dash site during the transition
- [ ] Playwright smoke tests per page

**Done when:** every page is served by Leptos.

## Phase 6 — Rust tracking processing *(as needed)*
- [ ] Identify logic that SQL handles poorly (possession chains, pressure/LPR metrics)
- [ ] Implement in Rust over Arrow/Polars; write results to BigQuery for dbt
- [ ] Benchmark vs the Python equivalent

## Phase 7 — Decommission
- [ ] Retire Dash, Postgres, DigitalOcean
- [ ] Delete superseded scripts
- [ ] README with architecture diagram, benchmarks, and live link

---

## Open decisions
- **Tracking in the API:** per-game Parquet on GCS vs bundled in the container image
- **Infrastructure as code:** Terraform now, or click-ops first and codify later?
- **Domain/hosting cutover:** when to point the live domain at Firebase Hosting / Cloud Run
- **Cold starts:** scale to zero ($0) vs one always-warm instance (~$10–15) during job applications

## Deferred
- Smooth player animation on the rink. HALO tracking is per-event snapshots,
  not continuous frames. Revisit only with frame-level data.
- Re-enabling login (code kept, commented out)
- Robustness items (SECRET_KEY fallback, routing refactor, caching) are superseded by the rewrite
