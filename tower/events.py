"""Event envelope — durable contract 3 (design C5).

One envelope for live, synthetic and replay, carried unchanged over the
RT→app socket and the app→browser SSE stream::

    {"schema_version": 1, "type": "strike", "seq": 10423, "t": 1234.5678,
     "payload": {"bell": 3, "stroke": "hand", "source": "live"}}

Compatibility rule
------------------
* ``schema_version`` is bumped only for incompatible changes: removing or
  renaming a field, or changing a field's meaning or type.
* Additive changes — new optional payload fields, new event types — do not
  bump it. Consumers must ignore payload fields and event types they do not
  understand.
* A reader rejects any envelope whose ``schema_version`` is newer than its
  own ``SCHEMA_VERSION``. Older versions are accepted only through an
  explicit upgrade step (there are none yet, as only version 1 exists).

``t`` is monotonic seconds on the Pi's timebase, serialised to microsecond
precision.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Mapping

SCHEMA_VERSION = 1

EVENT_TYPES = frozenset(
    {"strike", "row", "touch_start", "touch_end", "analysis", "state", "board", "system"}
)

STROKES = frozenset({"hand", "back"})
STRIKE_SOURCES = frozenset({"live", "synthetic", "replay", "simulated"})


class ContractError(ValueError):
    """An envelope does not satisfy the event contract."""


@dataclass(frozen=True, slots=True)
class Envelope:
    type: str
    seq: int
    t: float
    payload: Mapping[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.type, str) or not self.type:
            raise ContractError(f"type must be a non-empty string, got {self.type!r}")
        if not _is_int(self.seq) or self.seq < 0:
            raise ContractError(f"seq must be a non-negative integer, got {self.seq!r}")
        if not _is_number(self.t) or not math.isfinite(self.t):
            raise ContractError(f"t must be a finite number, got {self.t!r}")
        if not isinstance(self.payload, Mapping):
            raise ContractError(f"payload must be an object, got {type(self.payload).__name__}")
        if not _is_int(self.schema_version) or self.schema_version < 1:
            raise ContractError(f"schema_version must be a positive integer, got {self.schema_version!r}")
        if self.schema_version > SCHEMA_VERSION:
            raise ContractError(
                f"schema_version {self.schema_version} is newer than supported ({SCHEMA_VERSION})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "type": self.type,
            "seq": self.seq,
            "t": round(float(self.t), 6),
            "payload": dict(self.payload),
        }

    def to_json(self) -> str:
        """One line, no trailing newline. Suitable for JSONL, datagrams and SSE ``data:``."""
        return json.dumps(self.to_dict(), separators=(",", ":"), allow_nan=False)


def from_dict(d: Mapping[str, Any]) -> Envelope:
    if not isinstance(d, Mapping):
        raise ContractError("envelope must be a JSON object")
    missing = {"schema_version", "type", "seq", "t"} - d.keys()
    if missing:
        raise ContractError(f"envelope missing fields: {', '.join(sorted(missing))}")
    return Envelope(
        type=d["type"],
        seq=d["seq"],
        t=d["t"],
        payload=d.get("payload", {}),
        schema_version=d["schema_version"],
    )


def from_json(line: str | bytes) -> Envelope:
    try:
        d = json.loads(line)
    except json.JSONDecodeError as e:
        raise ContractError(f"invalid JSON: {e}") from None
    return from_dict(d)


def strike_payload(bell: int, stroke: str, source: str) -> dict[str, Any]:
    if not _is_int(bell) or not 1 <= bell <= 16:
        raise ContractError(f"bell must be 1..16, got {bell!r}")
    if stroke not in STROKES:
        raise ContractError(f"stroke must be one of {sorted(STROKES)}, got {stroke!r}")
    if source not in STRIKE_SOURCES:
        raise ContractError(f"source must be one of {sorted(STRIKE_SOURCES)}, got {source!r}")
    return {"bell": bell, "stroke": stroke, "source": source}


class Sequencer:
    """Stamps outgoing envelopes with a monotonically increasing ``seq``.

    Producers only emit known types; tolerance of unknown types is a consumer rule.
    """

    def __init__(self, start: int = 1) -> None:
        self._next = start

    def emit(self, type: str, t: float, payload: Mapping[str, Any] | None = None) -> Envelope:
        if type not in EVENT_TYPES:
            raise ContractError(f"unknown event type {type!r}")
        env = Envelope(type=type, seq=self._next, t=t, payload=payload or {})
        self._next += 1
        return env


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)
