"""Audio engine (design C4): one output stream, in-process mixing, sample-accurate strikes.

All samples are pre-decoded to float32 in RAM. One playback stream; every
period, active voices are summed into the period buffer. A stream per bell
does not give reliable inter-bell timing.

When does frame ``f`` play? Blocking writes pace the loop: a write returns
once the device has room for one more period, so at that moment the buffer
is full and the next frame written plays ``buffer_frames / rate`` later. The
return can only be *late* (scheduling), never early, so the low-percentile
estimator from clock discipline turns the noisy return times into a stable
anchor. A strike due inside a period starts at the matching sample offset
within it. A strike already in the past (a late pulse) plays at once and its
lateness is counted, never dropped.

Outputs:

* ``AlsaOutput`` — the Pi. ``pyalsaaudio`` from Debian (``python3-alsaaudio``).
* ``WavOutput`` — writes a WAV file and models a real device's buffer on an
  injected clock. With ``FakeClock`` it renders deterministically, which is
  how timing is tested off the Pi. It is a recorder, not a stand-in for ALSA.
"""

from __future__ import annotations

import heapq
import logging
import threading
import wave
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

from tower.clock import Clock
from tower.rt.discipline import OffsetEstimator
from tower.rt.soundpack import SoundPack

log = logging.getLogger(__name__)


class AudioOutput(Protocol):
    rate: int
    channels: int
    period_frames: int
    buffer_frames: int

    def write(self, pcm: bytes) -> None:
        """Queue one period of interleaved S16_LE; blocks until the device has room."""
        ...

    def close(self) -> None: ...


class AudioUnavailable(Exception):
    pass


class AlsaOutput:
    def __init__(self, device: str, rate: int, channels: int, period_frames: int, periods: int) -> None:
        try:
            import alsaaudio
        except ImportError:
            raise AudioUnavailable("pyalsaaudio is not installed (apt install python3-alsaaudio)") from None
        try:
            try:
                self.pcm = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, alsaaudio.PCM_NORMAL, device=device,
                                         rate=rate, channels=channels, format=alsaaudio.PCM_FORMAT_S16_LE,
                                         periodsize=period_frames, periods=periods)
            except TypeError:  # pyalsaaudio before 0.10 has no `periods`
                self.pcm = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, alsaaudio.PCM_NORMAL, device=device,
                                         rate=rate, channels=channels, format=alsaaudio.PCM_FORMAT_S16_LE,
                                         periodsize=period_frames)
        except alsaaudio.ALSAAudioError as e:
            raise AudioUnavailable(f"cannot open ALSA device {device!r}: {e}") from None
        self.rate, self.channels = rate, channels
        self.period_frames = period_frames
        self.buffer_frames = period_frames * periods
        info = getattr(self.pcm, "info", None)
        if info:  # the device may round what was asked for
            try:
                actual = info()
                self.rate = actual.get("rate", rate)
                self.period_frames = actual.get("period_size", period_frames)
                self.buffer_frames = actual.get("buffer_size", self.buffer_frames)
            except Exception:  # noqa: BLE001 — info() is best effort
                pass
        self.device = device

    def write(self, pcm: bytes) -> None:
        self.pcm.write(pcm)

    def close(self) -> None:
        self.pcm.close()


class WavOutput:
    """Records to a WAV file, pacing writes like a device with ``periods`` buffered periods."""

    def __init__(self, path: Path, clock: Clock, rate: int = 44100, channels: int = 2,
                 period_frames: int = 256, periods: int = 3) -> None:
        self.rate, self.channels = rate, channels
        self.period_frames = period_frames
        self.buffer_frames = period_frames * periods
        self.clock = clock
        self._w = wave.open(str(path), "wb")
        self._w.setnchannels(channels)
        self._w.setsampwidth(2)
        self._w.setframerate(rate)
        self.written = 0
        self.started: float | None = None  # when frame 0 played

    def write(self, pcm: bytes) -> None:
        frames = len(pcm) // (2 * self.channels)
        if self.started is None:
            # Like ALSA's default start threshold: playback begins once the buffer is full.
            if self.written + frames >= self.buffer_frames:
                self.started = self.clock.now()
        else:
            played = (self.clock.now() - self.started) * self.rate
            if self.written - played + frames > self.buffer_frames:
                self.clock.sleep_until(self.started + (self.written + frames - self.buffer_frames) / self.rate)
        self._w.writeframes(pcm)
        self.written += frames

    def close(self) -> None:
        self._w.close()


@dataclass
class _Voice:
    bell: int
    samples: np.ndarray
    pos: int = 0


@dataclass
class AudioStats:
    status: str = "not started"
    device: str = ""
    periods: int = 0
    strikes: int = 0
    late: int = 0  # strikes whose time had passed when their period was rendered
    max_late_ms: float = 0.0
    steals: int = 0
    resyncs: int = 0  # output clock jumps (underruns), re-anchored
    missing_bell: int = 0  # strikes for a bell the pack does not have
    detail: str = ""

    def as_dict(self) -> dict:
        return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


@dataclass(order=True)
class _Pending:
    t: float
    seq: int
    bell: int = field(compare=False)


class AudioEngine:
    def __init__(self, output: AudioOutput, pack: SoundPack, clock: Clock,
                 voices: int = 48, volume_db: float = -6.0) -> None:
        if pack.rate != output.rate:
            raise ValueError(f"pack is {pack.rate} Hz but output is {output.rate} Hz")
        self.out = output
        self.clock = clock
        self.max_voices = voices
        self.stats = AudioStats(device=getattr(output, "device", type(output).__name__))
        self._pack = pack
        self._gain = np.float32(10 ** (volume_db / 20))
        self._pending: list[_Pending] = []
        self._seq = 0
        self._lock = threading.Lock()
        self._voices: deque[_Voice] = deque()
        self._written = 0
        # Output clock anchor: play time of frame f = f / rate + offset + buffer / rate.
        self._anchor = OffsetEstimator(window_s=10.0, percentile=5.0)
        self._recent: deque[tuple[float, float]] = deque(maxlen=64)  # (frames as s, return time)
        self.stop = threading.Event()

    # --- control (any thread) ------------------------------------------------

    def schedule(self, bell: int, t: float) -> None:
        with self._lock:
            self._seq += 1
            heapq.heappush(self._pending, _Pending(t, self._seq, bell))

    def set_pack(self, pack: SoundPack) -> None:
        if pack.rate != self.out.rate:
            raise ValueError(f"pack is {pack.rate} Hz but output is {self.out.rate} Hz")
        with self._lock:
            self._pack = pack

    def set_volume(self, volume_db: float) -> None:
        self._gain = np.float32(10 ** (volume_db / 20))

    @property
    def pack(self) -> SoundPack:
        return self._pack

    def frame_time(self, frame: int) -> float | None:
        """Monotonic time at which ``frame`` plays, once the anchor has a sample."""
        offset = self._anchor.offset
        if offset is None:
            return None
        return (frame + self.out.buffer_frames) / self.out.rate + offset

    # --- render loop (audio thread) ----------------------------------------------

    def run(self) -> None:
        self.stats.status = "ok"
        try:
            while not self.stop.is_set():
                self.render_period()
        finally:
            self.stats.status = "stopped"

    def render_period(self) -> None:
        p = self.out.period_frames
        start = self._written
        t0 = self.frame_time(start)
        mix = np.zeros(p, dtype=np.float32)
        if t0 is not None:
            self._start_due_voices(t0, p)
        self._mix_voices(mix)
        self._write(mix)

    def _start_due_voices(self, t0: float, p: int) -> None:
        rate = self.out.rate
        t_end = t0 + p / rate
        due: list[tuple[int, int]] = []
        with self._lock:
            while self._pending and self._pending[0].t < t_end:
                item = heapq.heappop(self._pending)
                offset = int(round((item.t - t0) * rate))
                if offset < 0:
                    self.stats.late += 1
                    self.stats.max_late_ms = max(self.stats.max_late_ms, -offset * 1000 / rate)
                    offset = 0
                due.append((min(offset, p - 1), item.bell))
            pack = self._pack
        for offset, bell in due:
            b = pack.bells.get(bell)
            self.stats.strikes += 1
            if b is None:
                self.stats.missing_bell += 1
                continue
            if len(self._voices) >= self.max_voices:
                self._voices.popleft()  # steal the oldest
                self.stats.steals += 1
            # A voice starting mid-period is represented by leading silence.
            self._voices.append(_Voice(bell, b.samples, pos=-offset))

    def _mix_voices(self, mix: np.ndarray) -> None:
        p = len(mix)
        keep: deque[_Voice] = deque()
        for v in self._voices:
            dst = max(0, -v.pos)
            src = max(0, v.pos)
            n = min(p - dst, len(v.samples) - src)
            if n > 0:
                mix[dst:dst + n] += v.samples[src:src + n]
            v.pos += p
            if v.pos < len(v.samples):
                keep.append(v)
        self._voices = keep

    def _write(self, mix: np.ndarray) -> None:
        mix *= self._gain
        np.clip(mix, -1.0, 1.0, out=mix)
        pcm = (mix * 32767).astype("<i2")
        if self.out.channels == 2:
            pcm = np.repeat(pcm, 2)
        self.out.write(pcm.tobytes())
        self._written += len(mix)
        self.stats.periods += 1
        self._observe(self.clock.now())

    def _observe(self, t_return: float) -> None:
        """Feed the anchor; detect an underrun as the whole recent window jumping late."""
        t_frames = self._written / self.out.rate
        self._recent.append((t_frames, t_return))
        offset = self._anchor.offset
        if offset is not None and len(self._recent) == self._recent.maxlen:
            jump = min(r - f for f, r in self._recent) - offset
            if jump > 2 * self.out.period_frames / self.out.rate:
                self.stats.resyncs += 1
                log.warning("audio output clock jumped %.1f ms (underrun?); re-anchoring", jump * 1000)
                self._anchor.reset()
                for f, r in self._recent:
                    self._anchor.add(f, r)
                return
        self._anchor.add(t_frames, t_return)
