"""Network behaviour against a scripted nmcli.

This checks the decisions (which profiles, which radio, when to fall back),
not NetworkManager itself; that is exercised on the Pi (design §3).
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from tower.config import NetworkSection
from tower.net import AP_CON, LOCAL_ONLY, SHARED, UPLINK_CON, NetworkManager, Supervisor, is_uplink_con

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


TOWER = {"ssid": "Tower", "psk": "towerpass"}


class PlanTest(unittest.TestCase):
    """Behaviour follows the hardware (design C16)."""

    def test_plans(self):
        cases = [
            ({"cable": True, "devices": ("wlan0", "wlan1")}, [CHURCH], "cable"),  # cable beats the dongle
            ({"devices": ("wlan0", "wlan1")}, [CHURCH], "dongle"),
            ({"devices": ("wlan0",)}, [CHURCH], "single"),
            ({"devices": ("wlan0", "wlan1")}, [], "offline"),
            ({"cable": True}, [], "cable"),  # a cable needs no known networks
        ]
        for hw, nets, want in cases:
            with self.subTest(hw=hw, nets=nets):
                fake = FakeNmcli(devices=hw.get("devices", ("wlan0",)))
                fake.cable = hw.get("cable", False)
                self.assertEqual(manager(fake, uplinks=nets).plan(), want)


class ApplyTest(unittest.TestCase):
    def test_access_point_always_on(self):
        for devices, cable, nets in [(("wlan0",), False, []), (("wlan0",), False, [CHURCH]),
                                     (("wlan0",), True, [CHURCH]), (("wlan0", "wlan1"), False, [CHURCH])]:
            with self.subTest(devices=devices, cable=cable, nets=nets):
                fake = FakeNmcli(devices=devices)
                fake.cable = cable
                m = manager(fake, uplinks=nets)
                r = m.apply()
                self.assertTrue(r.ok, r.detail)
                self.assertEqual(fake.active.get(AP_CON), "wlan0")
                self.assertTrue(m.in_effect())

    def test_ap_settings(self):
        fake = FakeNmcli()
        manager(fake, ap_ssid="St Mary", ap_psk="ringing123").apply()
        p = fake.props[AP_CON]
        self.assertEqual((p["802-11-wireless.mode"], p["802-11-wireless.ssid"]), ("ap", "St Mary"))
        self.assertEqual((p["ipv4.method"], p["wifi-sec.psk"]), ("shared", "ringing123"))
        self.assertEqual(p["connection.autoconnect"], "yes")  # always boots onto the AP
        self.assertEqual(p["802-11-wireless.powersave"], "2")

    def test_single_radio_never_autojoins(self):
        """The AP must win at boot: known networks on the onboard radio never autoconnect."""
        fake = FakeNmcli()
        m = manager(fake, uplinks=[CHURCH, TOWER])
        r = m.apply()
        self.assertEqual(r.plan, "single")
        self.assertEqual(fake.active, {AP_CON: "wlan0"})
        for name in (UPLINK_CON, "tower-uplink-2"):
            self.assertEqual(fake.props[name]["connection.autoconnect"], "no")
            self.assertEqual(fake.props[name]["connection.interface-name"], "wlan0")
        self.assertGreater(int(fake.props[AP_CON]["connection.autoconnect-priority"]),
                           int(fake.props[UPLINK_CON]["connection.autoconnect-priority"]))

    def test_dongle_joins_first_known_network_in_range(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"), in_range=("Tower",))
        m = manager(fake, uplinks=[CHURCH, TOWER])
        r = m.apply()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0", "tower-uplink-2": "wlan1"})
        self.assertEqual(fake.props[UPLINK_CON]["connection.autoconnect"], "yes")
        self.assertTrue(m.online())

    def test_dongle_with_nothing_in_range_keeps_ap(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"), in_range=())
        m = manager(fake, uplinks=[CHURCH])
        r = m.apply()
        self.assertFalse(r.ok)
        self.assertIn("in range", r.detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})
        self.assertFalse(m.online())

    def test_cable_is_online_and_dongle_unused(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        fake.cable = True
        m = manager(fake, uplinks=[CHURCH])
        r = m.apply()
        self.assertEqual(r.plan, "cable")
        self.assertEqual(fake.active, {AP_CON: "wlan0"})
        self.assertTrue(m.online())

    def test_offline_and_single_are_not_online(self):
        self.assertFalse(manager(FakeNmcli()).online())
        self.assertFalse(manager(FakeNmcli(), uplinks=[CHURCH]).online())

    def test_apply_does_not_restart_a_running_ap(self):
        """Re-activating the AP would drop every phone on it."""
        fake = FakeNmcli()
        m = manager(fake)
        m.apply()
        m.apply()
        ups = [c for c in fake.calls if c[-3:-1] == ["connection", "up"] and c[-1] == AP_CON]
        self.assertEqual(len(ups), 1)

    def test_removed_networks_lose_their_profiles(self):
        fake = FakeNmcli()
        manager(fake, uplinks=[CHURCH, TOWER]).apply()
        manager(fake, uplinks=[CHURCH]).apply()
        self.assertNotIn("tower-uplink-2", fake.connections)

    def test_older_single_network_setting_still_works(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        r = manager(fake, uplink_ssid="Church", uplink_psk="secret99").apply()
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(fake.props[UPLINK_CON]["802-11-wireless.ssid"], "Church")

    def test_open_network(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        manager(fake, uplinks=[{"ssid": "Open"}]).apply()
        self.assertNotIn("wifi-sec.psk", fake.props[UPLINK_CON])

    def test_ap_failure_is_reported(self):
        r = manager(FakeNmcli(ap_ok=False)).apply()
        self.assertFalse(r.ok)
        self.assertIn("not available", r.detail)

    def test_imager_wifi_profile_is_replaced_by_the_ap(self):
        """A Pi imaged with home WiFi settings ends up on its AP: one way to connect everywhere."""
        fake = FakeNmcli()
        fake.os_wifi["wlan0"] = "Home"
        fake.active["preconfigured"] = "wlan0"
        manager(fake, uplinks=[CHURCH]).apply()
        self.assertEqual(fake.active, {AP_CON: "wlan0"})


class SingleRadioCheckTest(unittest.TestCase):
    """The update check: leave the AP, join a known network, come back."""

    def test_go_online_then_back(self):
        fake = FakeNmcli(in_range=("Tower",))
        m = manager(fake, uplinks=[CHURCH, TOWER])
        m.apply()
        ok, detail = m.go_online()
        self.assertEqual((ok, detail), (True, "joined Tower"))
        self.assertEqual(fake.active, {"tower-uplink-2": "wlan0"})
        self.assertFalse(m.in_effect())
        r = m.back_to_ap()
        self.assertTrue(r.ok)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})

    def test_nothing_in_range_returns_to_ap_at_once(self):
        fake = FakeNmcli(in_range=("Elsewhere",))
        m = manager(fake, uplinks=[CHURCH])
        m.apply()
        ok, detail = m.go_online()
        self.assertFalse(ok)
        self.assertIn("in range", detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})

    def test_wrong_password_tries_the_next(self):
        fake = FakeNmcli(refuse=("Church",))
        m = manager(fake, uplinks=[CHURCH, TOWER])
        m.apply()
        self.assertEqual(m.go_online(), (True, "joined Tower"))
        m.back_to_ap()
        fake = FakeNmcli(refuse=("Church",), in_range=("Church",))
        m = manager(fake, uplinks=[CHURCH])
        m.apply()
        ok, detail = m.go_online()
        self.assertFalse(ok)
        self.assertIn("Church: Error: secrets were required", detail)
        self.assertEqual(fake.active, {AP_CON: "wlan0"})

    def test_no_known_networks(self):
        fake = FakeNmcli()
        m = manager(fake)
        m.apply()
        self.assertEqual(m.go_online(), (False, "no known networks configured"))
        self.assertEqual(fake.active, {AP_CON: "wlan0"})


class SupervisorTest(unittest.TestCase):
    def test_follows_cable_and_dongle(self):
        fake = FakeNmcli()
        m = manager(fake, uplinks=[CHURCH])
        sup = Supervisor(m)
        self.assertEqual(sup.check().plan, "single")
        self.assertIsNone(sup.check())  # nothing changed
        fake.cable = True
        self.assertEqual(sup.check().plan, "cable")
        fake.cable = False
        fake.devices = ["wlan0", "wlan1"]
        r = sup.check()
        self.assertEqual(r.plan, "dongle")
        self.assertEqual(fake.active, {AP_CON: "wlan0", UPLINK_CON: "wlan1"})
        fake.devices = ["wlan0"]
        fake.active.pop(UPLINK_CON)
        self.assertEqual(sup.check().plan, "single")

    def test_restores_ap_that_went_down(self):
        fake = FakeNmcli()
        sup = Supervisor(manager(fake))
        sup.check()
        fake.active.clear()
        self.assertIsNotNone(sup.check())
        self.assertEqual(fake.active, {AP_CON: "wlan0"})

    def test_paused_during_update_check(self):
        fake = FakeNmcli()
        sup = Supervisor(manager(fake, uplinks=[CHURCH]))
        sup.check()
        sup.net.go_online()
        sup.paused = True
        self.assertIsNone(sup.check())  # must not snatch the radio back mid-check
        self.assertEqual(fake.active, {UPLINK_CON: "wlan0"})

    def test_known_network_change_reapplies(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        m = manager(fake, uplinks=[CHURCH])
        sup = Supervisor(m)
        sup.check()
        m.cfg = NetworkSection(uplinks=[TOWER])
        self.assertIsNotNone(sup.check())
        self.assertEqual(fake.props[UPLINK_CON]["802-11-wireless.ssid"], "Tower")


class SharingTest(unittest.TestCase):
    def test_local_only_by_default(self):
        conf = sharing_file()
        manager(FakeNmcli(), sharing_conf=conf).apply()
        self.assertEqual(conf.read_text(), LOCAL_ONLY)
        self.assertIn("dhcp-option=option:router\n", LOCAL_ONLY)  # no default route offered

    def test_sharing_on(self):
        conf = sharing_file()
        manager(FakeNmcli(), sharing_conf=conf, ap_share_internet=True).apply()
        self.assertEqual(conf.read_text(), SHARED)

    def test_written_before_the_access_point_starts(self):
        """dnsmasq reads it when the AP starts, so it must be in place first."""
        conf = sharing_file()
        fake = FakeNmcli()
        seen = []

        def spy(argv, timeout=60):
            if argv[-3:-1] == ["connection", "up"] and argv[-1] == AP_CON:
                seen.append(conf.read_text())
            return fake(argv, timeout)

        manager(spy, sharing_conf=conf).apply()
        self.assertEqual(seen, [LOCAL_ONLY])

    def test_missing_file_reported_but_ap_still_starts(self):
        missing = Path(tempfile.mkdtemp()) / "nope" / "tower-ap.conf"
        m = manager(FakeNmcli(), sharing_conf=missing)
        with self.assertLogs("tower.net", "ERROR"):
            r = m.apply()
        self.assertTrue(r.ok)
        self.assertIn("install.sh", m.status()["sharing_error"])


class OtherTest(unittest.TestCase):
    def test_status(self):
        fake = FakeNmcli(devices=("wlan0", "wlan1"))
        m = manager(fake, uplinks=[CHURCH])
        m.apply()
        s = m.status()
        self.assertEqual((s["plan"], s["online"], s["ap_active"]), ("dongle", True, True))
        self.assertEqual((s["dongle"], s["connected_ssid"]), ("wlan1", "Church"))
        self.assertNotIn("secret99", str(s))

    def test_connected_ssid_escapes(self):
        fake = FakeNmcli()
        fake.os_wifi["wlan0"] = "St Mary\\:guest"  # nmcli escapes ':' in terse output
        self.assertEqual(manager(fake).connected_ssid("wlan0"), "St Mary:guest")

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
