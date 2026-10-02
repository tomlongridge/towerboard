"""Network modes against a scripted nmcli.

This checks the decisions (which profiles, which radio, when to fall back),
not NetworkManager itself; that is exercised on the Pi (design §3).
"""

import subprocess
import unittest

from tower.config import NetworkSection
from tower.net import AP_CON, UPLINK_CON, NetworkManager


class FakeNmcli:
    def __init__(self, devices=("wlan0",), connections=(), join_ok=True, ap_ok=True):
        self.devices = list(devices)
        self.connections = set(connections)
        self.active: dict[str, str] = {}
        self.join_ok = join_ok
        self.ap_ok = ap_ok
        self.calls: list[list[str]] = []
        self.props: dict[str, dict[str, str]] = {}

    def __call__(self, argv, timeout=60):
        self.calls.append(argv)
        args = argv[1:]
        if args[:1] == ["--wait"]:
            args = args[2:]
        out, code, err = "", 0, ""
        if args == ["-t", "-f", "DEVICE,TYPE", "device"]:
            out = "".join(f"{d}:wifi\n" for d in self.devices) + "eth0:ethernet\nlo:loopback\n"
        elif args == ["-t", "-f", "NAME", "connection", "show"]:
            out = "".join(f"{c}\n" for c in sorted(self.connections))
        elif args == ["-t", "-f", "NAME,DEVICE", "connection", "show", "--active"]:
            out = "".join(f"{n}:{d}\n" for n, d in self.active.items())
        elif args[:2] == ["connection", "add"]:
            name = args[args.index("con-name") + 1]
            self.connections.add(name)
            self.props[name] = dict(zip(args[8::2], args[9::2]))
        elif args[:2] == ["connection", "modify"]:
            if args[3] != "remove":
                self.props.setdefault(args[2], {}).update(dict(zip(args[3::2], args[4::2])))
        elif args[:2] == ["connection", "up"]:
            name = args[2]
            if name == UPLINK_CON and not self.join_ok:
                code, err = 4, "Error: secrets were required"
            elif name == AP_CON and not self.ap_ok:
                code, err = 4, "Error: device wlan0 not available"
            else:
                self.active[name] = self.props[name]["connection.interface-name"]
        elif args[:2] == ["connection", "down"]:
            if self.active.pop(args[2], None) is None:
                code = 10
        return subprocess.CompletedProcess(argv, code, out, err)


def manager(fake, **cfg):
    return NetworkManager(NetworkSection(**cfg), runner=fake)


class NetworkManagerTest(unittest.TestCase):
    def test_ap_mode_creates_shared_wpa_access_point(self):
        fake = FakeNmcli()
        r = manager(fake, mode="ap", ap_ssid="St Mary", ap_psk="ringing123").apply()
        self.assertTrue(r.ok)
        self.assertEqual(r.effective, "ap")
        p = fake.props[AP_CON]
        self.assertEqual(p["802-11-wireless.mode"], "ap")
        self.assertEqual(p["802-11-wireless.ssid"], "St Mary")
        self.assertEqual(p["ipv4.method"], "shared")
        self.assertEqual(p["wifi-sec.psk"], "ringing123")
        self.assertEqual(p["connection.autoconnect"], "yes")
        self.assertEqual(fake.active, {AP_CON: "wlan0"})

    def test_apply_is_idempotent_modify_not_recreate(self):
        fake = FakeNmcli()
        m = manager(fake, mode="ap")
        m.apply()
        m.apply()
        adds = [c for c in fake.calls if c[1:3] == ["connection", "add"]]
        self.assertEqual(len(adds), 1)

    def test_joined_uses_onboard_radio_and_disables_ap_autoconnect(self):
        fake = FakeNmcli()
        r = manager(fake, mode="joined", uplink_ssid="Church", uplink_psk="secret99").apply()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(fake.active, {UPLINK_CON: "wlan0"})
        self.assertEqual(fake.props[AP_CON]["connection.autoconnect"], "no")

    def test_failed_join_falls_back_to_ap(self):
        fake = FakeNmcli(join_ok=False)
        r = manager(fake, mode="joined", uplink_ssid="Church", uplink_psk="wrong-pass").apply()
        self.assertFalse(r.ok)
        self.assertEqual(r.effective, "ap")
        self.assertIn("fell back", r.detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})
        self.assertEqual(fake.props[AP_CON]["connection.autoconnect"], "yes")
        self.assertEqual(fake.props[UPLINK_CON]["connection.autoconnect"], "no")

    def test_joined_without_ssid_stays_ap(self):
        fake = FakeNmcli()
        r = manager(fake, mode="joined").apply()
        self.assertFalse(r.ok)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})

    def test_dual_puts_uplink_on_dongle(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        r = manager(fake, mode="dual", uplink_ssid="Church", uplink_psk="secret99").apply()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0", UPLINK_CON: "wlan1"})

    def test_dual_without_dongle_degrades_to_ap(self):
        fake = FakeNmcli(devices=("wlan0",))
        r = manager(fake, mode="dual", uplink_ssid="Church").apply()
        self.assertFalse(r.ok)
        self.assertEqual(r.effective, "ap")
        self.assertIn("dongle", r.detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})

    def test_dual_failed_join_keeps_ap(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"), join_ok=False)
        r = manager(fake, mode="dual", uplink_ssid="Church", uplink_psk="x" * 8).apply()
        self.assertEqual(r.effective, "ap")
        self.assertIn(AP_CON, fake.active)

    def test_ap_failure_is_reported(self):
        for mode in ("ap", "dual"):
            with self.subTest(mode=mode):
                r = manager(FakeNmcli(ap_ok=False), mode=mode).apply()
                self.assertFalse(r.ok)
                self.assertEqual(r.effective, "none")
                self.assertIn("not available", r.detail)

    def test_open_uplink_network(self):
        fake = FakeNmcli()
        manager(fake, mode="joined", uplink_ssid="Open").apply()
        self.assertNotIn("wifi-sec.psk", fake.props[UPLINK_CON])

    def test_in_effect(self):
        fake = FakeNmcli(devices=("wlan0",))
        m = manager(fake, mode="ap")
        self.assertFalse(m.in_effect())
        m.apply()
        self.assertTrue(m.in_effect())
        m.cfg = NetworkSection(mode="dual")
        self.assertTrue(m.in_effect())  # no dongle: AP alone is the best dual can do

    def test_status(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        m = manager(fake, mode="ap")
        m.apply()
        s = m.status()
        self.assertTrue(s["ap_active"])
        self.assertEqual(s["dongle"], "wlan1")
        self.assertEqual(s["wifi_devices"], ["wlan0", "wlan1"])

    def test_unavailable_off_the_pi(self):
        m = NetworkManager(NetworkSection())
        if m.available():
            self.skipTest("nmcli present on this host")
        self.assertFalse(m.status()["available"])

    def test_terse_escapes(self):
        fake = FakeNmcli()
        fake.active = {"Name\\:with colon": "wlan0"}
        self.assertEqual(manager(fake).active(), {"Name:with colon": "wlan0"})
