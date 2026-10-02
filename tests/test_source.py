import unittest

from tower.clock import FakeClock
from tower.rt.source import SyntheticParams, SyntheticSource


def pulses(clock=None, **kw):
    return list(SyntheticSource(SyntheticParams(**kw), clock or FakeClock()))


class SyntheticSourceTest(unittest.TestCase):
    def test_one_pulse_per_bell_per_row(self):
        ps = pulses(bells=6, rows=10)
        self.assertEqual(len(ps), 60)
        for bell in range(1, 7):
            self.assertEqual(sum(p.bell == bell for p in ps), 10)

    def test_seq_and_times_monotonic(self):
        ps = pulses(rows=50, error_sd=0.05)
        self.assertEqual([p.seq for p in ps], list(range(1, len(ps) + 1)))
        for a, b in zip(ps, ps[1:]):
            self.assertLessEqual(a.t_src, b.t_src)
            self.assertLessEqual(a.t_rx, b.t_rx)

    def test_receipt_never_before_source(self):
        for p in pulses(rows=20):
            self.assertGreaterEqual(p.t_rx, p.t_src)

    def test_exact_ideal_timing_without_noise(self):
        ps = pulses(bells=4, rows=4, gap=0.25, uplift=0.25, error_sd=0, jitter=0, latency=0)
        lead_in = ps[0].t_src
        offsets = [round(p.t_src - lead_in, 9) for p in ps]
        # Rounds; handstroke gap (one extra beat) before rows 2 and 4 only.
        self.assertEqual(offsets, [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75,
                                   2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75, 4.0])
        self.assertEqual([p.bell for p in ps], [1, 2, 3, 4] * 4)

    def test_deterministic_for_seed(self):
        self.assertEqual(pulses(rows=20, seed=3), pulses(rows=20, seed=3))
        self.assertNotEqual(pulses(rows=20, seed=3), pulses(rows=20, seed=4))

    def test_drives_injected_clock(self):
        clock = FakeClock(100.0)
        ps = pulses(clock=clock, rows=5)
        self.assertEqual(clock.now(), ps[-1].t_rx)
        self.assertGreater(ps[0].t_rx, 100.0)

    def test_per_bell_error(self):
        ps = pulses(bells=4, rows=200, error_sd=0, bell_error_sd={3: 0.03}, jitter=0)
        lead_in = ps[0].t_src
        for p in ps:
            if p.bell != 3:
                residual = (p.t_src - lead_in) % 0.2
                self.assertAlmostEqual(min(residual, 0.2 - residual), 0, places=9)
        bell3 = [p for p in ps if p.bell == 3]
        self.assertTrue(any(abs(((p.t_src - lead_in) % 0.2) - 0.1) < 0.09 for p in bell3))

    def test_large_errors_still_ordered(self):
        ps = pulses(bells=4, rows=100, error_sd=0.2)
        self.assertEqual(len(ps), 400)
        self.assertEqual(sorted(ps, key=lambda p: p.t_src), ps)

    def test_zero_rows(self):
        self.assertEqual(pulses(rows=0), [])

    def test_unbounded_when_rows_none(self):
        it = iter(SyntheticSource(SyntheticParams(rows=None), FakeClock()))
        self.assertEqual(len([next(it) for _ in range(1000)]), 1000)

    def test_rejects_bad_params(self):
        for kw in ({"bells": 1}, {"bells": 17}, {"gap": 0}, {"error_sd": -1}, {"rows": -1},
                   {"bells": 4, "bell_error_sd": {5: 0.01}}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                SyntheticParams(**kw)
