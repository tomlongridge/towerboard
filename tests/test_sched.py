import unittest

from tower.rt.sched import StrokeTracker


class StrokeTrackerTest(unittest.TestCase):
    def test_alternates_per_bell_from_handstroke(self):
        s = StrokeTracker()
        self.assertEqual([s.next(1), s.next(2), s.next(1), s.next(2), s.next(1)],
                         ["hand", "hand", "back", "back", "hand"])

    def test_reset_reseeds_handstroke(self):
        s = StrokeTracker()
        s.next(1)
        s.reset()
        self.assertEqual(s.next(1), "hand")
