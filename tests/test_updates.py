"""The update service end to end: fake WiFi hardware and GitHub, real signed bundles."""

import json
import tempfile
from pathlib import Path

from tests import helpers
from tests.test_github import API, FakeGitHub, release
from tests.test_web import WebTestCase
from tower.net import AP_CON, UPLINK_CON
from tower.release.github import GitHubReleases
from tower.updates import UpdateService

CHURCH = {"ssid": "Church", "psk": "secret99"}


class UpdateServiceTest(WebTestCase):
    @classmethod
    def setUpClass(cls):
        cls.dist = Path(tempfile.mkdtemp())
        cls.good = helpers.build_bundle(cls.dist, "9.0.0").read_bytes()
        cls.untrusted = helpers.build_bundle(Path(tempfile.mkdtemp()), "9.0.0",
                                             key=helpers.untrusted_key()).read_bytes()

    def setUp(self):
        super().setUp()
        self.ntp_synced = True
        self.github = FakeGitHub([release("v9.0.0", data=self.good)],
                                 {"https://github.test/dl/v9.0.0.tower": self.good})
        self.service = self.make_service()
        self.app.updates = self.service
        self.handoffs.clear()

    def make_service(self):
        return UpdateService(self.app, github=GitHubReleases("owner/repo", api=API, opener=self.github),
                             ntp=lambda: self.ntp_synced)

    def hardware(self, cable=False, dongle=False, in_range=("Church",), networks=(CHURCH,)):
        self.fake_nm.cable = cable
        self.fake_nm.devices = ["wlan0", "wlan1"] if dongle else ["wlan0"]
        self.fake_nm.in_range = set(in_range)
        self.app.net.cfg = self.app.cfg.network.__class__(uplinks=list(networks))
        self.app.cfg = self.app.cfg.__class__(**{**self.app.cfg.__dict__, "network": self.app.net.cfg})
        self.app.net.apply()

    def events(self):
        sub = self.app.bus.subscribe()
        self.addCleanup(self.app.bus.unsubscribe, sub)
        return sub

    # --- online (cable or dongle) ---------------------------------------------------------

    def test_cable_downloads_verifies_and_offers(self):
        self.hardware(cable=True)
        result = self.service.check()
        self.assertTrue(result["ok"], result)
        self.assertIn("9.0.0 downloaded and ready to apply", result["detail"])
        self.assertIn("9.0.0", self.app.releases.available())
        status = self.service.status()
        self.assertEqual(status["available"]["version"], "9.0.0")
        self.assertIn("cable", status["how"])
        self.assertEqual(list((self.tmp / "state" / "incoming").iterdir()), [])
        self.assertEqual(self.handoffs, [])  # never applied without an admin

    def test_published_bundle_named_by_full_version(self):
        """A real release: tag v9.1.0, bundle version 9.1.0+g1a2b3c4."""
        data = helpers.build_bundle(Path(tempfile.mkdtemp()), "9.1.0+g1a2b3c4").read_bytes()
        self.github.releases = [release("v9.1.0", data=data)]
        self.github.assets = {"https://github.test/dl/v9.1.0.tower": data}
        self.hardware(cable=True)
        self.assertIn("downloaded and ready", self.service.check()["detail"])
        downloads = len(self.github.requests)
        self.assertIn("downloaded and ready", self.service.check()["detail"])  # not fetched again
        self.assertEqual(len([r for r in self.github.requests[downloads:] if "/dl/" in r.full_url]), 0)
        self.service.apply()
        self.assertEqual(self.handoffs, [("activate", "9.1.0+g1a2b3c4")])
        # It fails its health check here: not offered again.
        self.app.releases._remember_failed("9.1.0+g1a2b3c4")
        self.assertIsNone(self.service.status()["available"])
        self.assertIn("up to date", self.service.check()["detail"])

    def test_apply_hands_off_the_staged_release(self):
        self.hardware(cable=True)
        self.service.check()
        self.assertEqual(self.service.apply(), "handed (test)")
        self.assertEqual(self.handoffs, [("activate", "9.0.0")])

    def test_dongle_is_online(self):
        self.hardware(dongle=True)
        self.assertTrue(self.service.check()["ok"])
        self.assertEqual(self.fake_nm.active, {AP_CON: "wlan0", UPLINK_CON: "wlan1"})  # AP untouched

    def test_dongle_not_joined(self):
        self.hardware(dongle=True, in_range=())
        result = self.service.check()
        self.assertFalse(result["ok"])
        self.assertIn("dongle is not connected", result["detail"])

    def test_up_to_date(self):
        self.github.releases = [release("v0.0.1")]
        self.hardware(cable=True)
        result = self.service.check()
        self.assertTrue(result["ok"])
        self.assertIn("up to date", result["detail"])
        self.assertIsNone(self.service.status()["available"])

    def test_untrusted_bundle_rejected(self):
        self.github.assets["https://github.test/dl/v9.0.0.tower"] = self.untrusted
        self.hardware(cable=True)
        result = self.service.check()
        self.assertFalse(result["ok"])
        self.assertIn("rejected", result["detail"])
        self.assertNotIn("9.0.0", self.app.releases.available())

    def test_failed_version_not_offered_again(self):
        self.app.releases._remember_failed("9.0.0")
        self.hardware(cable=True)
        self.assertIn("up to date", self.service.check()["detail"])

    def test_already_downloaded_not_fetched_twice(self):
        self.hardware(cable=True)
        self.service.check()
        downloads = len([r for r in self.github.requests if "/dl/" in r.full_url])
        self.service.check()
        self.assertEqual(len([r for r in self.github.requests if "/dl/" in r.full_url]), downloads)

    def test_waits_for_the_clock(self):
        self.ntp_synced = False
        self.hardware(cable=True)
        start = self.app.clock.now()
        self.assertTrue(self.service.check()["ok"])  # tries anyway after the wait
        self.assertGreaterEqual(self.app.clock.now() - start, self.app.cfg.update.ntp_wait_s)

    def test_github_unreachable(self):
        import urllib.error

        self.github.error = urllib.error.URLError(OSError("Network is unreachable"))
        self.hardware(cable=True)
        result = self.service.check()
        self.assertFalse(result["ok"])
        self.assertIn("cannot reach GitHub", result["detail"])

    def test_offline_explains_how_to_get_online(self):
        self.hardware(networks=())
        result = self.service.check()
        self.assertFalse(result["ok"])
        self.assertIn("plug in a network cable", result["detail"])

    def test_result_survives_restart(self):
        self.hardware(cable=True)
        self.service.check()
        again = self.make_service()
        self.assertEqual(again.status()["available"]["version"], "9.0.0")
        self.assertTrue(again.status()["last_result"]["ok"])
        self.assertTrue(again.status()["last_check_at"])

    # --- single radio ---------------------------------------------------------------------

    def test_single_radio_goes_online_briefly_and_returns(self):
        self.hardware()
        sub = self.events()
        result = self.service.check()
        self.assertTrue(result["ok"], result)
        self.assertIn("via Church", result["detail"])
        self.assertEqual(self.fake_nm.active, {AP_CON: "wlan0"})  # back on the AP
        self.assertFalse(self.app.supervisor.paused)
        modes = [json.loads(line)["payload"].get("update_mode") for line in sub.get(0)]
        modes = [m for m in modes if m is not None]
        self.assertTrue(modes[0]["active"])  # the wall was told
        self.assertIn("switch the Pi off and on", modes[0]["if_stuck"])
        self.assertIn("WiFi is off", modes[0]["message"])
        self.assertFalse(modes[-1]["active"])

    def test_single_radio_waits_for_quiet(self):
        self.hardware()
        self.app.bus.last_strike_at = self.app.clock.now()  # the bells just rang
        start = self.app.clock.now()
        self.service.check()
        self.assertGreaterEqual(self.app.clock.now() - start, self.app.cfg.update.quiet_s)

    def test_single_radio_nothing_in_range(self):
        self.hardware(in_range=())
        result = self.service.check()
        self.assertFalse(result["ok"])
        self.assertIn("in range", result["detail"])
        self.assertEqual(self.fake_nm.active, {AP_CON: "wlan0"})

    def test_single_radio_time_limit(self):
        self.hardware()
        self.app.cfg = self.app.cfg.__class__(**{**self.app.cfg.__dict__, "update": self.app.cfg.update.__class__(
            **{**self.app.cfg.update.__dict__, "check_window_s": 0.0})})
        result = self.service.check()
        self.assertFalse(result["ok"])
        self.assertIn("ran out of time", result["detail"])
        self.assertEqual(self.fake_nm.active, {AP_CON: "wlan0"})

    def test_single_radio_returns_to_ap_even_if_the_check_crashes(self):
        self.hardware()
        self.github.error = RuntimeError("boom")
        result = self.service.check()
        self.assertFalse(result["ok"])
        self.assertEqual(self.fake_nm.active, {AP_CON: "wlan0"})
        self.assertFalse(self.app.supervisor.paused)

    # --- admin API ---------------------------------------------------------------------------

    def test_routes_need_admin(self):
        for method, path in (("GET", "/api/admin/updates"), ("POST", "/api/admin/updates/check"),
                             ("POST", "/api/admin/updates/apply")):
            with self.subTest(path=path):
                self.assertEqual(self.request(method, path)[0], 401)

    def test_apply_with_nothing_downloaded(self):
        self.login()
        status, body = self.request("POST", "/api/admin/updates/apply")
        self.assertEqual(status, 409)
        self.assertIn("no downloaded update", body["error"])

    def test_check_and_apply_over_http(self):
        self.login()
        self.hardware(cable=True)
        status, body = self.request("POST", "/api/admin/updates/check")
        self.assertEqual((status, body["detail"]), (202, "check started"))
        self.service.check()  # what the background thread does when woken
        _, body = self.request("GET", "/api/admin/updates")
        self.assertEqual(body["available"]["version"], "9.0.0")
        status, body = self.request("POST", "/api/admin/updates/apply")
        self.assertEqual(status, 202)
        self.assertEqual(self.handoffs, [("activate", "9.0.0")])

    def test_diagnostics_show_updates(self):
        _, body = self.request("GET", "/api/diagnostics")
        self.assertIn("updates", body)
        self.assertEqual(body["updates"]["repo"], self.app.cfg.update.github_repo)
