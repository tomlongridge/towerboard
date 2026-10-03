import unittest

import numpy as np

from tower.rt.jitter import analyse, find_onsets

RATE = 44100


def capture_for(times, t0, delay, jitter_s, rate=RATE, length_s=None):
    length_s = length_s or (times[-1] - t0 + 1)
    x = np.zeros(int(length_s * rate), dtype=np.int16)
    rng = np.random.default_rng(0)
    for t in times:
        i = int(round((t + delay + rng.uniform(-jitter_s, jitter_s) - t0) * rate))
        x[i:i + 40] = 20000
    return x


class JitterTest(unittest.TestCase):
    times = [10.0 + i * 0.2 for i in range(500)]

    def test_tight_timing_passes(self):
        x = capture_for(self.times, 9.5, delay=0.0123, jitter_s=0.0005)
        r = analyse(self.times, 9.5, x, RATE, min_gap_s=0.1)
        self.assertTrue(r.passed, str(r))
        self.assertAlmostEqual(r.median_delay_ms, 12.3, delta=0.2)

    def test_jitter_over_limit_fails(self):
        x = capture_for(self.times, 9.5, delay=0.01, jitter_s=0.02)
        r = analyse(self.times, 9.5, x, RATE, min_gap_s=0.1)
        self.assertFalse(r.passed)
        self.assertGreater(r.max_ms, 10)

    def test_missing_clicks_fail(self):
        x = capture_for(self.times[:-10], 9.5, delay=0.01, jitter_s=0.0, length_s=self.times[-1] - 9.5 + 1)
        r = analyse(self.times, 9.5, x, RATE, min_gap_s=0.1)
        self.assertFalse(r.passed)
        self.assertLess(r.detected, r.scheduled)

    def test_silence(self):
        r = analyse(self.times, 0, np.zeros(1000, np.int16), RATE, min_gap_s=0.1)
        self.assertFalse(r.passed)
        self.assertEqual(len(find_onsets(np.zeros(10), RATE, 0.1)), 0)
