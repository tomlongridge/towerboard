"""Health check and updater handoff. systemctl is scripted; the HTTP side is a real server."""

import json
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tower.clock import FakeClock
from tower.release import host


def systemctl(active=True, start_ok=True):
    calls = []

    def run(argv, timeout=60):
        calls.append(argv)
        if argv[1] == "is-active":
            return subprocess.CompletedProcess(argv, 0 if active else 3,
                                               "active\n" if active else "failed\n", "")
        ok = start_ok
        return subprocess.CompletedProcess(argv, 0 if ok else 1, "", "" if ok else "Access denied")

    run.calls = calls
    return run


class HealthServer:
    def __init__(self, body):
        self.body = body
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                data = json.dumps(outer.body).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02},
                         daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class HealthCheckTest(unittest.TestCase):
    def check(self, body, active=True, timeout=5):
        srv = HealthServer(body)
        self.addCleanup(srv.close)
        clock = FakeClock()
        ok, detail = host.health_check(srv.port, ["tower.service"], timeout, clock,
                                       systemctl(active))("1.1.0")
        return ok, detail, clock

    def test_healthy(self):
        ok, detail, _ = self.check({"status": "ok", "version": "1.1.0"})
        self.assertTrue(ok, detail)

    def test_wrong_version_is_unhealthy(self):
        """The old release still answering means the swap did not take."""
        ok, detail, clock = self.check({"status": "ok", "version": "1.0.0"})
        self.assertFalse(ok)
        self.assertIn("expected '1.1.0'", detail)
        self.assertGreaterEqual(clock.now(), 5)  # waited out the grace period

    def test_unit_not_active(self):
        ok, detail, _ = self.check({"status": "ok", "version": "1.1.0"}, active=False)
        self.assertFalse(ok)
        self.assertIn("not active", detail)

    def test_no_http(self):
        ok, detail = host.health_check(1, ["tower.service"], 2, FakeClock(), systemctl())("1.1.0")
        self.assertFalse(ok)
        self.assertIn("HTTP", detail)

    def test_bad_status(self):
        ok, detail, _ = self.check({"status": "degraded", "version": "1.1.0", "checks": {"audio": "x"}})
        self.assertFalse(ok)
        self.assertIn("degraded", detail)


class HandoffTest(unittest.TestCase):
    def test_request_round_trip(self):
        state = Path(tempfile.mkdtemp())
        host.write_request(state, "activate", "1.2.3")
        self.assertEqual(host.take_request(state), {"action": "activate", "version": "1.2.3"})
        self.assertIsNone(host.take_request(state))  # consumed exactly once

    def test_start_updater(self):
        run = systemctl()
        host.start_updater(run)
        self.assertEqual(run.calls, [["systemctl", "start", "--no-block", "tower-update.service"]])

    def test_start_updater_failure(self):
        with self.assertRaisesRegex(RuntimeError, "Access denied"):
            host.start_updater(systemctl(start_ok=False))

    def test_restart_units(self):
        run = systemctl()
        host.restart_units(["tower.service"], run)()
        self.assertEqual(run.calls, [["systemctl", "restart", "tower.service"]])
