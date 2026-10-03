"""Audio jitter harness (design C4): the gate before any audio-path release.

Plays clicks through the real engine at scheduled times while capturing the
output through a loopback cable (line out → line in, or a USB card's own
loopback), finds each click in the recording, and compares when it sounded
with when it was scheduled. The absolute delay through the cable is unknown
and constant, so it is removed (median residual); what remains is jitter.

    python -m tower rt-jitter --capture hw:1,0 --blows 3000

Exits non-zero if any click lands more than 10 ms from where it should.
Runs on the desk Pi only: it needs real ALSA playback and capture.
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
from dataclasses import dataclass
from typing import Sequence

import numpy as np

log = logging.getLogger(__name__)

LIMIT_MS = 10.0


@dataclass
class JitterReport:
    scheduled: int
    detected: int
    median_delay_ms: float
    sd_ms: float
    p99_ms: float
    max_ms: float

    @property
    def passed(self) -> bool:
        return self.detected == self.scheduled and self.max_ms < LIMIT_MS

    def __str__(self) -> str:
        verdict = "PASS" if self.passed else "FAIL"
        return (f"{verdict}: {self.detected}/{self.scheduled} clicks found; delay {self.median_delay_ms:.2f} ms; "
                f"jitter sd {self.sd_ms:.2f} ms, p99 {self.p99_ms:.2f} ms, max {self.max_ms:.2f} ms "
                f"(limit {LIMIT_MS:.0f} ms)")


def find_onsets(x: np.ndarray, rate: int, min_gap_s: float, threshold: float = 0.3) -> np.ndarray:
    """Sample indices where the signal first crosses ``threshold × peak`` after a quiet gap."""
    level = np.abs(x.astype(np.float32))
    peak = float(level.max()) if len(level) else 0.0
    if peak == 0:
        return np.array([], dtype=np.int64)
    hot = np.flatnonzero(level > threshold * peak)
    if len(hot) == 0:
        return hot
    gap = int(min_gap_s * rate)
    keep = np.concatenate(([True], np.diff(hot) > gap))
    return hot[keep]


def analyse(scheduled: Sequence[float], capture_t0: float, capture: np.ndarray, rate: int,
            min_gap_s: float) -> JitterReport:
    """``capture_t0`` is the monotonic time of capture sample 0 (approximate; only differences matter)."""
    onsets = find_onsets(capture, rate, min_gap_s)
    sched = np.asarray(scheduled, dtype=np.float64)
    heard = capture_t0 + onsets / rate
    if len(heard) == 0:
        return JitterReport(len(sched), 0, float("nan"), float("nan"), float("nan"), float("inf"))
    # Pair each scheduled click with the first onset after it (loopback only adds delay).
    idx = np.searchsorted(heard, sched)
    valid = idx < len(heard)
    residual = heard[idx[valid]] - sched[valid]
    # Different scheduled clicks must not claim the same onset.
    unique = len(np.unique(idx[valid]))
    delay = float(np.median(residual))
    err_ms = np.abs(residual - delay) * 1000
    return JitterReport(
        scheduled=len(sched), detected=unique, median_delay_ms=delay * 1000,
        sd_ms=float(np.std(err_ms)), p99_ms=float(np.percentile(err_ms, 99)), max_ms=float(err_ms.max()),
    )


def click_pack(rate: int):
    from tower.rt.soundpack import Bell, SoundPack

    click = np.zeros(int(0.005 * rate), dtype=np.float32)
    click[: int(0.001 * rate)] = 0.8  # 1 ms square pulse: an unambiguous onset
    return SoundPack("click", "Click", rate, {1: Bell(1, click)})


def run(device: str, capture_device: str, blows: int, gap_s: float, rate: int,
        period_frames: int, periods: int) -> JitterReport:
    import alsaaudio

    from tower.clock import SystemClock
    from tower.rt.audio import AlsaOutput, AudioEngine

    clock = SystemClock()
    out = AlsaOutput(device, rate, 1, period_frames, periods)
    engine = AudioEngine(out, click_pack(rate), clock, voices=8, volume_db=0.0)
    cap = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, device=capture_device,
                        rate=rate, channels=1, format=alsaaudio.PCM_FORMAT_S16_LE, periodsize=period_frames)
    chunks: list[bytes] = []
    stop = threading.Event()
    t0_holder: list[float] = []

    def capture() -> None:
        while not stop.is_set():
            n, data = cap.read()
            if n > 0:
                if not t0_holder:  # first chunk ended now: back-date to its first sample
                    t0_holder.append(clock.now() - n / rate)
                chunks.append(data)

    threading.Thread(target=capture, daemon=True).start()
    audio = threading.Thread(target=engine.run, daemon=True)
    audio.start()
    clock.sleep_until(clock.now() + 1.0)  # let the output anchor settle

    # Schedule like the RT process does: a little ahead, from another thread, with
    # irregular gaps so periods and clicks never fall into step.
    rng = np.random.default_rng(0)
    t = clock.now() + 0.5
    scheduled = []
    for _ in range(blows):
        clock.sleep_until(t - 0.15)
        engine.schedule(1, t)
        scheduled.append(t)
        t += gap_s * rng.uniform(0.8, 1.2)
    clock.sleep_until(t + 0.5)
    engine.stop.set()
    stop.set()
    audio.join(2)
    x = np.frombuffer(b"".join(chunks), dtype="<i2")
    log.info("engine: %s", engine.stats.as_dict())
    return analyse(scheduled, t0_holder[0], x, rate, min_gap_s=gap_s * 0.5)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m tower rt-jitter", description=__doc__.split("\n\n")[0])
    p.add_argument("--device", default="default", help="ALSA playback device")
    p.add_argument("--capture", required=True, help="ALSA capture device on the loopback")
    p.add_argument("--blows", type=int, default=3000)
    p.add_argument("--gap-ms", type=float, default=200.0)
    p.add_argument("--rate", type=int, default=44100)
    p.add_argument("--period", type=int, default=256)
    p.add_argument("--periods", type=int, default=3)
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    report = run(a.device, a.capture, a.blows, a.gap_ms / 1000, a.rate, a.period, a.periods)
    print(report)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
