"""Ringing routes over HTTP; control messages checked on a real socket where the RT would listen."""

import http.client
import json
import threading

from tests.test_soundpack import MANIFEST, make_zip
from tests.test_web import WebTestCase
from tower import ipc


class RingingApiTest(WebTestCase):
    def setUp(self):
        super().setUp()
        self.rt_control = ipc.Receiver(self.tmp / "run" / ipc.CONTROL)
        self.addCleanup(self.rt_control.close)

    def controls(self):
        out = []
        while (m := self.rt_control.recv(timeout=0.05)) is not None:
            out.append(m)
        return out

    def test_admin_routes_need_session(self):
        for path in ("/api/admin/audio", "/api/admin/calibration", "/api/admin/volume", "/api/admin/time"):
            method = "GET" if path.endswith("audio") else "POST"
            with self.subTest(path=path):
                self.assertEqual(self.request(method, path, {})[0], 401)

    def test_reset_strokes_is_public(self):
        status, body = self.request("POST", "/api/strokes/reset")
        self.assertEqual((status, body["sent"]), (200, True))
        self.assertEqual(self.controls(), [{"cmd": "reset_strokes"}])

    def test_calibration_persists_and_tells_rt(self):
        self.login()
        self.request("POST", "/api/admin/calibration", {"bell": 2, "stroke": "back", "steps": 3})
        status, body = self.request("POST", "/api/admin/calibration", {"bell": 2, "stroke": "back", "steps": -1})
        self.assertEqual((status, body["ms"], body["applied"]), (200, 10.0, True))
        saved = json.loads((self.tmp / "state" / "calibration.json").read_text())
        self.assertEqual(saved["offsets_ms"]["2"]["back"], 10.0)
        self.assertEqual(self.controls(), [{"cmd": "reload_calibration"}] * 2)
        _, audio = self.request("GET", "/api/admin/audio")
        self.assertEqual(audio["calibration_ms"]["2"]["back"], 10.0)

    def test_calibration_validation(self):
        self.login()
        for body in ({"bell": 0, "stroke": "hand", "steps": 1}, {"bell": 1, "stroke": "x", "steps": 1},
                     {"bell": 1, "stroke": "hand"}):
            with self.subTest(body=body):
                self.assertEqual(self.request("POST", "/api/admin/calibration", body)[0], 400)

    def test_calibration_saved_even_when_rt_is_down(self):
        self.login()
        self.rt_control.close()
        _, body = self.request("POST", "/api/admin/calibration", {"bell": 1, "stroke": "hand", "ms": 120})
        self.assertFalse(body["applied"])
        self.assertTrue((self.tmp / "state" / "calibration.json").is_file())

    def test_test_strike(self):
        self.login()
        self.request("POST", "/api/admin/test-strike", {"bell": 4})
        self.assertEqual(self.controls(), [{"cmd": "test_strike", "bell": 4, "stroke": "hand"}])
        self.assertEqual(self.request("POST", "/api/admin/test-strike", {"bell": 40})[0], 400)

    def test_volume_persists(self):
        self.login()
        status, _ = self.request("POST", "/api/admin/volume", {"db": -12})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(self.overrides.read_text())["audio"]["volume_db"], -12.0)
        self.assertEqual(self.controls(), [{"cmd": "volume", "db": -12.0}])
        self.assertEqual(self.request("POST", "/api/admin/volume", {"db": 50})[0], 400)

    def test_pack_upload_select(self):
        self.login()
        z = make_zip(self.tmp / "p.zip")
        status, body = self.request("POST", "/api/admin/soundpack", raw=z.read_bytes())
        self.assertEqual(status, 201, body)
        self.assertEqual(body["installed"]["id"], "test-ring")
        status, _ = self.request("POST", "/api/admin/soundpack/select", {"id": "test-ring"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(self.overrides.read_text())["audio"]["pack"], "test-ring")
        self.assertEqual(self.controls(), [{"cmd": "pack", "id": "test-ring"}])
        self.assertEqual(self.request("POST", "/api/admin/soundpack/select", {"id": "nope"})[0], 400)
        self.assertEqual(list((self.tmp / "state" / "incoming").iterdir()), [])

    def test_bad_pack_rejected(self):
        self.login()
        z = make_zip(self.tmp / "p.zip", manifest=MANIFEST.replace("schema_version = 1", "schema_version = 9"))
        status, body = self.request("POST", "/api/admin/soundpack", raw=z.read_bytes())
        self.assertEqual(status, 422)
        self.assertIn("schema_version", body["error"])

    def test_time_from_browser(self):
        self.login()
        import time

        status, body = self.request("POST", "/api/admin/time", {"epoch_ms": time.time() * 1000 + 7200_000})
        self.assertEqual(status, 200)
        if body["used"]:  # not on an NTP-synchronised host
            self.assertEqual(body["source"], "browser")
            self.assertAlmostEqual(body["browser_offset_s"], 7200, delta=5)

    def test_sse_stream(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/api/events")
        resp = conn.getresponse()
        self.assertEqual(resp.getheader("Content-Type"), "text/event-stream")
        self.assertEqual(resp.readline(), b"retry: 2000\n")
        first = json.loads(resp.readline().decode()[6:])
        self.assertEqual(first["type"], "state")
        resp.readline()
        self.app.bus.on_rt({"schema_version": 1, "type": "strike", "seq": 5, "t": 1.0,
                            "payload": {"bell": 3, "stroke": "hand", "source": "live"}})
        line = resp.readline()
        while line.startswith(b":"):  # skip keepalives
            resp.readline()
            line = resp.readline()
        self.assertEqual(json.loads(line.decode()[6:])["payload"]["bell"], 3)
        self.assertEqual(self.app.bus.stats()["clients"], 1)
        conn.close()

    def test_sse_does_not_block_other_requests(self):
        conns = []
        for _ in range(5):
            c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            c.request("GET", "/api/events")
            c.getresponse()
            conns.append(c)
        self.assertEqual(self.request("GET", "/api/health")[0], 200)
        for c in conns:
            c.close()
        threading.Event().wait(0.1)
