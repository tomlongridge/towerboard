"""Clock discipline (design C2): map source timestamps onto the Pi's monotonic clock.

Transport delay is one-sided: serial can only make a pulse late, never early.
So over a window, the smallest ``t_rx - t_src`` is the best estimate of the
true offset between the two clocks. A strict minimum is poisoned by a single
glitched sample (a clock wrap, a bad timestamp), so the estimate is a low
percentile instead.

The window slides, which also tracks slow crystal drift between the box and
the Pi: at 50 ppm that is 3 ms a minute, inside one 60 s window. A gap longer
than the window re-seeds from scratch.

The same estimator anchors the audio output clock (``tower.rt.audio``),
where wake-ups after a blocking write are likewise only ever late.
"""

from __future__ import annotations

import bisect
from collections import deque


class OffsetEstimator:
    def __init__(self, window_s: float = 60.0, percentile: float = 2.0) -> None:
        if not 0 <= percentile < 50:
            raise ValueError("percentile must be in [0, 50)")
        self.window_s = window_s
        self.percentile = percentile
        self._samples: deque[tuple[float, float]] = deque()  # (t_rx, delta), oldest first
        self._sorted: list[float] = []  # deltas, for percentile lookup
        self.reseeds = 0

    def add(self, t_src: float, t_rx: float) -> None:
        if self._samples and t_rx - self._samples[-1][0] > self.window_s:
            self.reset()
            self.reseeds += 1
        delta = t_rx - t_src
        self._samples.append((t_rx, delta))
        bisect.insort(self._sorted, delta)
        while self._samples and t_rx - self._samples[0][0] > self.window_s:
            _, old = self._samples.popleft()
            del self._sorted[bisect.bisect_left(self._sorted, old)]

    @property
    def offset(self) -> float | None:
        """Estimated ``t_rx - t_src`` with transport delay removed, or None before any sample."""
        if not self._sorted:
            return None
        i = int(len(self._sorted) * self.percentile / 100)
        return self._sorted[i]

    def to_local(self, t_src: float) -> float:
        offset = self.offset
        return t_src if offset is None else t_src + offset

    def reset(self) -> None:
        self._samples.clear()
        self._sorted.clear()

    def __len__(self) -> int:
        return len(self._samples)
