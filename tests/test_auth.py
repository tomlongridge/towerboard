import tempfile
import unittest
from pathlib import Path

from tower.clock import FakeClock
from tower.web import auth
from tower.web.auth import AdminAuth, AuthError, DamagedPinFile


class AdminAuthTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.path = Path(tempfile.mkdtemp()) / "admin.json"
        self.auth = AdminAuth(self.path, self.clock, session_s=3600)

    def test_first_pin_sets_and_logs_in(self):
        self.assertFalse(self.auth.has_pin())
        token = self.auth.set_pin("1234")
        self.assertTrue(self.auth.has_pin())
        self.assertTrue(self.auth.check(token))
        self.assertNotIn("1234", self.path.read_text())
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_pin_format(self):
        for bad in ("123", "abcd", "1234567890123", "12 34", ""):
            with self.subTest(pin=bad), self.assertRaises(AuthError):
                self.auth.set_pin(bad)

    def test_login(self):
        self.auth.set_pin("1234")
        self.assertTrue(self.auth.check(self.auth.login("1234")))
        with self.assertRaisesRegex(AuthError, "wrong PIN"):
            self.auth.login("4321")

    def test_login_before_pin(self):
        with self.assertRaisesRegex(AuthError, "no PIN"):
            self.auth.login("1234")

    def test_changing_pin_needs_session_and_ends_others(self):
        first = self.auth.set_pin("1234")
        other = self.auth.login("1234")
        with self.assertRaisesRegex(AuthError, "log in"):
            self.auth.set_pin("5678")
        new = self.auth.set_pin("5678", first)
        self.assertTrue(self.auth.check(new))
        self.assertFalse(self.auth.check(other))
        self.auth.login("5678")

    def test_sessions_expire(self):
        token = self.auth.set_pin("1234")
        self.clock.advance(3599)
        self.assertTrue(self.auth.check(token))
        self.clock.advance(2)
        self.assertFalse(self.auth.check(token))

    def test_logout(self):
        token = self.auth.set_pin("1234")
        self.auth.logout(token)
        self.assertFalse(self.auth.check(token))
        self.assertFalse(self.auth.check(None))
        self.assertFalse(self.auth.check("made-up"))

    def test_lockout_after_repeated_failures(self):
        self.auth.set_pin("1234")
        for _ in range(auth.MAX_FAILURES):
            with self.assertRaises(AuthError):
                self.auth.login("0000")
        with self.assertRaisesRegex(AuthError, "too many"):
            self.auth.login("1234")  # even the right PIN, while locked
        self.clock.advance(auth.LOCKOUT_S)
        self.assertTrue(self.auth.check(self.auth.login("1234")))

    def test_pin_survives_restart(self):
        self.auth.set_pin("1234")
        again = AdminAuth(self.path, self.clock, session_s=3600)
        self.assertTrue(again.check(again.login("1234")))

    def test_damaged_pin_file_is_reported_not_bypassed(self):
        """An empty file (power cut on an older release) must not let anyone set a new PIN."""
        for content in ("", "{not json", '{"salt": "zz", "iterations": 1, "hash": "x"}', "{}"):
            with self.subTest(content=content):
                self.path.write_text(content)
                with self.assertRaisesRegex(DamagedPinFile, "delete"):
                    self.auth.login("1234")
                with self.assertRaises(AuthError):
                    self.auth.set_pin("9999")  # still counts as having a PIN
