"""Injected clocks (design C2).

No component calls ``time.monotonic()`` inline. A ``Clock`` is passed in
everywhere: ``SystemClock`` in production, ``FakeClock`` in tests and in
``--fast`` runs, which is what makes the timing stack deterministic.
"""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float:
        """Monotonic seconds."""
        ...

    def sleep_until(self, t: float) -> None:
        """Block until ``now() >= t``. Returns immediately if ``t`` has passed."""
        ...


class SystemClock:
    def now(self) -> float:
        return time.monotonic()

    def sleep_until(self, t: float) -> None:
        delay = t - time.monotonic()
        if delay > 0:
            time.sleep(delay)


class FakeClock:
    """A clock that only moves when told to. ``sleep_until`` jumps forward instantly."""

    def __init__(self, start: float = 0.0) -> None:
        self._t = float(start)

    def now(self) -> float:
        return self._t

    def advance(self, dt: float) -> None:
        if dt < 0:
            raise ValueError("FakeClock cannot go backwards")
        self._t += dt

    def sleep_until(self, t: float) -> None:
        if t > self._t:
            self._t = float(t)
