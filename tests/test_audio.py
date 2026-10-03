"""Audio engine timing on a fake clock, recorded through WavOutput. Pi-only: real ALSA (rt-jitter)."""

import tempfile
import threading
import unittest
import wave
from pathlib import Path

import numpy as np

from tower.clock import FakeClock
from tower.rt.audio import AudioEngine, WavOutput
from tower.rt.soundpack import Bell, SoundPack

RATE = 44100


def impulse_pack(bells=4, length=100):
    out = {}
    for b in range(1, bells + 1):
        x = np.zeros(length, np.float32)
        x[0] = 0.1 * b  # amplitude identifies the bell
        out[b] = Bell(b, x)
    return SoundPack("imp", "Impulses", RATE, out)


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "out.wav"
        self.clock = FakeClock(1000.0)
        self.out = WavOutput(self.path, self.clock, RATE, channels=1, period_frames=256, periods=3)

    def engine(self, pack=None, **kw):
        return AudioEngine(self.out, pack or impulse_pack(), self.clock, volume_db=0.0, **kw)

    def samples(self):
        self.out.close()
        with wave.open(str(self.path)) as w:
            return np.frombuffer(w.readframes(w.getnframes()), "<i2")

    def run_until(self, eng, t):
        while self.clock.now() < t:
            eng.render_period()

    def test_strikes_land_on_the_right_sample(self):
        eng = self.engine()
        self.run_until(eng, 1000.1)
        rng = np.random.default_rng(3)
        times = np.sort(self.clock.now() + 0.1 + rng.uniform(0, 3, 200))
        times = times[np.concatenate(([True], np.diff(times) > 0.004))]
        for t in times:
            eng.schedule(1, float(t))
        self.run_until(eng, times[-1] + 0.1)
        x = self.samples()
        onsets = np.flatnonzero(x)
        expected = np.round((times - self.out.started) * RATE).astype(int)
        self.assertEqual(len(onsets), len(expected))
        self.assertLessEqual(int(np.max(np.abs(onsets - expected))), 1)  # within one sample
        self.assertEqual(eng.stats.late, 0)

    def test_late_strike_plays_immediately_and_is_counted(self):
        eng = self.engine()
        self.run_until(eng, 1000.1)
        eng.schedule(2, self.clock.now() - 0.05)  # already in the past
        self.run_until(eng, 1000.2)
        self.assertEqual(eng.stats.late, 1)
        self.assertGreater(eng.stats.max_late_ms, 50)
        self.assertEqual(len(np.flatnonzero(self.samples())), 1)  # played, not dropped

    def test_voices_overlap_and_mix(self):
        pack = SoundPack("c", "Const", RATE, {1: Bell(1, np.full(4000, 0.1, np.float32)),
                                             2: Bell(2, np.full(4000, 0.2, np.float32))})
        eng = self.engine(pack)
        self.run_until(eng, 1000.1)
        t = self.clock.now() + 0.05
        eng.schedule(1, t)
        eng.schedule(2, t + 0.01)
        self.run_until(eng, t + 0.2)
        x = self.samples()
        self.assertAlmostEqual(x.max() / 32767, 0.3, places=2)

    def test_voice_stealing(self):
        pack = SoundPack("c", "Const", RATE, {1: Bell(1, np.full(RATE, 0.01, np.float32))})
        eng = self.engine(pack, voices=3)
        self.run_until(eng, 1000.1)
        for i in range(5):
            eng.schedule(1, self.clock.now() + 0.05 + i * 0.01)
        self.run_until(eng, 1000.3)
        self.assertEqual(eng.stats.steals, 2)

    def test_missing_bell_counted(self):
        eng = self.engine()
        self.run_until(eng, 1000.1)
        eng.schedule(9, self.clock.now() + 0.05)
        self.run_until(eng, 1000.3)
        self.assertEqual(eng.stats.missing_bell, 1)

    def test_clipping_and_volume(self):
        pack = SoundPack("c", "Loud", RATE, {1: Bell(1, np.full(1000, 0.9, np.float32))})
        eng = self.engine(pack)
        eng.set_volume(12.0)
        self.run_until(eng, 1000.1)
        eng.schedule(1, self.clock.now() + 0.05)
        eng.schedule(1, self.clock.now() + 0.05)
        self.run_until(eng, 1000.3)
        self.assertEqual(int(self.samples().max()), 32767)

    def test_rate_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            AudioEngine(self.out, SoundPack("x", "x", 48000, {}), self.clock)

    def test_underrun_reanchors(self):
        eng = self.engine()
        self.run_until(eng, 1000.5)
        self.clock.advance(0.2)  # the device starved: playback resumes later than expected
        self.out.started += 0.2
        self.run_until(eng, 1001.5)
        self.assertEqual(eng.stats.resyncs, 1)
        t = self.clock.now() + 0.1
        eng.schedule(1, t)
        self.run_until(eng, t + 0.1)
        onset = np.flatnonzero(self.samples())[0]
        self.assertLessEqual(abs(onset - round((t - self.out.started) * RATE)), 1)

    def test_schedule_is_thread_safe(self):
        eng = self.engine()
        self.run_until(eng, 1000.1)
        base = self.clock.now() + 0.2
        threads = [threading.Thread(target=lambda k=k: [eng.schedule(1, base + (k * 50 + i) * 0.003)
                                                         for i in range(50)]) for k in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.run_until(eng, base + 1.0)
        self.assertEqual(eng.stats.strikes, 200)
