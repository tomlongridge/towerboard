import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tower import wallclock
from tower.wallclock import WallClock


class WallClockTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "wallclock.json"
        self.sys_time = 1_000_000.0

    def clock(self, ntp=False):
        return WallClock(self.path, ntp=lambda: ntp, system_time=lambda: self.sys_time)

    def test_untrusted_by_default(self):
        c = self.clock()
        self.assertEqual((c.source(), c.trusted(), c.now()), ("none", False, self.sys_time))

    def test_browser_time_applied_as_offset_and_persisted(self):
        c = self.clock()
        self.assertTrue(c.accept_browser(self.sys_time + 3600))
        self.assertEqual((c.source(), c.now()), ("browser", self.sys_time + 3600))
        self.assertEqual(self.clock().now(), self.sys_time + 3600)  # same boot: kept

    def test_new_boot_forgets_browser_time(self):
        self.clock().accept_browser(self.sys_time + 3600)
        with mock.patch.object(wallclock, "_boot_id", return_value="another-boot"):
            self.assertEqual(self.clock().source(), "none")

    def test_ntp_wins(self):
        c = self.clock(ntp=True)
        self.assertFalse(c.accept_browser(self.sys_time + 3600))
        self.assertEqual((c.source(), c.now()), ("ntp", self.sys_time))

    def test_implausible_rejected(self):
        with self.assertRaises(ValueError):
            self.clock().accept_browser(self.sys_time + 20 * 365 * 86400)
