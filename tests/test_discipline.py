import random
import unittest

from tower.rt.discipline import OffsetEstimator


class OffsetEstimatorTest(unittest.TestCase):
    def test_recovers_offset_through_one_sided_jitter(self):
        rng = random.Random(1)
        est = OffsetEstimator()
        for i in range(2000):
            t_src = i * 0.2
            est.add(t_src, t_src + 1000.0 + 0.002 + rng.expovariate(1 / 0.004))
        self.assertAlmostEqual(est.offset, 1000.002, delta=0.0005)

    def test_one_bad_sample_does_not_poison(self):
        est = OffsetEstimator()
        for i in range(500):
            est.add(i * 0.1, i * 0.1 + 5.0 + 0.003)
        est.add(50.0, 50.0 + 4.0)  # a glitch: one second early
        self.assertAlmostEqual(est.offset, 5.003, places=6)

    def test_window_slides_to_track_drift(self):
        est = OffsetEstimator(window_s=10)
        for i in range(400):  # 40 s; offset drifts by 1 ms per 10 s
            t = i * 0.1
            est.add(t, t + 2.0 + t * 0.0001)
        self.assertAlmostEqual(est.offset, 2.003, delta=0.0002)
        self.assertLessEqual(len(est), 101)

    def test_reseed_after_long_gap(self):
        est = OffsetEstimator(window_s=10)
        est.add(0, 1.0)
        est.add(100, 103.0)
        self.assertEqual(est.offset, 3.0)
        self.assertEqual(est.reseeds, 1)

    def test_identity_before_samples(self):
        est = OffsetEstimator()
        self.assertIsNone(est.offset)
        self.assertEqual(est.to_local(12.5), 12.5)
