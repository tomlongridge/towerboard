"""Best-effort wall-clock time (design C16, open question 5).

The Pi has no RTC and often no internet. Times within a session come from the
monotonic clock and are always right relative to each other; wall-clock time
only labels things ("Tuesday practice"). Sources, best first:

* ``ntp`` — systemd says the clock is synchronised.
* ``browser`` — an admin's phone supplied its time this boot. Kept as an offset
  from the system clock, never written to the system clock (that needs root
  and fights timesyncd). Tied to the boot id, because after a reboot the
  system clock restarts from whatever fake-hwclock saved.
* ``none`` — the system clock, untrusted.

Session headers (M3) record which source applied.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from tower.fsutil import atomic_write

BOOT_ID = Path("/proc/sys/kernel/random/boot_id")
MAX_PLAUSIBLE_S = 10 * 365 * 86400  # reject phones claiming to be a decade adrift


def _boot_id() -> str:
    try:
        return BOOT_ID.read_text().strip()
    except OSError:
        return "no-boot-id"  # not Linux: treat the process as one boot


def ntp_synchronised() -> bool:
    if not shutil.which("timedatectl"):
        return False
    try:
        r = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.stdout.strip() == "yes"


class WallClock:
    def __init__(self, path: Path, ntp=ntp_synchronised, system_time=time.time) -> None:
        self.path = path
        self._ntp_probe = ntp
        self._ntp_cache: tuple[float, bool] | None = None  # (checked at, result)
        self._system = system_time
        self._offset = 0.0
        self._source = "none"
        self._set_at: str | None = None
        try:
            data = json.loads(path.read_text())
            if data.get("boot_id") == _boot_id():
                self._offset = float(data["offset_s"])
                self._source = "browser"
                self._set_at = data.get("set_at")
        except (OSError, ValueError, KeyError):
            pass

    def _ntp(self) -> bool:
        now = time.monotonic()
        if self._ntp_cache is None or now - self._ntp_cache[0] > 30:
            self._ntp_cache = (now, self._ntp_probe())
        return self._ntp_cache[1]

    def source(self) -> str:
        return "ntp" if self._ntp() else self._source

    def now(self) -> float:
        return self._system() if self.source() == "ntp" else self._system() + self._offset

    def trusted(self) -> bool:
        return self.source() != "none"

    def accept_browser(self, browser_epoch_s: float) -> bool:
        """Record a phone's time unless NTP already holds. Returns whether it was used."""
        if self._ntp():
            return False
        offset = browser_epoch_s - self._system()
        if abs(offset) > MAX_PLAUSIBLE_S:
            raise ValueError("browser time is implausible")
        self._offset, self._source = offset, "browser"
        self._set_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        atomic_write(self.path, json.dumps({"boot_id": _boot_id(), "offset_s": offset, "set_at": self._set_at}))
        return True

    def status(self) -> dict:
        now = datetime.fromtimestamp(self.now(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"now": now, "source": self.source(), "trusted": self.trusted(),
                "browser_offset_s": round(self._offset, 1) if self._source == "browser" else None,
                "browser_set_at": self._set_at}
