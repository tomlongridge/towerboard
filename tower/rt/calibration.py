"""Per-tower strike offsets, calibrated by ear (design C4).

Ring open with the simulator sounding, and nudge each bell's handstroke and
backstroke offsets in 5 ms steps until the sound coincides with the real
bell. These belong to the tower (where the sensors sit), so they live in
state, never in the shipped sound pack.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

STEP_MS = 5.0
LIMIT_MS = 1500.0
STROKES = ("hand", "back")


class Calibration:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.offsets: dict[int, dict[str, float]] = {}
        self.load()

    def load(self) -> None:
        try:
            data = json.loads(self.path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        self.offsets = {
            int(b): {s: float(v.get(s, 0.0)) for s in STROKES}
            for b, v in data.get("offsets_ms", {}).items()
        }

    def get(self, bell: int, stroke: str) -> float:
        return self.offsets.get(bell, {}).get(stroke, 0.0)

    def set(self, bell: int, stroke: str, ms: float) -> float:
        if not 1 <= bell <= 16 or stroke not in STROKES:
            raise ValueError(f"bad bell/stroke {bell}/{stroke}")
        ms = max(-LIMIT_MS, min(LIMIT_MS, round(ms, 1)))
        self.offsets.setdefault(bell, {s: 0.0 for s in STROKES})[stroke] = ms
        return ms

    def nudge(self, bell: int, stroke: str, steps: int) -> float:
        return self.set(bell, stroke, self.get(bell, stroke) + steps * STEP_MS)

    def as_dict(self) -> dict[str, dict[str, float]]:
        return {str(b): dict(v) for b, v in sorted(self.offsets.items())}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"offsets_ms": self.as_dict()}, indent=2) + "\n")
        os.replace(tmp, self.path)
