# Benchmarks: Dash + Postgres vs the Rust API

Measured 2026-10-27. Scripts in `bench/`.

## What's compared

For each page, the Dash site's data requests for one page view are compared with the
Rust API requests that replace them. Dash makes one request per callback, and a page
load fires several: Player Detail fires four that query the database. The API makes
one request per page view, two where the season dropdown needs `/api/seasons`. Page
times below are the **sum of each request's median**, as if the requests ran one after
another. The browser runs some Dash callbacks in parallel, so this overstates Dash's
page time somewhat.

`bench/build_requests.py` captures the Dash requests by acting as a minimal Dash
client. It runs each page's callbacks in the order a page load fires them and feeds
each response into the next callback. It keeps only the callbacks that hit the
database. Both sides use the same entities: the season's top scorer, his team, his
latest game and his third shift. These are looked up at run time.

## Read these numbers with care

- **Dash returns rendered components and the API returns data.** Dash callbacks send
  ready-made HTML component trees. The API sends JSON that the Leptos frontend (Phase
  5) will render, and some of that rendering work comes back if pages are rendered on
  the server. These numbers compare data serving, not full page loads.
- **Dash doesn't compress responses. That's one flag (`compress=True`).** Sizes below
  are uncompressed, which is the fair comparison. With gzip, the API's responses
  shrink a further 4–10×.
- **The old rink query is inefficient.** The Dash callback for a shift's frames takes
  339 ms. Its code lazy-loads the player for each tracking row (an N+1 query), which is
  a likely cause, though I haven't profiled it. Tuned SQL would probably close much of
  that gap, so part of the rink speedup is old-code inefficiency, not Rust.
- **The Game Report's Dash total includes the rink drawing** (`rink-base`, 17 ms,
  27 KB of Plotly geometry). The new site draws the rink in the browser, so that
  request has no API counterpart.
- The local run uses one machine for everything (Apple M1 Max, 10 cores, 64 GB): the
  servers, Postgres and the load generator.

## Local: same machine, same data

Dash runs as deployed: gunicorn with 4 sync workers, and Postgres 18 local. The API
is the release build. Its rate limiter stays in the request path, with the limits
raised. Latency comes from one client sending 200 requests in a row after a warm-up.
Throughput comes from 32 concurrent clients (`oha`). Dash's throughput runs are
capped at 3,000 requests: its sync workers close every connection, and longer runs
exhaust macOS's local ports on the client side (see `bench/run.py`).

| Page | Dash: requests, p50, p95 | Rust API: requests, p50, p95 | p50 ratio | Page views/s, Dash → API | Response size raw, Dash → API |
|---|---|---|---|---|---|
| Standings | 3, 14.9 ms, 19.2 ms | 2, 0.37 ms, 0.47 ms | 40× | 279 → 31,559 (113×) | 86 KB → 12 KB (7.4×) |
| Player Stats | 3, 25.2 ms, 35.4 ms | 2, 0.70 ms, 0.87 ms | 36× | 186 → 13,739 (74×) | 93 KB → 13 KB (7.2×) |
| Team Detail | 4, 20.8 ms, 27.2 ms | 1, 0.35 ms, 0.42 ms | 59× | 199 → 30,309 (152×) | 101 KB → 18 KB (5.5×) |
| Player Detail | 4, 34.2 ms, 49.8 ms | 1, 0.34 ms, 0.40 ms | 100× | 123 → 30,852 (251×) | 117 KB → 19 KB (6.2×) |
| Game Report | 6, 44.0 ms, 58.4 ms | 1, 0.21 ms, 0.27 ms | 209× | 101 → 51,481 (509×) | 54 KB → 5 KB (10.1×) |
| Rink (one shift) | 2, 348.2 ms, 401.8 ms | 1, 1.95 ms, 2.09 ms | 179× | 15 → 4,128 (267×) | 222 KB → 167 KB (1.3×) |

"Page views/s" is the throughput of the page's requests run back to back:
1 / Σ(1 / requests per second).

**Memory (resident):** Dash, gunicorn master plus 4 workers, uses 502 MB idle and
596 MB at peak. The Rust API uses 61 MB idle and 72 MB at peak. Dash also needs
Postgres, about 288 MB. That figure is approximate, because Postgres's shared memory
is counted once per process.

## Live: as a visitor sees it

The live comparison is Dash at snakepuck.com (DigitalOcean, behind Cloudflare, managed
Postgres) against the API on Cloud Run (us-central1), measured from a home connection
in the US Eastern time zone. It's
latency only, at 2 requests a second, so it's gentle on the production site and stays
under the API's rate limit: 30 samples per request after a warm-up, over kept-alive
connections. The two hosts sit at different distances from the client, so the gap
isn't only the code.

| Page | Dash requests | Dash p50 (sum) | API requests | API p50 (sum) | Ratio |
|---|---|---|---|---|---|
| Standings | 3 | 130 ms | 2 | 98 ms | 1.3× |
| Player Stats | 3 | 167 ms | 2 | 98 ms | 1.7× |
| Team Detail | 4 | 181 ms | 1 | 49 ms | 3.7× |
| Player Detail | 4 | 245 ms | 1 | 50 ms | 4.9× |
| Game Report | 6 | 337 ms | 1 | 47 ms | 7.2× |
| Rink (one shift) | 2 | 2,424 ms | 1 | 61 ms | 40× |

Over the internet, the round trip dominates: about 49 ms per API request from the
client to Iowa. The server's own time is under 2 ms. So most of the live gain comes from
**fewer requests per page** and from the rink query, not from raw server speed. The
two-request pages (Standings, Player Stats) gain little. `/api/seasons` rarely
changes, so a browser cache or the frontend could skip it, and those pages would also
become one request.

**Cold start:** the API scales to zero when idle. The first request after an idle
period took 2.6 s (one observation, 2026-10-27). About 1 s of that is loading the marts
over the Cloud Storage mount; the rest is starting the instance. A warm instance
removes this wait (see Open decisions in `MIGRATION_PLAN.md`).

## Reproduce

```bash
# Dash as deployed, against local Postgres
gunicorn run:app --bind 127.0.0.1:8060 --workers 4
# The API, release build, limiter raised for load testing
(cd site && DATA_DIR=data/serving PORT=8091 RATE_LIMIT_PER_SECOND=1000000 \
  RATE_LIMIT_BURST=1000000 cargo run --release)

cargo install oha
python bench/build_requests.py > bench/out/requests.json
python bench/run.py local > bench/out/report-local.md   # ~15 min
python bench/live.py > bench/out/report-live.md          # ~8 min
```
