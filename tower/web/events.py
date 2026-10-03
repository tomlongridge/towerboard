"""Event bus and SSE fan-out (design C5).

The bus receives envelopes from the RT process and from the app itself and
broadcasts them to every connected browser over Server-Sent Events, using the
same envelope on both hops.

Each client has a bounded queue that drops its *oldest* events when full: a
phone on a bad connection must never stall the wall display. Drops are
counted and shown in diagnostics. A client reconciles after a reconnect by
taking the current state snapshot sent on connect, not by replaying history.

A ``system`` heartbeat carrying the server's monotonic time goes out every
couple of seconds. Browsers use it to map envelope ``t`` onto their own clock
(the minimum of receipt − t, the same one-sided trick as clock discipline),
so a strike animates when the bell sounds rather than when the pulse arrived.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Any, Callable

from tower import ipc
from tower.clock import Clock
from tower.events import ContractError, Envelope, Sequencer, from_dict

log = logging.getLogger(__name__)

CLIENT_QUEUE = 256
HEARTBEAT_S = 2.0
RT_STALE_S = 10.0


class Subscriber:
    def __init__(self, maxlen: int = CLIENT_QUEUE) -> None:
        self.queue: deque[str] = deque(maxlen=maxlen)
        self.dropped = 0
        self.cond = threading.Condition()
        self.closed = False

    def put(self, line: str) -> None:
        with self.cond:
            if len(self.queue) == self.queue.maxlen:
                self.dropped += 1  # deque drops the oldest itself
            self.queue.append(line)
            self.cond.notify()

    def get(self, timeout: float) -> list[str]:
        with self.cond:
            if not self.queue and not self.closed:
                self.cond.wait(timeout)
            items = list(self.queue)
            self.queue.clear()
            return items


class EventBus:
    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.seq = Sequencer()  # for envelopes the app itself originates
        self._subs: set[Subscriber] = set()
        self._lock = threading.Lock()
        self.rt_status: dict | None = None
        self.rt_status_at: float | None = None
        self.rt_bad = 0
        self.dropped_total = 0  # from subscribers that have gone

    # --- publishing ------------------------------------------------------------

    def publish(self, env: Envelope) -> None:
        line = env.to_json()
        with self._lock:
            subs = list(self._subs)
        for s in subs:
            s.put(line)

    def emit(self, type_: str, payload: dict) -> None:
        self.publish(self.seq.emit(type_, self.clock.now(), payload))

    def on_rt(self, obj: Any) -> None:
        try:
            env = from_dict(obj)
        except ContractError as e:
            self.rt_bad += 1
            log.warning("bad envelope from RT: %s", e)
            return
        if env.type == "system" and isinstance(env.payload.get("rt"), dict):
            self.rt_status = dict(env.payload["rt"])
            self.rt_status_at = self.clock.now()
            return  # status is for the app; browsers get it via the state snapshot
        self.publish(env)

    def rt_fresh(self) -> bool:
        return self.rt_status_at is not None and self.clock.now() - self.rt_status_at < RT_STALE_S

    # --- subscribers -------------------------------------------------------------

    def subscribe(self) -> Subscriber:
        s = Subscriber()
        with self._lock:
            self._subs.add(s)
        return s

    def unsubscribe(self, s: Subscriber) -> None:
        with self._lock:
            self._subs.discard(s)
            self.dropped_total += s.dropped

    def stats(self) -> dict:
        with self._lock:
            subs = list(self._subs)
        return {"clients": len(subs), "dropped": self.dropped_total + sum(s.dropped for s in subs),
                "dropped_by_client": [s.dropped for s in subs]}

    # --- threads ------------------------------------------------------------------

    def run_receiver(self, receiver: ipc.Receiver, stop: threading.Event) -> None:
        while not stop.is_set():
            obj = receiver.recv(timeout=0.5)
            if obj is not None:
                self.on_rt(obj)

    def run_heartbeat(self, stop: threading.Event) -> None:
        while not stop.wait(HEARTBEAT_S):
            self.emit("system", {"heartbeat": True})


def stream(bus: EventBus, snapshot: Callable[[], dict], write: Callable[[bytes], None],
           stop: threading.Event, keepalive_s: float = HEARTBEAT_S) -> None:
    """Serve one SSE client until it goes away or ``stop`` is set."""
    sub = bus.subscribe()
    try:
        first = bus.seq.emit("state", bus.clock.now(), snapshot())
        write(b"retry: 2000\n" + _frame(first.to_json()))
        while not stop.is_set():
            lines = sub.get(timeout=keepalive_s)
            if lines:
                write(b"".join(_frame(line) for line in lines))
            else:
                write(b": keepalive\n\n")
    except (ConnectionError, OSError):
        pass
    finally:
        bus.unsubscribe(sub)


def _frame(line: str) -> bytes:
    return f"data: {line}\n\n".encode()


def control_sender(run_dir) -> ipc.Sender:
    return ipc.Sender(run_dir / ipc.CONTROL)

