"""Live pulse source: the photohead box over USB serial (design C1).

The box sends one character per sensor pulse at 2400 baud, the character
naming the bell. The default map is the ringers' symbols for bells 1..16
(``1``–``9``, ``0``, ``E``, ``T``, ``A``–``D``). Decoding works on raw bytes
and ignores case: an earlier implementation lost bells 11 and 12 because it
only handled one case of ``E`` and ``T``.

The box sends no timestamp of its own, so ``t_src`` is the receipt time and
clock discipline (C2) is the identity for this source. Timing quality
therefore depends on the USB latency timer: FTDI's 16 ms default adds jitter
well above what a ringer can hear. A udev rule shipped in the image sets it
to 1 ms; this source checks it on open and logs loudly if it is not.

Still to confirm against the real box: capture golden byte streams with
``python -m tower.rt.serial_source --capture`` and add them as tests.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from tower.clock import Clock
from tower.rt.source import PulseEvent

log = logging.getLogger(__name__)

SYSFS_USB_SERIAL = Path("/sys/bus/usb-serial/devices")


class SourceUnavailable(Exception):
    """The box is not connected, or its port cannot be opened."""


def build_charmap(chars: str) -> dict[int, int]:
    """Byte value → bell number, accepting both cases of every letter."""
    if len(chars) != 16 or len(set(chars.upper())) != 16:
        raise ValueError("charmap must be 16 distinct characters")
    table: dict[int, int] = {}
    for bell, ch in enumerate(chars, start=1):
        for variant in {ch.upper(), ch.lower()}:
            table[ord(variant)] = bell
    return table


def decode(data: bytes, table: dict[int, int]) -> tuple[list[int], int]:
    """Bells named by ``data``, plus a count of bytes that named no bell."""
    bells, unknown = [], 0
    for b in data:
        bell = table.get(b)
        if bell is None:
            if b not in (0x0A, 0x0D):  # line endings are framing, not noise
                unknown += 1
        else:
            bells.append(bell)
    return bells, unknown


def find_port(usb_ids: list[str]) -> str:
    """Resolve the box by USB vendor:product id."""
    from serial.tools import list_ports

    wanted = {tuple(int(x, 16) for x in uid.split(":")) for uid in usb_ids}
    matches = [p.device for p in list_ports.comports() if (p.vid, p.pid) in wanted]
    if not matches:
        raise SourceUnavailable(f"no serial device with USB id in {usb_ids}")
    if len(matches) > 1:
        log.warning("several matching serial devices %s; using %s", matches, matches[0])
    return sorted(matches)[0]


def check_latency_timer(port: str, sysfs: Path = SYSFS_USB_SERIAL) -> int | None:
    """The FTDI latency timer in ms, or None if the device has none (not FTDI, or not Linux)."""
    path = sysfs / Path(port).name / "latency_timer"
    try:
        value = int(path.read_text().strip())
    except (OSError, ValueError):
        return None
    if value > 1:
        log.error("USB latency timer on %s is %d ms, expected 1: strike timing will jitter. "
                  "Is the udev rule 99-tower-serial.rules installed?", port, value)
    return value


@dataclass
class SourceStats:
    port: str | None = None
    status: str = "not started"  # open | absent | error
    latency_timer_ms: int | None = None
    pulses: int = 0
    unknown_bytes: int = 0
    reopens: int = 0
    detail: str = ""

    def as_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class SerialSource:
    """Yields ``PulseEvent``s; reconnects if the box is unplugged and replugged.

    ``opener`` returns an object with ``read(n)`` (pyserial-like); injected for tests.
    """

    usb_ids: list[str]
    charmap: str
    clock: Clock
    port: str = ""
    baud: int = 2400
    opener: Callable[[str, int], object] | None = None
    retry_s: float = 2.0
    stop: threading.Event = field(default_factory=threading.Event)
    stats: SourceStats = field(default_factory=SourceStats)

    def __post_init__(self) -> None:
        self._table = build_charmap(self.charmap)

    def __iter__(self) -> Iterator[PulseEvent]:
        seq = 0
        while not self.stop.is_set():
            try:
                dev = self._open()
            except SourceUnavailable as e:
                self.stats.status, self.stats.detail = "absent", str(e)
                self.stop.wait(self.retry_s)
                continue
            try:
                while not self.stop.is_set():
                    data = dev.read(64)  # returns early on timeout or as soon as bytes arrive
                    if not data:
                        continue
                    t_rx = self.clock.now()
                    bells, unknown = decode(data, self._table)
                    self.stats.unknown_bytes += unknown
                    # Bytes read together arrived one character time apart; the last
                    # arrived at t_rx. 10 bits per character (start, 8 data, stop).
                    char_s = 10 / self.baud
                    for i, bell in enumerate(bells):
                        seq += 1
                        self.stats.pulses += 1
                        t = t_rx - (len(bells) - 1 - i) * char_s
                        yield PulseEvent(bell=bell, t_src=t, t_rx=t, seq=seq)
            except OSError as e:  # includes serial.SerialException: unplugged mid-touch
                log.error("serial read failed: %s", e)
                self.stats.status, self.stats.detail = "error", str(e)
                self.stats.reopens += 1
            finally:
                close = getattr(dev, "close", None)
                if close:
                    close()

    def _open(self):
        port = self.port or find_port(self.usb_ids)
        self.stats.port = port
        try:
            if self.opener:
                dev = self.opener(port, self.baud)
            else:
                import serial

                dev = serial.Serial(port, self.baud, timeout=0.2)
        except OSError as e:
            raise SourceUnavailable(f"cannot open {port}: {e}") from None
        self.stats.latency_timer_ms = check_latency_timer(port)
        self.stats.status, self.stats.detail = "open", ""
        log.info("photohead box on %s at %d baud", port, self.baud)
        return dev


def capture(port: str, baud: int, seconds: float, out: Path) -> int:
    """Record raw bytes from the box, for golden-stream tests. Returns the byte count."""
    import time

    import serial

    with serial.Serial(port, baud, timeout=0.2) as dev, out.open("wb") as f:
        end = time.monotonic() + seconds
        n = 0
        while time.monotonic() < end:
            data = dev.read(64)
            f.write(data)
            n += len(data)
    return n


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(prog="python -m tower.rt.serial_source")
    p.add_argument("--capture", type=Path, required=True, help="file to write raw bytes to")
    p.add_argument("--seconds", type=float, default=60)
    p.add_argument("--port", default="")
    p.add_argument("--baud", type=int, default=2400)
    a = p.parse_args()
    from tower.config import SerialSection

    port = a.port or find_port(SerialSection().usb_ids)
    print(f"captured {capture(port, a.baud, a.seconds, a.capture)} bytes from {port}")
