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
bench/                             Dash vs Rust API benchmark scripts (Phase 4)
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

- [x] dbt project (`dbt/`, dbt 1.12) with `staging` / `intermediate` / `marts` layers.
      Run from `dbt/`: `dbt deps && dbt build` (dev → `dbt_dev_*` datasets; `--target prod` → `staging`, `marts`, ...).
      Per-query cap of 5 GB in `profiles.yml`.
- [x] Staging: typed, renamed views over each raw table, plus an `ahl_teams` seed
      (names, logos, divisions formerly hard-coded in `seed_db.py`). 34 tests on keys, nulls,
      relationships, and accepted values; all pass. Event key is `(game_id, sl_event_id)`.
- [x] CI: `.github/workflows/dbt.yml` runs on pushes to main that touch `dbt/`. Keyless auth
      via Workload Identity Federation (pool `github`, trusting only repo ID 1150873071 on
      `refs/heads/main`). Slim CI: builds and tests only what changed (`state:modified+`)
      in `dbt_ci_*` with `--defer` to prod, then deploys the same selection to prod and saves
      the manifest to `gs://snakepuck-data/dbt-state/prod/`. Manual runs can rebuild
      everything or re-prove legacy parity.
- [x] Build cost: about 5 GiB for a full build. `store_failures` is limited to the golden
      tests, because it turns `not_null`/`unique` into `select *` scans.
- [x] Intermediate: `int_stints__enriched` (situations, TOI, shift numbers) and
      `int_stints__event_stats` (events credited to each stint's time window)
- [x] Marts: `fct_stints`, `fct_player_game_stats`, `fct_player_season_stats`, `fct_team_season_stats`
- [x] dbt tests: uniqueness, not-null, relationships, accepted values, plus a
      `matches_golden` reconciliation test (every row and column, one scan per table)
- [x] **Parity reached (2026-10-25):** all four marts match golden exactly. The only
      tolerance is ±0.1 on one-decimal ATOI, where exact ties round differently with
      Python's vs BigQuery's summation order.
- [x] Fixed the old pipeline's bugs (below). `dbt build --vars 'legacy_parity: true'`
      still reproduces the old numbers and runs the golden reconciliation, so parity
      can be re-proven at any time. The default build applies the fixes and tests them.
- [x] Game-report tables for the rink: `fct_game_events`, `fct_tracking_snapshots`
      (display names and team resolved, including "Unidentified (team)"), `fct_shifts`
- [x] dbt docs (lineage graph) built by CI and published to GitHub Pages

**Bugs found in the old pipeline (fixed 2026-10-25):**
1. *Boundary plays uncredited.* The old pipeline matched events to stints by time
   window `[start, end)`. Plays at the exact instant a stint ends, which HALO itself
   leaves unassigned, were credited to no one: 6 goals, 19 shots.
   **Fix:** credit events to the stint HALO assigned them (`events.game_stint`, which
   follows the true order of plays and agrees with the window everywhere else). Fall
   back to the stint ending at that moment for unassigned plays.
   **Effect vs the live site:** 6 players +1 goal; 15 player-seasons gain shots; the
   on-ice xG of those 19 shots moves to the line that was on the ice (432 stints).
   One faceoff remains uncredited: its player isn't in any stint at that time (data glitch).
2. *Quiet games dropped.* A player-game row existed only if the player recorded an
   event, and season totals summed those rows. Games with no events still counted in
   GP but lost their TOI and on-ice xG.
   **Fix:** game rows come from stints. **Effect:** 2 goalie games added; those
   goalies' ATOI rises about 30 seconds.

3. *Shifts spanning periods.* Shift numbering linked a stint to the player's next one
   whenever one's end time equalled the other's start time, ignoring the period. Once in
   the season, a 1st-period stint ending at 2:19.03 was merged with a 3rd-period stint
   starting at 2:19.03. **Fix:** the period must match too.

Checked and *not* a bug: HALO's team-level goal rows sit at the end of the ending
stint, but every player-credited goal and assist lands in the same stint, and the same
situation (PP/PK/EV), under both HALO's assignment and the old time window.

**Done when:** every mart matches the golden numbers (or every difference is explained as a bug fix).

## Phase 4 — Serving layer: marts → Parquet → Rust API
- [x] Export marts to Parquet in GCS, run by the dbt workflow after each prod deploy
      (`infra/export_serving.py`). Uses free extract jobs rather than `EXPORT DATA`, which
      bills the query. Small marts go to `serving/prod/marts/<table>/*.parquet` (about 6 MB),
      which the API holds in memory. Events, shifts, stints and tracking are too large for
      that (stints alone would be over 1 GB in memory), and a page only ever needs one game,
      so they go to `serving/prod/games/<table>/<game_id>.parquet` (about 375 MB in total).
      Also writes fixed 100-row samples to `serving/prod/samples/<name>.parquet`. Game
      `1528a22a…` (WBS vs BEL, 2023-11-04) has no HALO tracking, so the API must handle a
      game with no tracking file.
- [x] Rust (Axum) API in `site/`: small marts held in memory as typed structs read from
      Parquet (only the columns each struct declares), with HashMap indexes. Per-game files
      (including tracking) are loaded on first request into a 16-game cache, never all
      13.5M tracking rows at once. First local numbers, on dev data: loads in about 55 ms,
      61 MB resident, about 1 ms per in-memory request, about 14 ms for a game's first
      request (reads its files), and 1–12 KB gzipped responses.
      Endpoints, one per page view:
  - [x] `/api/health`, `/api/seasons`, `/api/standings?league&season`
  - [x] `/api/player-stats?league&season&situation&sort&dir&page` (25 rows per page)
  - [x] `/api/teams/{abbr}/{season}?situation&sort&dir`
  - [x] `/api/players/{player_id}?situation`
  - [x] `/api/games/{game_id}/players/{player_id}?situation` (header, stat line, shifts)
  - [x] `/api/games/{game_id}/players/{player_id}/shifts/{shift}` (stint rows + rink frames)
  - [x] `/api/sample/{name}` (fixed 100-row sample per table, replacing Sample Data's random rows)
- [x] Player Analysis (defensemen LPR table), 2026-10-27. Dash computed it per request
      from most of `events` and all of `stints`; it's now `int_lpr_events` (one row per
      5-on-5 defenseman LPR, with next-play result and post-LPR on-ice xG) and
      `fct_defense_lpr` (one row per defenseman × dropdown view), served by
      `/api/player-analysis/defense-lpr?view&sort&dir` with the page's minimums (20 GP,
      15 LPRs) and Total row. **Parity:** `golden.defense_lpr` snapshots the page as
      displayed for all 5 views (`scripts/export_golden_defense_lpr.py`). The legacy-parity
      build matches all 645 rows within the page's rounding, with counts exact. With the
      bug fixes, 12 of 1,761 mart rows move (on-ice xG of the boundary shots, at most 0.17).
      Ties at the same instant are ordered by `sl_event_id`, which matches the old
      Postgres `id` order exactly.
- [x] API exposure: endpoints return only what a page needs (one game or stint at a time,
      only the columns drawn), no bulk-download endpoints, per-client rate limiting.
      Data is never compiled into the WASM frontend; it always comes through endpoints.
      Rate limit: 5 requests/s sustained, bursts of 50, per client IP, per instance (max 2
      instances). The key is the last `X-Forwarded-For` entry, which Cloud Run appends
      (checked 2026-10-26: forged earlier entries are ignored). **Recheck
      `TRUSTED_PROXY_HOPS` if Firebase Hosting goes in front**, since it adds a hop.
- [x] HALO license: showing raw tracking publicly is fine (confirmed by Jake, 2026-10-26)
- [x] `cargo test` + endpoint tests (CI: `.github/workflows/site.yml`); deploy to Cloud Run.
      Live at https://snakepuck-api-xxquvkhdxq-uc.a.run.app (e.g. `/api/standings?league=AHL&season=2023-24`).
      CI builds a distroless image (about 73 MB) and applies `site/service.yaml`: scale to
      zero, max 2 instances, bucket mounted read-only with only `serving/prod` visible.
      After each export, the dbt workflow rolls a new revision so instances load the new
      marts. Setup is recorded in `infra/README.md`. Startup loads the marts in about 1 s
      over the mount (3 s before files were read whole). Warm requests take about 1 ms on
      the server; from the East Coast, round trip dominates at 80–100 ms.
- [x] Benchmark latency and memory vs the Dash/Postgres path; publish the numbers.
      `docs/BENCHMARKS.md` (scripts in `bench/`), 2026-10-27. Locally, per page view, the
      API is 36–209× faster at the median (179× for a rink shift) and gives 74–509× more
      throughput, using 61–72 MB of memory against Dash's 502–596 MB plus Postgres. Live,
      network round trips dominate, so it's 1.3–7× faster per page and 40× for the rink.
      Caveats are in the doc: Dash returns rendered components, it doesn't compress, and
      its rink query is N+1.

**Done when:** the API serves every dataset the site needs, with published benchmarks.

**Phase 4 complete (2026-10-27).** Every Dash page's data is served by the live API.

## Phase 5 — Leptos frontend, page by page
- [x] Leptos app shell (navbar, footer, routing, SnakePuck styling), 2026-10-27. Leptos
      0.8 (latest stable), server-rendered and hydrated, in the same `site/` crate and
      process as the API. `ssr` and `hydrate` features: the data layer (`src/server/`) is
      ssr-only, so HALO data can't be compiled into the WASM bundle (346 KB, 135 KB
      gzipped). Styling is the Dash site's Bootstrap 5.3.6 plus `assets/custom.css`, carried
      over as-is. `cargo leptos watch` serves it locally at http://localhost:3000.
- [ ] Port pages roughly in order of simplicity: About → Blog → Standings →
      Player Stats → Team Detail → Player Detail → Game Report (rink last)
  - [x] About
  - [x] Blog, 2026-10-27: posts from `content/blog` baked into the image
  - [x] Standings, 2026-10-27: league and season in the URL; sorting and the
        division/league view are in the browser. `/api/standings` now returns the season
        list too, with both parameters optional (AHL, newest season)
  - [x] Player Stats, 2026-10-27: every choice is in the URL, which the page parses
        into the same `PlayerStatsQuery` the API reads. The server sorts and pages; a page
        past the end now means the last page, as on Dash
  - [x] Team Detail, 2026-10-27: `/team/<team_abbr>/<season>?situation&sort&dir`. The API
        returns `skaters` and `goalies` separately (goalies by games played, as on Dash).
        The player tables share `src/app/stats_table.rs`
  - [x] Player Detail, 2026-10-27: `/player/<player_id>?situation`. Game log rows open
        `/player/<player_id>/game/<game_id>`, the Dash site's Game Report URL
  - [x] Game Report, 2026-10-27: `/player/<player_id>/game/<game_id>?situation&period&shift`.
        The rink is SVG drawn by Leptos (ported from `app/utils/rink.py`), not Plotly: it
        renders on the server and playback redraws only the frame's markers. Playback
        timing and the slider's stint marks follow Dash
  - [ ] Player Analysis, Sample Data
- [x] Pages not yet ported link back to the Dash site during the transition
- [ ] Playwright smoke tests per page (for now, a headless-Chrome check that hydration,
      the menu and client-side navigation work, with no console errors)

Data for pages: each endpoint's response type is shared by both builds. Server rendering
calls the endpoint's function directly; navigation in the browser fetches the same
`/api/...` endpoint. The REST API stays the one interface.

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
- **Infrastructure as code:** Terraform now, or click-ops first and codify later?
- **Domain/hosting cutover:** when to point the live domain at Firebase Hosting / Cloud Run

## Reminders
- BigQuery daily query cap is temporarily 200 GiB (raised 2026-10-26 for build-out).
  Lower it to 50 GiB once Phases 3–5 settle (command in `infra/README.md`).

## Decided
- **Cold starts (2026-10-27):** scale to zero, to keep costs low for now. The first
  request after an idle period takes about 2.6 s. One warm instance (about $10–15 a
  month) is a one-line change in `site/service.yaml` if that's needed later.
- **Season lists (2026-10-27):** Standings and Player Stats include the season list and
  default to the newest season, so each page is one request.
- **Tracking in the API (2026-10-26):** per-game Parquet in GCS, loaded on demand, not
  bundled into the container image. New data is expected, so data deploys stay
  separate from code deploys.
- **API URLs (2026-10-26):** natural keys (`player_id`, `team_abbr` + season, game UUID),
  not the Dash site's Postgres integer ids. Old Dash links need redirects if we want them.
- **API data model (2026-10-26):** typed Rust structs plus indexes, not Polars DataFrames.
  Leaner, faster and quicker to compile, and the endpoints need no ad-hoc analytics.

## Deferred
- Smooth player animation on the rink. HALO tracking is per-event snapshots,
  not continuous frames. Revisit only with frame-level data.
- Re-enabling login (code kept, commented out)
- Robustness items (SECRET_KEY fallback, routing refactor, caching) are superseded by the rewrite
