"""Browser smoke tests for the Leptos site: each page loads, hydrates and its controls
work, with no console errors.

They need the licensed HALO data in site/data/serving, which never enters CI or the
repo, so they skip without it. The entities they click through (a team, a player, a
game) are found at run time, never written down here.

    pytest site/e2e                                  # builds and serves on :3010
    SITE_URL=http://127.0.0.1:3000 pytest site/e2e   # a site that's already running

They drive the installed Google Chrome, so Playwright needs no browser download.
"""

import os
import signal
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parents[1]
DATA = SITE / "data" / "serving"
# Not 3000, which `cargo leptos watch` uses while developing.
PORT = 3010
BUILD_TIMEOUT_S = 900


def _healthy(url):
    try:
        with urllib.request.urlopen(f"{url}/api/health", timeout=2) as r:
            return r.status == 200
    except OSError:
        return False


@pytest.fixture(scope="session")
def base_url():
    if url := os.environ.get("SITE_URL"):
        yield url.rstrip("/")
        return
    if not (DATA / "marts").is_dir():
        pytest.skip("no local HALO data in site/data/serving (it never enters CI)")
    url = f"http://127.0.0.1:{PORT}"
    if _healthy(url):
        yield url
        return

    env = {
        **os.environ,
        "LEPTOS_SITE_ADDR": f"127.0.0.1:{PORT}",
        "LEPTOS_RELOAD_PORT": str(PORT + 1),
        "PATH": f"{Path.home() / '.cargo' / 'bin'}:{os.environ['PATH']}",
    }
    log = tempfile.NamedTemporaryFile(
        "w", prefix="snakepuck-e2e-", suffix=".log", delete=False
    )
    server = subprocess.Popen(
        ["cargo", "leptos", "serve"],
        cwd=SITE,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,  # its own process group, so teardown stops the server too
    )
    try:
        deadline = time.monotonic() + BUILD_TIMEOUT_S
        while not _healthy(url):
            if server.poll() is not None:
                pytest.fail(f"cargo leptos serve exited; see {log.name}")
            if time.monotonic() > deadline:
                pytest.fail(f"site not up after {BUILD_TIMEOUT_S}s; see {log.name}")
            time.sleep(2)
        yield url
    finally:
        os.killpg(server.pid, signal.SIGTERM)
        server.wait(timeout=30)


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {"channel": "chrome", **browser_type_launch_args}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1600, "height": 1000}}


@pytest.fixture(autouse=True)
def no_console_errors(page):
    """Fail any test whose page logs an error or throws."""
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    yield
    assert not errors, f"console errors: {errors}"
