"""Checking for, downloading and offering new releases (design C15, C16).

When to check:

* Online (cable, or a dongle on a known network): at start-up, then every
  ``update.check_interval_h``.
* Single radio: at start-up, and when an admin presses *Check for updates*.
  Never on a schedule. The radio has to leave the access point, so the check
  waits for the bells to be quiet, tells the wall display, joins a known
  network, and comes back to the AP as soon as it is done or its time is up.
* No known networks and no cable: never. *Check for updates* says why.

A newer release is downloaded, verified and staged, then waits for an admin to
press *Apply* (requirements: "an option in the ACP to apply the update"). It
is never applied automatically. A version that failed its health check on this
Pi is never offered again.
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from tower import version
from tower.fsutil import atomic_write
from tower.release import ReleaseError
from tower.release.github import GitHubReleases, Release, UpdateError, is_newer
from tower.wallclock import ntp_synchronised

if TYPE_CHECKING:
    from tower.web.api import TowerApp

log = logging.getLogger(__name__)

STATE_FILE = "update-check.json"
STARTUP_DELAY_S = 20.0  # let the network settle after boot
POLL_S = 5.0


class _OutOfTime(Exception):
    pass


def clock_set() -> bool:
    """Whether systemd says the clock is set from the internet. Off a systemd host
    there is no way to tell, so don't wait."""
    return shutil.which("timedatectl") is None or ntp_synchronised()


class UpdateService:
    def __init__(self, app: TowerApp, github: GitHubReleases | None = None,
                 ntp: Callable[[], bool] = clock_set) -> None:
        self.app = app
        self.github = github or GitHubReleases(app.cfg.update.github_repo)
        self.ntp = ntp
        self.wake = threading.Event()
        self.busy = threading.Lock()
        self.state = "idle"
        self.message = ""
        self.progress: tuple[int, int] | None = None
        self.update_mode: dict | None = None  # shown on the wall during a single-radio check
        self._saved = self._load()

    @property
    def cfg(self):
        return self.app.cfg.update

    # --- what the admin page sees ----------------------------------------------------

    def status(self) -> dict:
        available = self._saved.get("available")
        if available and not self._still_offered(available["version"]):
            available = None
        plan = self.app.net.plan() if self.app.net.available() else None
        return {
            "state": self.state,
            "message": self.message,
            "progress": {"done": self.progress[0], "total": self.progress[1]} if self.progress else None,
            "last_check_at": self._saved.get("last_check_at"),
            "last_result": self._saved.get("last_result"),
            "available": available,
            "how": _how(plan),
            "repo": self.cfg.github_repo,
        }

    def request_check(self) -> str:
        if self.busy.locked():
            return "a check is already running"
        self.wake.set()
        return "check started"

    def apply(self) -> str:
        available = self._saved.get("available")
        if not available or not self._still_offered(available["version"]):
            raise UpdateError("there is no downloaded update to apply")
        # The staged release is named by its full version (``0.4.0+g1a2b3c4``),
        # not the tag's (``0.4.0``).
        return self.app.handoff("activate", available.get("staged_version", available["version"]))

    # --- the loop ----------------------------------------------------------------------

    def run(self, stop: threading.Event) -> None:
        clock = self.app.clock
        if self.app.net.available():  # on a Pi; off it, only when asked
            if stop.wait(STARTUP_DELAY_S):
                return
            self.check(reason="start-up")
        while not stop.is_set():
            manual = self.wake.wait(60)
            if stop.is_set():
                return
            self.wake.clear()
            due = self._online_check_due(clock)
            if manual or due:
                self.check(reason="requested" if manual else "daily")

    def _online_check_due(self, clock) -> bool:
        if not self.app.net.available():
            return False  # off the Pi: only when asked
        try:
            if not self.app.net.online():
                return False
        except RuntimeError:
            return False
        last = self._saved.get("last_check_monotonic_boot")
        boot = _boot_marker()
        if last is None or last[0] != boot:
            return True
        return time.monotonic() - last[1] >= self.cfg.check_interval_h * 3600

    def check(self, reason: str = "requested") -> dict:
        """Run one check now (blocking). Returns the result recorded for the admin page."""
        if not self.busy.acquire(blocking=False):
            return {"ok": False, "detail": "a check is already running"}
        try:
            result = self._check(reason)
        except Exception as e:  # noqa: BLE001 — a failed check must never take the app down
            log.exception("update check failed")
            result = {"ok": False, "detail": f"check failed: {e}"}
        finally:
            self.state, self.progress = "idle", None
            self.busy.release()
        self._record(result)
        return result

    def _check(self, reason: str) -> dict:
        net = self.app.net
        if not net.available():
            # Not a Pi (e.g. development on a Mac): no radios to manage, so check directly.
            return self._fetch(deadline=None)
        plan = net.plan()
        log.info("update check (%s) with plan %s", reason, plan)
        if plan == "offline":
            return {"ok": False, "detail": "no way to reach the internet: plug in a network cable, "
                                           "or add a known WiFi network on the Network page"}
        if plan in ("cable", "dongle"):
            if not net.online():
                return {"ok": False, "detail": "the USB WiFi dongle is not connected to any known network"}
            return self._fetch(deadline=None)
        return self._single_radio_check()

    # --- single radio ----------------------------------------------------------------------

    def _single_radio_check(self) -> dict:
        clock = self.app.clock
        self._set("waiting_for_quiet", "waiting for the bells to be quiet")
        while not self._quiet():
            clock.sleep_until(clock.now() + POLL_S)
        deadline = clock.now() + self.cfg.check_window_s
        self._announce(True)
        supervisor = self.app.supervisor
        supervisor.paused = True  # the radio is ours until we give it back
        try:
            self._set("going_online", "joining a known network")
            ok, detail = self.app.net.go_online()
            if not ok:
                return {"ok": False, "detail": detail}
            log.info("update check: %s", detail)
            return self._fetch(deadline=deadline, joined=detail)
        finally:
            self._set("returning", "returning to the access point")
            back = self.app.net.back_to_ap()
            if not back.ok:
                log.error("could not restore the access point: %s", back.detail)
            supervisor.paused = False
            self._announce(False)

    def _quiet(self) -> bool:
        last = self.app.bus.last_strike_at
        return last is None or self.app.clock.now() - last >= self.cfg.quiet_s

    def _announce(self, active: bool) -> None:
        """Tell the wall display (requirements: "Update mode information")."""
        if active:
            minutes = max(1, round(self.cfg.check_window_s / 60))
            self.update_mode = {
                "active": True,
                "message": f"The Towerboard WiFi is off for up to {minutes} minutes while the Pi looks for new software.",
                "if_stuck": "If this message stays for longer, switch the Pi off and on again. "
                            "If it keeps happening, remove the Pi's known networks on the admin page.",
            }
        else:
            self.update_mode = None
        self.app.bus.emit("state", {"update_mode": self.update_mode or {"active": False}})

    # --- fetching ------------------------------------------------------------------------------

    def _fetch(self, deadline: float | None, joined: str | None = None) -> dict:
        clock = self.app.clock
        self._wait_for_clock(deadline)
        self._set("checking", f"asking GitHub for releases of {self.cfg.github_repo}")
        try:
            release = self.github.latest(version.full_version(), include_pre=self.cfg.channel == "pre",
                                         skip=self._failed())
        except UpdateError as e:
            return {"ok": False, "detail": str(e)}
        via = f" (via {joined.removeprefix('joined ')})" if joined else ""
        if release is None:
            self._saved.pop("available", None)
            return {"ok": True, "detail": f"up to date: {version.full_version()} is the newest release{via}"}
        already = self._staged_as(release.version)
        if already:
            self._offer(release, already)
            return {"ok": True, "detail": f"{release.version} is downloaded and ready to apply"}
        incoming = self.app.cfg.state_dir / "incoming" / f"github-{release.version}.tower"

        def progress(done: int, total: int) -> None:
            self.progress = (done, total)
            if deadline is not None and clock.now() >= deadline:
                raise _OutOfTime()

        self._set("downloading", f"downloading {release.version}")
        try:
            self.github.download(release, incoming, progress)
            self._set("verifying", f"checking the signature of {release.version}")
            staged = self.app.releases.stage(incoming, Path(self.cfg.allowed_signers))
        except _OutOfTime:
            return {"ok": False, "detail": f"ran out of time downloading {release.version}; it will be tried again"}
        except UpdateError as e:
            return {"ok": False, "detail": str(e)}
        except ReleaseError as e:
            log.error("rejected %s from GitHub: %s", release.version, e)
            return {"ok": False, "detail": f"{release.version} from GitHub was rejected: {e}"}
        finally:
            incoming.unlink(missing_ok=True)
        self._offer(release, staged)
        return {"ok": True, "detail": f"{release.version} downloaded and ready to apply{via}"}

    def _wait_for_clock(self, deadline: float | None) -> None:
        clock = self.app.clock
        until = clock.now() + self.cfg.ntp_wait_s
        if deadline is not None:
            until = min(until, deadline)
        self._set("checking", "waiting for the clock to be set from the internet")
        while not self.ntp() and clock.now() < until:
            clock.sleep_until(clock.now() + 2)

    def _offer(self, release: Release, staged: str | None = None) -> None:
        offer = release.as_dict()
        offer["staged_version"] = staged or release.version
        self._saved["available"] = offer

    def _still_offered(self, v: str) -> bool:
        staged = self._saved.get("available", {}).get("staged_version", v)
        return is_newer(v, version.full_version()) and staged in self.app.releases.available() \
            and v not in self._failed()

    def _failed(self) -> set[str]:
        """Failed versions by release number: the manager records full versions."""
        return {v.split("+")[0] for v in self.app.releases.failed_versions()}

    def _staged_as(self, release_version: str) -> str | None:
        """The staged release for a tag's version, e.g. ``0.4.0`` → ``0.4.0+g1a2b3c4``."""
        return next((v for v in self.app.releases.available()
                     if v.split("+")[0] == release_version), None)

    # --- persistence ------------------------------------------------------------------------------

    def _set(self, state: str, message: str) -> None:
        self.state, self.message = state, message
        log.info("update: %s", message)

    def _record(self, result: dict) -> None:
        self._saved["last_result"] = result
        self._saved["last_check_at"] = datetime.fromtimestamp(
            self.app.wallclock.now(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._saved["last_check_monotonic_boot"] = [_boot_marker(), time.monotonic()]
        self.message = result["detail"]
        atomic_write(self._path(), json.dumps(self._saved, indent=2) + "\n")

    def _path(self) -> Path:
        return self.app.cfg.state_dir / STATE_FILE

    def _load(self) -> dict:
        try:
            data = json.loads(self._path().read_text())
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}


def _how(plan: str | None) -> str:
    return {
        "cable": "online over the network cable: checks at start-up and daily",
        "dongle": "online through the USB WiFi dongle: checks at start-up and daily",
        "single": "one WiFi radio: checks at start-up and when you press Check for updates; "
                  "the Towerboard WiFi is off while it checks",
        "offline": "no known networks and no cable: the Pi never goes online",
    }.get(plan or "", "not a Pi (no network management): checks GitHub directly when asked")


def _boot_marker() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "no-boot-id"
