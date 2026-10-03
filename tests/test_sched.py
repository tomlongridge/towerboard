import tempfile
import unittest
from pathlib import Path

from tower.rt.calibration import Calibration
from tower.rt.sched import StrikeScheduler, StrokeTracker


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


class StrikeSchedulerTest(unittest.TestCase):
    def test_offsets_per_bell_and_stroke(self):
        offsets = {(1, "hand"): 0.25, (1, "back"): 0.30}
        s = StrikeScheduler(lambda b, st: offsets[(b, st)], touch_gap_s=4)
        a, b = s.strike(1, 10.0), s.strike(1, 12.0)
        self.assertEqual((a.stroke, a.t), ("hand", 10.25))
        self.assertEqual((b.stroke, b.t), ("back", 12.30))

    def test_gap_ends_touch_and_reseeds(self):
        s = StrikeScheduler(lambda b, st: 0.0, touch_gap_s=4)
        self.assertEqual(s.strike(1, 0.0).stroke, "hand")
        self.assertEqual(s.strike(1, 2.0).stroke, "back")
        self.assertEqual(s.strike(1, 3.0).stroke, "hand")
        self.assertEqual(s.strike(1, 10.0).stroke, "hand")  # 7 s pause: new touch


class CalibrationTest(unittest.TestCase):
    def test_nudge_save_load(self):
        path = Path(tempfile.mkdtemp()) / "calibration.json"
        c = Calibration(path)
        self.assertEqual(c.nudge(3, "hand", 2), 10.0)
        self.assertEqual(c.nudge(3, "hand", -1), 5.0)
        c.set(4, "back", 123.4)
        c.save()
        again = Calibration(path)
        self.assertEqual((again.get(3, "hand"), again.get(4, "back"), again.get(9, "hand")), (5.0, 123.4, 0.0))

    def test_limits(self):
        c = Calibration(Path(tempfile.mkdtemp()) / "c.json")
        self.assertEqual(c.set(1, "hand", 99999), 1500.0)
        for bad in ((0, "hand"), (17, "hand"), (1, "sideways")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                c.set(*bad, 0)
