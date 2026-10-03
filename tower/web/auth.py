"""Admin PIN (design C17).

Scope: network mode, updates, content upload, calibration, profile admin.
Deliberately *not* the simulator, the notice board display, or bell
claiming; keeping the PIN off the everyday path is what stops it being
written on the wall next to the QR code.

There is no shipped default PIN. Until one is set, the first person to open
the admin page sets it (as the README describes: the first user becomes
admin). If it is forgotten, delete ``<state>/admin.json`` from the SD card.
A damaged file (e.g. from a power cut on an older release) is reported as
such; it never falls back to "no PIN", which would let anyone set one.

The PIN is stored as a PBKDF2 hash. Sessions are random tokens held in
memory, so they end on restart, including after every update. Repeated
failures lock out login for a while, which makes a 4-digit PIN costly to
guess over WiFi.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
from pathlib import Path

from tower.clock import Clock
from tower.fsutil import atomic_write

PIN_RE = re.compile(r"^[0-9]{4,12}$")
ITERATIONS = 200_000
MAX_FAILURES = 5
LOCKOUT_S = 60.0


class AuthError(Exception):
    pass


class DamagedPinFile(AuthError):
    pass


class AdminAuth:
    def __init__(self, path: Path, clock: Clock, session_s: float) -> None:
        self.path = path
        self.clock = clock
        self.session_s = session_s
        self._sessions: dict[str, float] = {}  # token -> expiry
        self._failures = 0
        self._locked_until = 0.0
        self._lock = threading.Lock()

    def has_pin(self) -> bool:
        return self.path.is_file()

    def set_pin(self, new: str, current_token: str | None = None) -> str:
        """Set the first PIN, or change it from a valid session. Returns a fresh session token."""
        if not PIN_RE.match(new):
            raise AuthError("PIN must be 4 to 12 digits")
        with self._lock:
            if self.has_pin() and not self._valid(current_token):
                raise AuthError("log in to change the PIN")
            salt = secrets.token_bytes(16)
            data = {"salt": salt.hex(), "iterations": ITERATIONS, "hash": _hash(new, salt, ITERATIONS)}
            atomic_write(self.path, json.dumps(data) + "\n", 0o600)
            self._sessions.clear()  # a PIN change ends every other session
            return self._new_session()

    def login(self, pin: str) -> str:
        with self._lock:
            now = self.clock.now()
            if now < self._locked_until:
                raise AuthError(f"too many attempts; try again in {int(self._locked_until - now) + 1} s")
            if not self.has_pin():
                raise AuthError("no PIN set yet")
            stored = self._read()
            attempt = _hash(pin, bytes.fromhex(stored["salt"]), stored["iterations"])
            if not hmac.compare_digest(attempt, stored["hash"]):
                self._failures += 1
                if self._failures >= MAX_FAILURES:
                    self._failures = 0
                    self._locked_until = now + LOCKOUT_S
                raise AuthError("wrong PIN")
            self._failures = 0
            return self._new_session()

    def check(self, token: str | None) -> bool:
        with self._lock:
            return self._valid(token)

    def logout(self, token: str | None) -> None:
        with self._lock:
            self._sessions.pop(token or "", None)

    def _read(self) -> dict:
        try:
            stored = json.loads(self.path.read_text())
            bytes.fromhex(stored["salt"])
            int(stored["iterations"])
            str(stored["hash"])
            return stored
        except (OSError, ValueError, KeyError, TypeError):
            raise DamagedPinFile(
                f"the admin PIN file is damaged; delete {self.path} on the Pi to set a new PIN"
            ) from None

    def _valid(self, token: str | None) -> bool:
        if not token:
            return False
        expiry = self._sessions.get(token)
        if expiry is None:
            return False
        if self.clock.now() >= expiry:
            del self._sessions[token]
            return False
        return True

    def _new_session(self) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = self.clock.now() + self.session_s
        return token


def _hash(pin: str, salt: bytes, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, iterations).hex()
