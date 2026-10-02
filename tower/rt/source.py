"""Pulse sources (design C1).

Whatever the hardware emits becomes ``PulseEvent``s on one contract, so live,
synthetic and replay sources are interchangeable downstream. M0 ships the
synthetic source only; serial arrives in M2 and replay in M3.
"""

from __future__ import annotations

import heapq
import random
from dataclasses import dataclass, field
from typing import Iterator, Mapping, Protocol

from tower.clock import Clock


@dataclass(frozen=True, slots=True)
class PulseEvent:
    bell: int  # 1..16, bell number as rung
    t_src: float  # source timebase seconds (MCU clock if available)
    t_rx: float  # Pi monotonic at receipt
    seq: int


class PulseSource(Protocol):
    def __iter__(self) -> Iterator[PulseEvent]: ...


@dataclass(frozen=True)
class SyntheticParams:
    """Rounds on ``bells`` bells with Hawkear-style ideal timing plus noise.

    Ideal time of place ``i`` in row ``r`` (row 0 is a handstroke)::

        t = (r * bells + i) * gap + (r // 2) * uplift

    i.e. each handstroke after the first is preceded by an extra ``uplift``
    (the open handstroke lead). All times are in seconds.
    """

    bells: int = 8
    gap: float = 0.200
    uplift: float = 0.200
    error_sd: float = 0.010
    bell_error_sd: Mapping[int, float] = field(default_factory=dict)
    latency: float = 0.002  # fixed serial transport delay
    jitter: float = 0.001  # additional one-sided transport delay, uniform 0..jitter
    rows: int | None = None  # None runs forever
    seed: int = 0

    def __post_init__(self) -> None:
        if not 2 <= self.bells <= 16:
            raise ValueError(f"bells must be 2..16, got {self.bells}")
        if self.gap <= 0:
            raise ValueError("gap must be positive")
        if self.uplift < 0 or self.error_sd < 0 or self.latency < 0 or self.jitter < 0:
            raise ValueError("uplift, error_sd, latency and jitter must be non-negative")
        if self.rows is not None and self.rows < 0:
            raise ValueError("rows must be non-negative")
        for bell, sd in self.bell_error_sd.items():
            if not 1 <= bell <= self.bells or sd < 0:
                raise ValueError(f"bad per-bell error {bell}: {sd}")


class SyntheticSource:
    """Deterministic for a given seed when driven by a ``FakeClock``.

    Noise uses only ``random.random()`` and arithmetic (Irwin–Hall
    approximation to a normal), so output is bit-identical across platforms.
    """

    def __init__(self, params: SyntheticParams, clock: Clock) -> None:
        self.params = params
        self.clock = clock

    def __iter__(self) -> Iterator[PulseEvent]:
        p = self.params
        rng = random.Random(p.seed)
        # Errors are clamped to half a row, so a blow can only be overtaken by
        # blows from the adjacent row; generating one row ahead keeps order exact.
        max_err = p.bells * p.gap / 2
        lead_in = max_err + p.gap  # keeps t_src >= 0
        t0 = self.clock.now()

        pending: list[tuple[float, int]] = []  # (t_src, bell)
        next_row = 0

        def row_start(r: int) -> float:
            return lead_in + r * p.bells * p.gap + (r // 2) * p.uplift

        def generate_row() -> None:
            nonlocal next_row
            start = row_start(next_row)
            for place in range(p.bells):
                bell = place + 1
                sd = p.bell_error_sd.get(bell, p.error_sd)
                err = max(-max_err, min(max_err, _approx_normal(rng) * sd))
                heapq.heappush(pending, (start + place * p.gap + err, bell))
            next_row += 1

        def more_rows() -> bool:
            return p.rows is None or next_row < p.rows

        seq = 0
        last_rx = t0
        while True:
            while more_rows() and (not pending or pending[0][0] >= row_start(next_row) - max_err):
                generate_row()
            if not pending:
                return
            t_src, bell = heapq.heappop(pending)
            delay = p.latency + rng.random() * p.jitter
            # Serial is FIFO: a pulse can never arrive before the one ahead of it.
            target = max(last_rx, t0 + t_src + delay)
            self.clock.sleep_until(target)
            last_rx = self.clock.now()
            seq += 1
            yield PulseEvent(bell=bell, t_src=t_src, t_rx=last_rx, seq=seq)


def _approx_normal(rng: random.Random) -> float:
    return sum(rng.random() for _ in range(12)) - 6.0
