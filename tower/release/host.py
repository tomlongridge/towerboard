"""How the pipeline restarts and checks the real system (Pi only).

The app cannot restart itself and then judge its own health, so it hands
over: it writes ``update-request.json`` and starts ``tower-update.service``,
a oneshot unit that runs ``python -m tower.release run-request`` from the
release that was current when it started. That process swaps, restarts
``tower.service``, health-checks over HTTP and rolls back if needed.

There is deliberately no Mac stand-in for systemd here (design §3): off
the Pi, ``systemd_available()`` is false and the app says so.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from tower.clock import Clock

REQUEST_FILE = "update-request.json"
UPDATER_UNIT = "tower-update.service"

Runner = Callable[..., subprocess.CompletedProcess]


def run(argv: list[str], timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


def systemd_available() -> bool:
    return shutil.which("systemctl") is not None and Path("/run/systemd/system").is_dir()


def write_request(state: Path, action: str, version: str | None = None) -> None:
    state.mkdir(parents=True, exist_ok=True)
    tmp = state / (REQUEST_FILE + ".tmp")
    tmp.write_text(json.dumps({"action": action, "version": version}) + "\n")
    os.replace(tmp, state / REQUEST_FILE)


def take_request(state: Path) -> dict | None:
    path = state / REQUEST_FILE
    try:
        req = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    path.unlink()
    return req


def start_updater(runner: Runner = run) -> None:
    r = runner(["systemctl", "start", "--no-block", UPDATER_UNIT])
    if r.returncode != 0:
        raise RuntimeError(f"could not start {UPDATER_UNIT}: {r.stderr.strip()}")


def restart_units(units: list[str], runner: Runner = run) -> Callable[[], None]:
    def restart() -> None:
        r = runner(["systemctl", "restart", *units], timeout=120)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or f"systemctl exited {r.returncode}")

    return restart


def health_check(
    port: int, units: list[str], timeout: float, clock: Clock, runner: Runner = run
) -> Callable[[str], tuple[bool, str]]:
    """Healthy when every unit is active and ``/api/health`` reports ``version`` and ok.

    Polls until ``timeout`` (the grace period) so a slow start is not a failure.
    """

    def check(version: str) -> tuple[bool, str]:
        deadline = clock.now() + timeout
        last = "no response"
        while True:
            last = _check_once(port, units, version, runner)
            if last == "ok":
                return True, f"healthy on {version}"
            if clock.now() >= deadline:
                return False, last
            clock.sleep_until(clock.now() + 1.0)

    return check


def _check_once(port: int, units: list[str], version: str, runner: Runner) -> str:
    r = runner(["systemctl", "is-active", *units], timeout=10)
    if r.returncode != 0:
        states = " ".join(r.stdout.split()) or "unknown"
        return f"units not active: {states}"
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as resp:
            body = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError) as e:
        return f"HTTP health endpoint: {e}"
    if body.get("version") != version:
        return f"running {body.get('version')!r}, expected {version!r}"
    if body.get("status") != "ok":
        return f"health status {body.get('status')!r}: {body.get('checks')}"
    return "ok"
