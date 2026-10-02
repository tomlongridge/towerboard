import unittest

from tower.clock import FakeClock, SystemClock


class FakeClockTest(unittest.TestCase):
    def test_starts_where_told(self):
        self.assertEqual(FakeClock(5.0).now(), 5.0)

    def test_advance(self):
        c = FakeClock()
        c.advance(1.5)
        self.assertEqual(c.now(), 1.5)

    def test_cannot_go_backwards(self):
        with self.assertRaises(ValueError):
            FakeClock().advance(-1)

    def test_sleep_until_jumps_forward_only(self):
        c = FakeClock(10.0)
        c.sleep_until(12.0)
        self.assertEqual(c.now(), 12.0)
        c.sleep_until(11.0)
        self.assertEqual(c.now(), 12.0)


class SystemClockTest(unittest.TestCase):
    def test_monotonic_and_sleeps(self):
        c = SystemClock()
        t0 = c.now()
        c.sleep_until(t0 + 0.01)
        self.assertGreaterEqual(c.now(), t0 + 0.01)

    def test_sleep_until_past_returns_immediately(self):
        c = SystemClock()
        t0 = c.now()
        c.sleep_until(t0 - 10)
        self.assertLess(c.now() - t0, 0.05)
