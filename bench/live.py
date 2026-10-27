"""Latency of the live sites, as a visitor sees it: Dash at snakepuck.com (DigitalOcean,
behind Cloudflare) and the Rust API on Cloud Run.

    python bench/live.py > bench/out/report-live.md

Replays bench/out/requests.json (the live Dash database uses the same ids as the local
copy it was restored from) with the hosts swapped. Latency only, 2 requests a second:
gentle on the production site and under the API's rate limit. Throughput is measured
locally (run.py), where neither side is limited by the network or rate limits.
"""

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).parent / "out"
OHA = str(Path.home() / ".cargo/bin/oha")
HOSTS = {
    "http://127.0.0.1:8060": "https://snakepuck.com",
    "http://127.0.0.1:8091": "https://snakepuck-api-xxquvkhdxq-uc.a.run.app",
}
SAMPLES = 30


def latency(request: dict) -> dict:
    url = request["url"]
    for local, live in HOSTS.items():
        url = url.replace(local, live)
    cmd = [OHA, "--no-tui", "--output-format", "json", "-H", "Accept-Encoding: gzip"]
    cmd += ["-c", "1", "-q", "2"]
    if request["method"] == "POST":
        cmd += [
            "-m",
            "POST",
            "-T",
            "application/json",
            "-d",
            json.dumps(request["body"]),
        ]
    for n in (3, SAMPLES):  # warm-up, then measure
        out = json.loads(
            subprocess.run(
                [*cmd, "-n", str(n), url], capture_output=True, check=True
            ).stdout
        )
    assert set(out["statusCodeDistribution"]) == {"200"}, (
        request["name"],
        out["statusCodeDistribution"],
    )
    p = out["latencyPercentiles"]
    return {
        **{k: request[k] for k in ("page", "side", "name")},
        "p50_ms": p["p50"] * 1000,
        "p95_ms": p["p95"] * 1000,
    }


def main() -> None:
    requests = json.loads((OUT / "requests.json").read_text())
    results = []
    for i, request in enumerate(requests, 1):
        print(
            f"[{i}/{len(requests)}] {request['page']} {request['side']}",
            file=sys.stderr,
        )
        results.append(latency(request))
    (OUT / "results-live.json").write_text(json.dumps(results, indent=1))

    pages = defaultdict(lambda: defaultdict(list))
    for r in results:
        pages[r["page"]][r["side"]].append(r)
    print(
        "| Page | Dash requests | Dash p50 (sum) | API requests | API p50 (sum) | Ratio |"
    )
    print("|---|---|---|---|---|---|")
    for page, sides in pages.items():
        d = sum(r["p50_ms"] for r in sides["dash"])
        a = sum(r["p50_ms"] for r in sides["api"])
        print(
            f"| {page} | {len(sides['dash'])} | {d:.0f} ms | {len(sides['api'])} | {a:.0f} ms | {d / a:.1f}× |"
        )


if __name__ == "__main__":
    main()
