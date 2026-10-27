"""Run the benchmark over bench/out/requests.json (see build_requests.py).

    python bench/run.py [label] > bench/out/report-<label>.md

For each request: latency with one client (200 requests after a warm-up), throughput
with 32 concurrent clients, and response size gzipped and raw.

Throughput runs 10 s for the API but a fixed 3,000 requests for Dash. Dash's gunicorn
sync workers close the connection after every response, so each request takes a new
local port, which macOS then holds for ~30 s (TIME_WAIT). At Dash's rate a 10 s run
exhausts the ~16k ports and fails on the client side, so Dash runs are capped and
wait for ports to free up first. The API keeps connections alive and isn't affected. While it runs,
the memory of the server processes is sampled: Dash (gunicorn master + workers), the
Rust API, and Postgres (approximate: its shared memory is counted once per process).
Raw results go to bench/out/results-<label>.json; a Markdown report goes to stdout.

Needs `oha` (cargo install oha) and both servers running locally.
"""

import json
import subprocess
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).parent / "out"
OHA = str(Path.home() / ".cargo/bin/oha")
LATENCY_REQUESTS = 200
CLIENTS = 32
DASH_THROUGHPUT_REQUESTS = 3000
MAX_TIME_WAIT = 8000  # sockets; macOS has ~16k ephemeral ports


def oha(request: dict, *args: str) -> dict:
    cmd = [
        OHA,
        "--no-tui",
        "--output-format",
        "json",
        "-H",
        "Accept-Encoding: gzip",
        *args,
    ]
    if request["method"] == "POST":
        cmd += [
            "-m",
            "POST",
            "-T",
            "application/json",
            "-d",
            json.dumps(request["body"]),
        ]
    result = json.loads(
        subprocess.run([*cmd, request["url"]], capture_output=True, check=True).stdout
    )
    codes = result["statusCodeDistribution"]
    # Requests still in flight when a timed run ends are aborted; anything else is a failure.
    errors = {
        e: n
        for e, n in result["errorDistribution"].items()
        if e != "aborted due to deadline"
    }
    assert set(codes) == {"200"} and not errors, f"{request['name']}: {codes} {errors}"
    return result


def wait_for_free_ports() -> None:
    while True:
        netstat = subprocess.run(
            ["netstat", "-an", "-p", "tcp"], capture_output=True, text=True
        )
        if netstat.stdout.count("TIME_WAIT") < MAX_TIME_WAIT:
            return
        time.sleep(2)


def size(request: dict, gzip: bool) -> int:
    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{size_download}"]
    if gzip:
        cmd += ["-H", "Accept-Encoding: gzip"]
    if request["method"] == "POST":
        cmd += [
            "-X",
            "POST",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(request["body"]),
        ]
    return int(
        subprocess.run([*cmd, request["url"]], capture_output=True, check=True).stdout
    )


def pids(pattern: str) -> list[str]:
    found = subprocess.run(
        ["pgrep", "-f", pattern], capture_output=True, text=True
    ).stdout
    return found.split()


def rss_mb(process_ids: list[str]) -> float:
    if not process_ids:
        return 0.0
    out = subprocess.run(
        ["ps", "-o", "rss=", "-p", ",".join(process_ids)],
        capture_output=True,
        text=True,
    )
    return sum(int(line) for line in out.stdout.split()) / 1024


class MemorySampler(threading.Thread):
    """Peak resident memory of each server while the benchmark runs."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.servers = {
            "dash": pids("gunicorn run:app"),
            "api": pids("target/release/snakepuck"),
            "postgres": pids("postgres"),
        }
        self.idle = {name: rss_mb(p) for name, p in self.servers.items()}
        self.peak = dict(self.idle)
        self.running = True

    def run(self) -> None:
        while self.running:
            for name, p in self.servers.items():
                self.peak[name] = max(self.peak[name], rss_mb(p))
            time.sleep(0.25)


def measure(request: dict) -> dict:
    oha(request, "-n", "20", "-c", "1")  # warm-up
    latency = oha(request, "-n", str(LATENCY_REQUESTS), "-c", "1")
    if request["side"] == "dash":
        wait_for_free_ports()
        throughput = oha(
            request, "-n", str(DASH_THROUGHPUT_REQUESTS), "-c", str(CLIENTS)
        )
    else:
        throughput = oha(request, "-z", "10s", "-c", str(CLIENTS))
    successes = throughput["statusCodeDistribution"]["200"]
    ms = {p: latency["latencyPercentiles"][p] * 1000 for p in ("p50", "p95", "p99")}
    return {
        **{k: request[k] for k in ("page", "side", "name")},
        **{f"{p}_ms": round(v, 2) for p, v in ms.items()},
        "rps": round(successes / throughput["summary"]["total"], 1),
        "bytes_gzip": size(request, gzip=True),
        "bytes_raw": size(request, gzip=False),
    }


def report(results: list[dict], memory: dict) -> str:
    by_page = defaultdict(lambda: defaultdict(list))
    for r in results:
        by_page[r["page"]][r["side"]].append(r)

    def total(rows: list[dict]) -> dict:
        return {
            "n": len(rows),
            "p50": sum(r["p50_ms"] for r in rows),
            "p95": sum(r["p95_ms"] for r in rows),
            # Page views per second if every request of the page ran back to back
            # at its measured throughput.
            "pages_per_s": 1 / sum(1 / r["rps"] for r in rows),
            "kb_gzip": sum(r["bytes_gzip"] for r in rows) / 1024,
        }

    lines = [
        "| Page | Stack | Requests | p50 (sum) | p95 (sum) | Page views/s at 32 clients | KB gzipped |",
        "|---|---|---|---|---|---|---|",
    ]
    for page, sides in by_page.items():
        d, a = total(sides["dash"]), total(sides["api"])
        for label, t in (("Dash", d), ("Rust API", a)):
            lines.append(
                f"| {page} | {label} | {t['n']} | {t['p50']:.1f} ms | {t['p95']:.1f} ms "
                f"| {t['pages_per_s']:,.0f} | {t['kb_gzip']:.1f} |"
            )
        lines.append(
            f"| | **ratio** | | **{d['p50'] / a['p50']:.0f}×** faster | "
            f"{d['p95'] / a['p95']:.0f}× | {a['pages_per_s'] / d['pages_per_s']:.0f}× | "
            f"{d['kb_gzip'] / a['kb_gzip']:.1f}× smaller |"
        )

    lines += [
        "",
        "| Request | Stack | p50 | p95 | p99 | Req/s | Bytes gzip | Bytes raw |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['page']}: `{r['name'][:60]}` | {r['side']} | {r['p50_ms']} | {r['p95_ms']} "
            f"| {r['p99_ms']} | {r['rps']:,.0f} | {r['bytes_gzip']:,} | {r['bytes_raw']:,} |"
        )

    lines += [
        "",
        "| Server | Memory before (MB) | Peak under load (MB) |",
        "|---|---|---|",
    ]
    for name in ("dash", "api", "postgres"):
        lines.append(
            f"| {name} | {memory['idle'][name]:.0f} | {memory['peak'][name]:.0f} |"
        )
    return "\n".join(lines)


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "local"
    requests = json.loads((OUT / "requests.json").read_text())
    sampler = MemorySampler()
    sampler.start()
    results = []
    for i, request in enumerate(requests, 1):
        print(
            f"[{i}/{len(requests)}] {request['page']} {request['side']} {request['name'][:50]}",
            file=sys.stderr,
        )
        results.append(measure(request))
    sampler.running = False
    memory = {"idle": sampler.idle, "peak": sampler.peak}
    (OUT / f"results-{label}.json").write_text(
        json.dumps({"results": results, "memory": memory}, indent=1)
    )
    print(report(results, memory))


if __name__ == "__main__":
    main()
