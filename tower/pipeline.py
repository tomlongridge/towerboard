"""Wires a pulse source to the event contract.

M0 writes envelopes as JSON lines. In M2 the same envelopes go over the
RT→app datagram socket instead.
"""

from __future__ import annotations

from typing import TextIO

from tower.events import Sequencer, strike_payload
from tower.rt.sched import StrokeTracker
from tower.rt.source import PulseSource


def run(source: PulseSource, out: TextIO, source_name: str) -> int:
    """Emit one ``strike`` envelope per pulse. Returns the number emitted."""
    seq = Sequencer()
    strokes = StrokeTracker()
    n = 0
    for pulse in source:
        env = seq.emit(
            "strike", pulse.t_rx, strike_payload(pulse.bell, strokes.next(pulse.bell), source_name)
        )
        out.write(env.to_json() + "\n")
        out.flush()
        n += 1
    return n
