"""Strike scheduling (design C3).

A pulse is not a strike. The photohead fires as the bell passes the sensor;
the clapper strikes a fixed interval later, which depends on the bell and
the stroke::

    t_strike = t_pulse_disciplined + offset(bell, stroke)

where the offset is the sound pack's (silence before the strike in the
recording) plus the tower's calibration (sensor position), in ms.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

STROKES = ("hand", "back")


class StrokeTracker:
    """Infers stroke by alternation per bell, seeded at handstroke.

    The sensor does not report rotation direction, so stroke is never inferred
    from it. ``reset()`` re-seeds every bell at handstroke: called on a gap that
    ends a touch, and from the "reset strokes" control.
    """

    def __init__(self) -> None:
        self._last: dict[int, str] = {}

    def next(self, bell: int) -> str:
        stroke = "back" if self._last.get(bell) == "hand" else "hand"
        self._last[bell] = stroke
        return stroke

    def reset(self) -> None:
        self._last.clear()


@dataclass
class Strike:
    bell: int
    stroke: str
    t_pulse: float
    t: float  # when it should sound


OffsetFn = Callable[[int, str], float]  # (bell, stroke) -> seconds


class StrikeScheduler:
    def __init__(self, offset: OffsetFn, touch_gap_s: float) -> None:
        self.offset = offset
        self.touch_gap_s = touch_gap_s
        self.strokes = StrokeTracker()
        self._last_pulse: float | None = None

    def strike(self, bell: int, t_pulse: float) -> Strike:
        if self._last_pulse is not None and t_pulse - self._last_pulse > self.touch_gap_s:
            self.strokes.reset()  # a pause long enough to end a touch: handstroke leads again
        self._last_pulse = t_pulse
        stroke = self.strokes.next(bell)
        return Strike(bell, stroke, t_pulse, t_pulse + self.offset(bell, stroke))

    def reset_strokes(self) -> None:
        self.strokes.reset()
