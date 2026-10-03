"""Local IPC between the RT and app processes (design §1.4, C5).

Two one-way Unix datagram sockets in the run directory, one JSON object per
datagram:

* ``events.sock`` — RT → app: event envelopes (contract 3), bound by the app.
* ``control.sock`` — app → RT: control commands, bound by the RT process.

Senders never block. If the receiver is missing, slow or full, the datagram
is dropped and counted: the app may never stall the RT process, and the
RT process does not care whether anyone is listening.
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any

EVENTS = "events.sock"
CONTROL = "control.sock"
MAX_DATAGRAM = 2048  # macOS's default limit for Unix datagrams; Linux allows far more


class Sender:
    def __init__(self, path: Path) -> None:
        self.path = str(path)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sent = 0
        self.dropped = 0

    def send(self, obj: Any) -> bool:
        data = json.dumps(obj, separators=(",", ":")).encode()
        if len(data) > MAX_DATAGRAM:
            self.dropped += 1
            return False
        try:
            self.sock.sendto(data, self.path)
        except (BlockingIOError, FileNotFoundError, ConnectionRefusedError, OSError):
            self.dropped += 1
            return False
        self.sent += 1
        return True

    def close(self) -> None:
        self.sock.close()


class Receiver:
    def __init__(self, path: Path, mode: int = 0o660) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.unlink()  # stale socket from a previous run
        except FileNotFoundError:
            pass
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind(str(path))
        os.chmod(path, mode)
        self.bad = 0

    def recv(self, timeout: float | None = None) -> Any | None:
        """One decoded object, or None on timeout. Malformed datagrams are counted and skipped."""
        self.sock.settimeout(timeout)
        try:
            data = self.sock.recv(65536)
        except (TimeoutError, socket.timeout):
            return None
        try:
            return json.loads(data)
        except ValueError:
            self.bad += 1
            return None

    def close(self) -> None:
        self.sock.close()
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
