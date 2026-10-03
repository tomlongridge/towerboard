"""The web app and admin API over real HTTP, in-process."""

import http.client
import json
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from tests import helpers
from tests.test_net import FakeNmcli
from tower import config
from tower.clock import FakeClock
from tower.net import NetworkManager
from tower.web.api import COOKIE, TowerApp
from tower.web.server import make_server


class WebTestCase(unittest.TestCase):
    rt_expected = False

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(dir="/tmp"))  # short: Unix socket paths are limited
        self.overrides = self.tmp / "overrides.json"
        cfg = config.load(tower_path=self.tmp / "none.toml", overrides_path=self.overrides, cli={
            "paths": {"state_dir": str(self.tmp / "state"), "opt_dir": str(self.tmp / "opt")},
            "update": {"allowed_signers": str(helpers.allowed_signers())},
            "tower": {"name": "St Test"},
            "ipc": {"run_dir": str(self.tmp / "run")},
            "rt": {"expected": self.rt_expected},
        })
        self.handoffs = []
        self.fake_nm = FakeNmcli()
        self.app = TowerApp(cfg, FakeClock(), overrides_path=self.overrides,
                            net=NetworkManager(cfg.network, runner=self.fake_nm),
                            handoff=lambda action, v: self.handoffs.append((action, v)) or "handed (test)")
        self.server = make_server(self.app.routes(), "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.app.close)
        self.addCleanup(self.server.shutdown)
        self.cookie = None

    def request(self, method, path, body=None, raw=None, csrf=True, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = dict(headers or {})
        if csrf and method == "POST":
            h["X-Tower-Request"] = "1"
        if self.cookie:
            h["Cookie"] = f"{COOKIE}={self.cookie}"
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        if method == "POST" and data is None:
            data = b""
        conn.request(method, path, body=data, headers=h)
        resp = conn.getresponse()
        payload = resp.read()
        for k, v in resp.getheaders():
            if k.lower() == "set-cookie" and v.startswith(COOKIE + "="):
                self.cookie = v.split(";")[0].split("=", 1)[1] or None
        conn.close()
        ctype = resp.getheader("Content-Type", "")
        return resp.status, (json.loads(payload) if ctype.startswith("application/json") else payload)

    def login(self):
        status, _ = self.request("POST", "/api/admin/pin", {"pin": "246810"})
        self.assertEqual(status, 200)


class PublicTest(WebTestCase):
    def test_health(self):
        status, body = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["version"].endswith("+dev"))

    def test_static_shell(self):
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"<title>Towerboard</title>", body)
        status, _ = self.request("GET", "/app.js")
        self.assertEqual(status, 200)

    def test_static_traversal_blocked(self):
        for path in ("/../../tower/config.py", "/%2e%2e/%2e%2e/pyproject.toml", "/nope.html"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path)[0], 404)

    def test_info(self):
        _, body = self.request("GET", "/api/info", headers={"Host": "10.42.0.1"})
        self.assertEqual(body["tower"], "St Test")
        self.assertEqual(body["app_url"], "http://10.42.0.1/")

    def test_qr_codes(self):
        for path in ("/qr/wifi.svg", "/qr/app.svg"):
            status, body = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertTrue(body.startswith(b"<svg"))

    def test_diagnostics_public_and_secret_free(self):
        self.app.cfg = replace(self.app.cfg, network=replace(self.app.cfg.network, uplink_psk="topsecret1"))
        status, body = self.request("GET", "/api/diagnostics")
        self.assertEqual(status, 200)
        text = json.dumps(body)
        self.assertNotIn("topsecret1", text)
        self.assertNotIn(self.app.cfg.network.ap_psk, text)
        for key in ("version", "update", "network", "disk", "source", "audio", "sse", "wall_clock", "rt"):
            self.assertIn(key, body)
        self.assertEqual(body["audio"], "no report from the RT process")
        self.assertEqual(body["sse"]["clients"], 0)

    def test_unknown_route_and_method(self):
        self.assertEqual(self.request("POST", "/api/nope")[0], 404)
        self.assertEqual(self.request("POST", "/api/health")[0], 405)


def rt_status(audio="ok", source="open", detail=""):
    from tower import version

    return {"schema_version": 1, "type": "system", "seq": 1, "t": 0.0, "payload": {"rt": {
        "version": version.full_version(),
        "audio": {"status": audio, "detail": detail},
        "source": {"status": source, "detail": detail},
        "pack": {"id": "synthetic", "name": "Synthetic 16", "bells": 16, "error": ""},
        "clock_offset_ms": 0.0,
    }}}


class HealthWithRtTest(WebTestCase):
    """On the Pi (rt.expected), health reflects the RT process: the update pipeline relies on it."""

    rt_expected = True

    def health(self):
        return self.request("GET", "/api/health")[1]

    def test_degraded_without_rt(self):
        body = self.health()
        self.assertEqual(body["status"], "degraded")
        self.assertIn("no report", body["checks"]["rt"])

    def test_ok_with_rt_reporting(self):
        self.app.bus.on_rt(rt_status())
        body = self.health()
        self.assertEqual(body["status"], "ok", body)

    def test_absent_sensor_is_ok_unless_required(self):
        self.app.bus.on_rt(rt_status(source="absent", detail="no serial device"))
        self.assertEqual(self.health()["status"], "ok")
        self.app.cfg = replace(self.app.cfg, source=replace(self.app.cfg.source, required=True))
        self.assertEqual(self.health()["status"], "degraded")

    def test_audio_failure_is_degraded(self):
        self.app.bus.on_rt(rt_status(audio="unavailable", detail="cannot open ALSA device"))
        body = self.health()
        self.assertEqual(body["status"], "degraded")
        self.assertIn("ALSA", body["checks"]["audio"])

    def test_stale_report_is_degraded(self):
        self.app.bus.on_rt(rt_status())
        self.app.clock.advance(11)
        self.assertEqual(self.health()["status"], "degraded")


class AdminTest(WebTestCase):
    def test_admin_routes_need_session(self):
        for method, path in (("GET", "/api/admin/releases"), ("POST", "/api/admin/rollback"),
                             ("GET", "/api/admin/network"), ("POST", "/api/admin/update")):
            with self.subTest(path=path):
                self.assertEqual(self.request(method, path)[0], 401)

    def test_post_without_csrf_header_refused(self):
        status, body = self.request("POST", "/api/admin/pin", {"pin": "1234"}, csrf=False)
        self.assertEqual(status, 403)
        self.assertFalse(self.app.auth.has_pin())

    def test_first_pin_then_login_flow(self):
        _, s = self.request("GET", "/api/admin/session")
        self.assertEqual(s, {"has_pin": False, "logged_in": False})
        self.login()
        _, s = self.request("GET", "/api/admin/session")
        self.assertTrue(s["logged_in"])
        self.request("POST", "/api/admin/logout")
        self.assertIsNone(self.cookie)
        status, _ = self.request("POST", "/api/admin/login", {"pin": "000000"})
        self.assertEqual(status, 401)
        status, _ = self.request("POST", "/api/admin/login", {"pin": "246810"})
        self.assertEqual(status, 200)

    def test_cannot_take_over_existing_pin(self):
        self.login()
        self.cookie = None
        status, _ = self.request("POST", "/api/admin/pin", {"pin": "1111"})
        self.assertEqual(status, 400)

    def test_session_cookie_flags(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.request("POST", "/api/admin/pin", body=b'{"pin":"1234"}', headers={"X-Tower-Request": "1"})
        cookie = conn.getresponse().getheader("Set-Cookie")
        conn.close()
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)

    def test_upload_stages_and_hands_off(self):
        self.login()
        b = helpers.build_bundle(self.tmp, "3.0.0")
        status, body = self.request("POST", "/api/admin/update", raw=b.read_bytes())
        self.assertEqual(status, 202, body)
        self.assertEqual(body["staged"], "3.0.0")
        self.assertEqual(self.handoffs, [("activate", "3.0.0")])
        self.assertEqual(list((self.tmp / "state" / "incoming").iterdir()), [])
        _, rel = self.request("GET", "/api/admin/releases")
        self.assertIn("3.0.0", rel["available"])

    def test_upload_rejects_untrusted_bundle(self):
        self.login()
        b = helpers.build_bundle(self.tmp, "3.0.0", key=helpers.untrusted_key())
        status, body = self.request("POST", "/api/admin/update", raw=b.read_bytes())
        self.assertEqual(status, 422)
        self.assertIn("signature", body["error"])
        self.assertEqual(self.handoffs, [])
        self.assertEqual(list((self.tmp / "state" / "incoming").iterdir()), [])

    def test_empty_upload(self):
        self.login()
        self.assertEqual(self.request("POST", "/api/admin/update", raw=b"")[0], 400)

    def test_rollback_needs_previous(self):
        self.login()
        status, _ = self.request("POST", "/api/admin/rollback")
        self.assertEqual(status, 409)
        self.assertEqual(self.handoffs, [])

    def test_network_change_persists_and_applies(self):
        self.login()
        status, body = self.request("POST", "/api/admin/network",
                                    {"mode": "joined", "uplink_ssid": "Church", "uplink_psk": "secret99"})
        self.assertEqual(status, 202, body)
        saved = json.loads(self.overrides.read_text())
        self.assertEqual(saved["network"]["mode"], "joined")
        self.assertEqual(self.overrides.stat().st_mode & 0o777, 0o600)
        with self.app._net_lock:  # wait for the background apply
            pass
        for _ in range(100):
            if self.app._net_result:
                break
            threading.Event().wait(0.02)
        self.assertEqual(self.app._net_result["effective"], "joined")
        _, status_body = self.request("GET", "/api/admin/network")
        self.assertNotIn("secret99", json.dumps(status_body))
        self.assertTrue(status_body["uplink_psk_set"])

    def test_network_change_validated(self):
        self.login()
        for body in ({"mode": "bogus"}, {"ap_psk": "short"}, {"unknown": 1}):
            with self.subTest(body=body):
                self.assertEqual(self.request("POST", "/api/admin/network", body)[0], 400)
        self.assertFalse(self.overrides.exists())

    def test_bad_json(self):
        status, _ = self.request("POST", "/api/admin/login", raw=b"{nope")
        self.assertEqual(status, 400)


class ConcurrencyTest(WebTestCase):
    def test_held_connection_does_not_block_others(self):
        """ThreadingHTTPServer: a client stuck mid-request must not wedge the server."""
        import socket

        stuck = socket.create_connection(("127.0.0.1", self.port))
        stuck.sendall(b"GET /api/health HTTP/1.1\r\nHost: x\r\n")  # never finishes headers
        self.addCleanup(stuck.close)
        self.assertEqual(self.request("GET", "/api/health")[0], 200)
