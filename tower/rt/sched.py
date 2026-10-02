"""Strike scheduling (design C3).

M0 carries only stroke inference. Per-bell strike offsets, audio lead time
and lateness metrics arrive with the audio engine in M2.
"""

from __future__ import annotations


class StrokeTracker:
    """Infers stroke by alternation per bell, seeded at handstroke.

    The sensor does not report rotation direction, so stroke is never inferred
    from it. Call ``reset()`` on a gap that ends a touch (handstroke leads).
    """

    def __init__(self) -> None:
        self._last: dict[int, str] = {}

    def next(self, bell: int) -> str:
        stroke = "back" if self._last.get(bell) == "hand" else "hand"
        self._last[bell] = stroke
        return stroke

    def reset(self) -> None:
        self._last.clear()
