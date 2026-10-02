"""Release layout and the verify → stage → swap → health-check pipeline (design C15).

::

    <opt>/releases/<version>/      unpacked release
    <opt>/current -> releases/<version>
    <opt>/previous -> releases/<version>
    <state>/                       state, never inside a release

Restarting units and checking health are injected, so the pipeline is the
same code on the Pi (systemd, HTTP health) and in tests.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from tower.release import bundle
from tower.release.bundle import ReleaseError

log = logging.getLogger(__name__)

STATUS_FILE = "update-status.json"

Restart = Callable[[], None]
# Given the version that should now be running, returns (healthy, detail).
HealthCheck = Callable[[str], "tuple[bool, str]"]


@dataclass
class Result:
    ok: bool
    action: str
    version: str | None
    previous: str | None
    detail: str

    def as_dict(self) -> dict:
        return {
            "result": "ok" if self.ok else "failed",
            "action": self.action,
            "version": self.version,
            "from": self.previous,
            "detail": self.detail,
            "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


class ReleaseManager:
    def __init__(self, opt_dir: Path, state_dir: Path, python: str = sys.executable) -> None:
        self.opt = opt_dir
        self.state = state_dir
        self.python = python
        self.releases = opt_dir / "releases"
        self.current_link = opt_dir / "current"
        self.previous_link = opt_dir / "previous"

    # --- inspection ------------------------------------------------------

    def current(self) -> str | None:
        return self._target(self.current_link)

    def previous(self) -> str | None:
        return self._target(self.previous_link)

    def available(self) -> list[str]:
        if not self.releases.is_dir():
            return []
        return sorted(
            p.name for p in self.releases.iterdir()
            if p.is_dir() and not p.name.endswith(".staging") and not p.name.startswith(".")
        )

    def last_result(self) -> dict | None:
        try:
            return json.loads((self.state / STATUS_FILE).read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def status(self) -> dict:
        return {
            "current": self.current(),
            "previous": self.previous(),
            "available": self.available(),
            "last_result": self.last_result(),
        }

    # --- pipeline --------------------------------------------------------

    def stage(self, bundle_path: Path, allowed_signers: Path) -> str:
        """Steps 2–3: verify the signature, unpack to ``.staging``, rename into place.

        Any failure leaves nothing half-applied. Returns the staged version.
        """
        self.releases.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.releases, prefix=".incoming-") as tmp:
            payload = bundle.open_bundle(bundle_path, Path(tmp), allowed_signers)
            manifest = bundle.read_manifest(payload)
            version = manifest["version"]
            if version == self.current():
                raise ReleaseError(f"{version} is already the current release")
            staging = self.releases / f"{version}.staging"
            shutil.rmtree(staging, ignore_errors=True)
            try:
                bundle.extract(payload, staging, manifest)
            except BaseException:
                shutil.rmtree(staging, ignore_errors=True)
                raise
            final = self.releases / version
            if final.exists():
                shutil.rmtree(final)
            os.rename(staging, final)
        log.info("staged %s", version)
        return version

    def activate(self, version: str, restart: Restart, health: HealthCheck) -> Result:
        """Steps 4–7: migrate, swap, restart, health-check, roll back on failure."""
        if not (self.releases / version).is_dir():
            return self._record(Result(False, "activate", version, self.current(), "not staged"))
        old, old_prev = self.current(), self.previous()
        self._record_progress("activate", version, old)

        try:
            self._migrate(version)
        except ReleaseError as e:
            return self._record(Result(False, "activate", version, old, str(e)))

        self._point(self.current_link, version)
        if old and old != version:
            self._point(self.previous_link, old)
        ok, detail = self._restart_and_check(restart, health, version)
        if ok:
            self.prune()
            return self._record(Result(True, "activate", version, old, detail))

        log.error("%s failed health check (%s); rolling back to %s", version, detail, old)
        if old is None:
            return self._record(Result(False, "activate", version, None,
                                       f"health check failed: {detail}; no previous release"))
        self._point(self.current_link, old)
        self._point_or_clear(self.previous_link, old_prev)
        back_ok, back_detail = self._restart_and_check(restart, health, old)
        suffix = "" if back_ok else f"; {old} also unhealthy: {back_detail}"
        return self._record(Result(False, "activate", version, old,
                                   f"health check failed: {detail}; rolled back to {old}{suffix}"))

    def rollback(self, restart: Restart, health: HealthCheck) -> Result:
        """Manual rollback: swap ``current`` and ``previous``, then health-check."""
        cur, prev = self.current(), self.previous()
        if not prev or not (self.releases / prev).is_dir():
            return self._record(Result(False, "rollback", None, cur, "no previous release"))
        self._record_progress("rollback", prev, cur)
        self._point(self.current_link, prev)
        if cur:
            self._point(self.previous_link, cur)
        ok, detail = self._restart_and_check(restart, health, prev)
        if ok:
            return self._record(Result(True, "rollback", prev, cur, detail))
        # The previous release is broken too; go back to what was running.
        if cur:
            self._point(self.current_link, cur)
            self._point(self.previous_link, prev)
            self._restart_and_check(restart, health, cur)
        return self._record(Result(False, "rollback", prev, cur,
                                   f"health check failed: {detail}; stayed on {cur}"))

    def prune(self, extra: int = 1) -> None:
        """Keep ``current``, ``previous`` and the ``extra`` newest others; delete the rest."""
        protected = {self.current(), self.previous()}
        old = [v for v in self.available() if v not in protected]
        old.sort(key=lambda v: (self.releases / v).stat().st_mtime, reverse=True)
        for v in old[extra:]:
            shutil.rmtree(self.releases / v, ignore_errors=True)

    # --- internals -------------------------------------------------------

    def _migrate(self, version: str) -> None:
        root = self.releases / version
        env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(root), str(root / "vendor")])}
        r = subprocess.run(
            [self.python, "-m", "tower.migrate", "--state-dir", str(self.state)],
            cwd=root, env=env, capture_output=True, text=True, timeout=300,
        )
        if r.returncode != 0:
            tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["no output"]
            raise ReleaseError(f"migration failed: {tail[0]}")

    def _restart_and_check(self, restart: Restart, health: HealthCheck, version: str):
        try:
            restart()
        except Exception as e:  # noqa: BLE001 — any restart failure is a failed update
            return False, f"restart failed: {e}"
        try:
            return health(version)
        except Exception as e:  # noqa: BLE001
            return False, f"health check error: {e}"

    def _target(self, link: Path) -> str | None:
        try:
            return Path(os.readlink(link)).name
        except FileNotFoundError:
            return None

    def _point(self, link: Path, version: str) -> None:
        """Atomic: build the new link beside the old one, then rename over it."""
        tmp = link.with_name(link.name + ".new")
        tmp.unlink(missing_ok=True)
        os.symlink(Path("releases") / version, tmp)
        os.replace(tmp, link)

    def _point_or_clear(self, link: Path, version: str | None) -> None:
        if version:
            self._point(link, version)
        else:
            link.unlink(missing_ok=True)

    def _record_progress(self, action: str, version: str | None, previous: str | None) -> None:
        self._write_status({
            "result": "in_progress", "action": action, "version": version, "from": previous,
            "detail": "", "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    def _record(self, result: Result) -> Result:
        (log.info if result.ok else log.error)("%s %s: %s", result.action, result.version, result.detail)
        self._write_status(result.as_dict())
        return result

    def _write_status(self, data: dict) -> None:
        self.state.mkdir(parents=True, exist_ok=True)
        tmp = self.state / (STATUS_FILE + ".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n")
        os.replace(tmp, self.state / STATUS_FILE)
