"""Network modes against a scripted nmcli.

This checks the decisions (which profiles, which radio, when to fall back),
not NetworkManager itself; that is exercised on the Pi (design §3).
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from tower.config import NetworkSection
from tower.net import LOCAL_ONLY, SHARED, AP_CON, UPLINK_CON, NetworkManager, Watchdog, is_uplink_con

CHURCH = {"ssid": "Church", "psk": "secret99"}


class FakeNmcli:
    def __init__(self, devices=("wlan0",), in_range=("Church", "Tower", "Open"), join_ok=True, ap_ok=True,
                 refuse=()):
        self.devices = list(devices)
        self.in_range = set(in_range)  # SSIDs a scan finds
        self.refuse = set(refuse)  # SSIDs in range that reject the password
        self.connections: set[str] = set()
        self.active: dict[str, str] = {}  # profile -> device
        self.join_ok = join_ok
        self.ap_ok = ap_ok
        self.os_wifi: dict[str, str] = {}  # device -> SSID joined through a profile we don't own
        self.cable = False  # a network cable plugged in and connected
        self.calls: list[list[str]] = []
        self.props: dict[str, dict[str, str]] = {}

    def ssid_on(self, dev):
        for name, d in self.active.items():
            if d == dev and is_uplink_con(name):
                return self.props[name]["802-11-wireless.ssid"]
        return self.os_wifi.get(dev)

    def __call__(self, argv, timeout=60):
        self.calls.append(argv)
        args = argv[1:]
        if args[:1] == ["--wait"]:
            args = args[2:]
        out, code, err = "", 0, ""
        if args == ["-t", "-f", "DEVICE,TYPE", "device"]:
            out = "".join(f"{d}:wifi\n" for d in self.devices) + "eth0:ethernet\nlo:loopback\n"
        elif args == ["-t", "-f", "TYPE,STATE", "device"]:
            out = f"ethernet:{'connected' if self.cable else 'unavailable'}\nloopback:connected (externally)\n"
            out += "".join("wifi:connected\n" for _ in self.devices)
        elif args == ["-t", "-f", "NAME", "connection", "show"]:
            out = "".join(f"{c}\n" for c in sorted(self.connections))
        elif args[:5] == ["-t", "-f", "ACTIVE,SSID", "device", "wifi"]:
            joined = self.ssid_on(args[args.index("ifname") + 1])
            out = "no:Neighbours\n" + (f"yes:{joined}\n" if joined else "")
        elif args[:5] == ["-t", "-f", "SSID", "device", "wifi"]:
            out = "".join(f"{s}\n" for s in sorted(self.in_range | {"Neighbours"}))
        elif args == ["-t", "-f", "NAME,DEVICE", "connection", "show", "--active"]:
            out = "".join(f"{n}:{d}\n" for n, d in self.active.items())
        elif args[:2] == ["connection", "add"]:
            name = args[args.index("con-name") + 1]
            self.connections.add(name)
            self.props[name] = dict(zip(args[8::2], args[9::2]))
        elif args[:2] == ["connection", "modify"]:
            if args[3] != "remove":
                self.props.setdefault(args[2], {}).update(dict(zip(args[3::2], args[4::2])))
        elif args[:2] == ["connection", "delete"]:
            self.connections.discard(args[2])
            self.props.pop(args[2], None)
            self.active.pop(args[2], None)
        elif args[:2] == ["connection", "up"]:
            name = args[2]
            ssid = self.props.get(name, {}).get("802-11-wireless.ssid")
            if is_uplink_con(name) and (not self.join_ok or ssid in self.refuse or ssid not in self.in_range):
                code, err = 4, "Error: secrets were required"
            elif name == AP_CON and not self.ap_ok:
                code, err = 4, "Error: device wlan0 not available"
            else:
                dev = self.props[name]["connection.interface-name"]
                self.active = {n: d for n, d in self.active.items() if d != dev}  # one connection per radio
                self.active[name] = dev
        elif args[:2] == ["connection", "down"]:
            if self.active.pop(args[2], None) is None:
                code = 10
        return subprocess.CompletedProcess(argv, code, out, err)


def sharing_file():
    path = Path(tempfile.mkdtemp()) / "tower-ap.conf"
    path.write_text("")  # install.sh creates it
    return path


def manager(fake, sharing_conf=None, **cfg):
    return NetworkManager(NetworkSection(**cfg), runner=fake, sharing_conf=sharing_conf or sharing_file())


class ApModeTest(unittest.TestCase):
    def test_creates_shared_wpa_access_point(self):
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

    def test_switching_joined_to_ap_survives_reboot(self):
        """Known networks must stop autoconnecting, or the next boot rejoins one instead of the AP."""
        fake = FakeNmcli()
        manager(fake, mode="joined", uplinks=[CHURCH, {"ssid": "Tower", "psk": "towerpass"}]).apply()
        r = manager(fake, mode="ap", uplinks=[CHURCH]).apply()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})
        self.assertEqual(fake.props[UPLINK_CON]["connection.autoconnect"], "no")
        self.assertEqual(fake.props["tower-uplink-2"]["connection.autoconnect"], "no")
        self.assertEqual(fake.props[AP_CON]["connection.autoconnect"], "yes")

    def test_ap_failure_is_reported(self):
        for mode in ("ap", "dual"):
            with self.subTest(mode=mode):
                r = manager(FakeNmcli(ap_ok=False), mode=mode).apply()
                self.assertFalse(r.ok)
                self.assertEqual(r.effective, "none")
                self.assertIn("not available", r.detail)


class JoinedModeTest(unittest.TestCase):
    def test_joins_first_known_network_in_range(self):
        fake = FakeNmcli(in_range=("Tower",))
        nets = [CHURCH, {"ssid": "Tower", "psk": "towerpass"}]
        r = manager(fake, mode="joined", uplinks=nets).apply()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(r.detail, "joined Tower")
        self.assertEqual(fake.active, {"tower-uplink-2": "wlan0"})
        self.assertEqual(fake.props[AP_CON]["connection.autoconnect"], "no")

    def test_profile_per_network_in_preference_order(self):
        fake = FakeNmcli()
        nets = [CHURCH, {"ssid": "Tower", "psk": "towerpass"}, {"ssid": "Open"}]
        manager(fake, mode="joined", uplinks=nets).apply()
        prio = [int(fake.props[n]["connection.autoconnect-priority"])
                for n in (UPLINK_CON, "tower-uplink-2", "tower-uplink-3")]
        self.assertEqual(prio, sorted(prio, reverse=True))
        self.assertGreater(min(prio), int(fake.props[AP_CON]["connection.autoconnect-priority"]))
        self.assertNotIn("wifi-sec.psk", fake.props["tower-uplink-3"])  # open network
        self.assertEqual(fake.active, {UPLINK_CON: "wlan0"})

    def test_removed_networks_lose_their_profiles(self):
        fake = FakeNmcli()
        manager(fake, mode="joined", uplinks=[CHURCH, {"ssid": "Tower", "psk": "towerpass"}]).apply()
        manager(fake, mode="joined", uplinks=[CHURCH]).apply()
        self.assertNotIn("tower-uplink-2", fake.connections)

    def test_older_single_network_setting_still_works(self):
        fake = FakeNmcli()
        r = manager(fake, mode="joined", uplink_ssid="Church", uplink_psk="secret99").apply()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(fake.props[UPLINK_CON]["802-11-wireless.ssid"], "Church")

    def test_none_in_range_runs_ap_until_reboot(self):
        """Requirement: not found → AP until rebooted. Nothing persistent may change."""
        fake = FakeNmcli(in_range=("Elsewhere",))
        r = manager(fake, mode="joined", uplinks=[CHURCH]).apply()
        self.assertFalse(r.ok)
        self.assertEqual(r.effective, "ap")
        self.assertIn("in range", r.detail)
        self.assertIn("until the Pi restarts", r.detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})
        self.assertEqual(fake.props[AP_CON]["connection.autoconnect"], "no")  # gone after reboot
        self.assertEqual(fake.props[UPLINK_CON]["connection.autoconnect"], "yes")  # tried again after reboot

    def test_wrong_password_tries_next_then_falls_back(self):
        fake = FakeNmcli(refuse=("Church",), in_range=("Church",))
        r = manager(fake, mode="joined", uplinks=[CHURCH]).apply()
        self.assertEqual(r.effective, "ap")
        self.assertIn("Church: Error: secrets were required", r.detail)
        fake = FakeNmcli(refuse=("Church",))
        r = manager(fake, mode="joined", uplinks=[CHURCH, {"ssid": "Tower", "psk": "towerpass"}]).apply()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(r.detail, "joined Tower")

    def test_no_known_networks_runs_ap(self):
        fake = FakeNmcli()
        r = manager(fake, mode="joined").apply()
        self.assertFalse(r.ok)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})

    def test_on_known_network_through_os_profile_is_in_effect(self):
        """Imager's own WiFi profile already on a known network: don't reconnect (drops SSH)."""
        fake = FakeNmcli()
        fake.os_wifi["wlan0"] = "Tower"
        m = manager(fake, mode="joined", uplinks=[CHURCH, {"ssid": "Tower", "psk": "towerpass"}])
        self.assertTrue(m.in_effect())
        fake.os_wifi["wlan0"] = "Somewhere else"
        self.assertFalse(m.in_effect())
        self.assertFalse(manager(fake, mode="joined").in_effect())


class CableTest(unittest.TestCase):
    """Joined mode with a network cable: the cable is the internet, the radio runs the AP."""

    def test_cable_means_access_point(self):
        fake = FakeNmcli()
        fake.cable = True
        m = manager(fake, mode="joined", uplinks=[CHURCH])
        r = m.apply()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(r.effective, "ap+cable")
        self.assertEqual(fake.active, {AP_CON: "wlan0"})
        self.assertTrue(m.in_effect())
        # Not persistent: at boot the known networks still autoconnect; the app re-checks the cable.
        self.assertEqual(fake.props[AP_CON]["connection.autoconnect"], "no")

    def test_cable_in_effect_needs_the_ap(self):
        fake = FakeNmcli()
        m = manager(fake, mode="joined", uplinks=[CHURCH])
        m.apply()  # joined Church over WiFi
        fake.cable = True
        self.assertFalse(m.in_effect())  # cable now present, but the radio is still a client

    def test_watchdog_follows_cable_in_and_out(self):
        fake = FakeNmcli()
        m = manager(fake, mode="joined", uplinks=[CHURCH])
        m.apply()
        dog = Watchdog(m, now=0)
        self.assertIsNone(dog.check(10))  # first look: nothing changed
        fake.cable = True
        r = dog.check(20)
        self.assertEqual(r.effective, "ap+cable")
        self.assertEqual(fake.active, {AP_CON: "wlan0"})
        self.assertIsNone(dog.check(200))  # cable still in: stays on the AP, no fallback
        fake.cable = False
        r = dog.check(210)
        self.assertEqual((r.effective, r.detail), ("joined", "joined Church"))
        self.assertEqual(fake.active, {UPLINK_CON: "wlan0"})

    def test_unplugging_with_no_known_network_falls_back(self):
        fake = FakeNmcli(in_range=())
        fake.cable = True
        m = manager(fake, mode="joined", uplinks=[CHURCH])
        m.apply()
        dog = Watchdog(m, now=0)
        dog.check(10)
        fake.cable = False
        r = dog.check(20)
        self.assertEqual(r.effective, "ap")
        self.assertIn("until the Pi restarts", r.detail)
        self.assertIsNotNone(dog.fell_back)

    def test_plugging_in_after_fallback_reapplies(self):
        fake = FakeNmcli(in_range=())
        m = manager(fake, mode="joined", uplinks=[CHURCH])
        m.apply()  # fell back
        dog = Watchdog(m, now=0)
        dog.check(10)
        dog.check(200)
        fake.cable = True
        r = dog.check(210)
        self.assertEqual(r.effective, "ap+cable")
        self.assertIsNone(dog.fell_back)

    def test_cable_irrelevant_in_ap_mode(self):
        fake = FakeNmcli()
        fake.cable = True
        r = manager(fake, mode="ap").apply()
        self.assertEqual(r.effective, "ap")


class SharingTest(unittest.TestCase):
    def test_local_only_by_default(self):
        conf = sharing_file()
        manager(FakeNmcli(), sharing_conf=conf, mode="ap").apply()
        self.assertEqual(conf.read_text(), LOCAL_ONLY)
        self.assertIn("dhcp-option=option:router\n", LOCAL_ONLY)  # no default route offered

    def test_sharing_on(self):
        conf = sharing_file()
        manager(FakeNmcli(), sharing_conf=conf, mode="ap", ap_share_internet=True).apply()
        self.assertEqual(conf.read_text(), SHARED)
        self.assertNotIn("dhcp-option", SHARED)

    def test_written_before_the_access_point_starts(self):
        """dnsmasq reads it when the AP starts, so it must be in place first."""
        conf = sharing_file()
        fake = FakeNmcli()
        seen = []
        original = fake.__call__

        def spy(argv, timeout=60):
            if argv[-3:-1] == ["connection", "up"] and argv[-1] == AP_CON:
                seen.append(conf.read_text())
            return original(argv, timeout)

        manager(spy, sharing_conf=conf, mode="ap").apply()
        self.assertEqual(seen, [LOCAL_ONLY])

    def test_missing_file_reported_but_ap_still_starts(self):
        missing = Path(tempfile.mkdtemp()) / "nope" / "tower-ap.conf"
        fake = FakeNmcli()
        m = manager(fake, sharing_conf=missing, mode="ap")
        with self.assertLogs("tower.net", "ERROR"):
            r = m.apply()
        self.assertTrue(r.ok)
        self.assertIn("install.sh", m.status()["sharing_error"])


class DualModeTest(unittest.TestCase):
    def test_uplink_on_dongle(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        r = manager(fake, mode="dual", uplinks=[CHURCH]).apply()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0", UPLINK_CON: "wlan1"})

    def test_without_dongle_degrades_to_ap(self):
        fake = FakeNmcli(devices=("wlan0",))
        r = manager(fake, mode="dual", uplinks=[CHURCH]).apply()
        self.assertFalse(r.ok)
        self.assertEqual(r.effective, "ap")
        self.assertIn("dongle", r.detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})

    def test_failed_join_keeps_ap(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"), join_ok=False)
        r = manager(fake, mode="dual", uplinks=[CHURCH]).apply()
        self.assertEqual(r.effective, "ap")
        self.assertEqual(fake.active, {AP_CON: "wlan0"})

    def test_dongle_on_os_profile_is_in_effect(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        m = manager(fake, mode="dual", uplinks=[CHURCH])
        m._ensure_ap(autoconnect=True)
        m._up(AP_CON)
        self.assertFalse(m.in_effect())
        fake.os_wifi["wlan1"] = "Church"
        self.assertTrue(m.in_effect())


class WatchdogTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakeNmcli()
        self.net = manager(self.fake, mode="joined", uplinks=[CHURCH], fallback_after_s=90)
        self.net.apply()
        self.dog = Watchdog(self.net, now=0)

    def test_connection_lost_runs_ap_until_reboot(self):
        """Requirement: connection lost → AP until rebooted."""
        self.assertIsNone(self.dog.check(10))
        self.fake.active.clear()  # the network went away
        self.fake.in_range.clear()
        self.assertIsNone(self.dog.check(60))  # within the grace period: NM may reconnect
        r = self.dog.check(101)
        self.assertIsNotNone(r)
        self.assertIn("until the Pi restarts", r.detail)
        self.assertEqual(self.fake.active, {AP_CON: "wlan0"})
        self.assertEqual(self.fake.props[UPLINK_CON]["connection.autoconnect"], "yes")
        self.assertIsNone(self.dog.check(500))  # stays on the AP: no flapping

    def test_brief_drop_does_not_fall_back(self):
        self.fake.active.clear()
        self.assertIsNone(self.dog.check(50))
        self.net.apply()  # NM reconnected
        self.assertIsNone(self.dog.check(80))
        self.assertIsNone(self.dog.check(150))
        self.assertIsNone(self.dog.fell_back)

    def test_booting_out_of_range_falls_back(self):
        self.fake.active.clear()
        dog = Watchdog(self.net, now=1000)
        self.assertIsNone(dog.check(1050))
        self.assertIsNotNone(dog.check(1095))

    def test_only_in_joined_mode(self):
        self.net.cfg = NetworkSection(mode="ap")
        self.fake.active.clear()
        self.assertIsNone(self.dog.check(1000))

    def test_reset_after_deliberate_change(self):
        self.fake.active.clear()
        self.dog.check(100)
        self.assertIsNotNone(self.dog.fell_back)
        self.dog.reset(200)
        self.assertIsNone(self.dog.fell_back)


class OtherTest(unittest.TestCase):
    def test_wifi_power_saving_off(self):
        """Power saving makes the Pi miss the first request after a quiet spell."""
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        manager(fake, mode="dual", uplinks=[CHURCH]).apply()
        self.assertEqual(fake.props[AP_CON]["802-11-wireless.powersave"], "2")
        self.assertEqual(fake.props[UPLINK_CON]["802-11-wireless.powersave"], "2")

    def test_status(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        m = manager(fake, mode="dual", uplinks=[CHURCH])
        m.apply()
        s = m.status()
        self.assertTrue(s["ap_active"])
        self.assertTrue(s["uplink_active"])
        self.assertEqual(s["connected_ssid"], "Church")
        self.assertEqual(s["dongle"], "wlan1")
        self.assertEqual(s["uplinks"], ["Church"])
        self.assertNotIn("secret99", str(s))

    def test_connected_ssid_escapes(self):
        fake = FakeNmcli()
        fake.os_wifi["wlan0"] = "St Mary\\:guest"  # nmcli escapes ':' in terse output
        self.assertEqual(manager(fake).connected_ssid("wlan0"), "St Mary:guest")
        self.assertIsNone(manager(FakeNmcli()).connected_ssid("wlan0"))

    def test_uplink_profile_names(self):
        self.assertTrue(is_uplink_con("tower-uplink"))
        self.assertTrue(is_uplink_con("tower-uplink-3"))
        self.assertFalse(is_uplink_con("tower-uplinkx"))
        self.assertFalse(is_uplink_con("preconfigured"))

    def test_unavailable_off_the_pi(self):
        m = NetworkManager(NetworkSection(), sharing_conf=sharing_file())
        if m.available():
            self.skipTest("nmcli present on this host")
        self.assertFalse(m.status()["available"])

    def test_terse_escapes(self):
        fake = FakeNmcli()
        fake.active = {"Name\\:with colon": "wlan0"}
        self.assertEqual(manager(fake).active(), {"Name:with colon": "wlan0"})
