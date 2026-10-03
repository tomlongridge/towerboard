"""Network manager (design C16): ``ap`` | ``joined`` | ``dual`` via NetworkManager.

* ``ap`` — onboard radio runs the ringers' access point. Default; needs no dongle.
* ``joined`` — onboard radio joins one of a list of known networks instead.
  If a network cable is connected, the cable is the internet connection and
  the radio runs the AP; unplugging it goes back to joining a known network.
* ``dual`` — onboard radio stays the AP; a USB dongle joins a known network.

The dongle is optional in every mode: without it, ``dual`` degrades to ``ap``.

With a single radio (``joined``), the Pi must never become unreachable: if
none of the known networks is in range when it starts, or the connection is
lost and does not come back, it runs the access point **until the next
reboot** (requirements: "Internet access"). The fallback changes nothing that
persists, so after a reboot it tries the known networks again.

The app owns these NetworkManager profiles and modifies them in place, so
settings survive reboot through NM's own autoconnect: ``tower-ap``, and one
per known network: ``tower-uplink``, ``tower-uplink-2``, … NM picks whichever
known network is in range. Nothing hand-rolls hostapd or dnsmasq; the AP uses
``ipv4.method shared`` (NM's built-in DHCP, gateway 10.42.0.1).

Whether phones on the AP get the Pi's internet connection is
``network.ap_share_internet``. NM's shared mode always offers it; local only
works by telling the AP's DHCP server (NM's dnsmasq, which reads
``dnsmasq-shared.d``) to offer no default route, so phones keep using their
mobile data for the internet. That stops phones being offered the internet;
it is not a firewall.

All behaviour goes through ``nmcli`` via an injected runner. Off the Pi
there is no ``nmcli``, and ``available()`` says so rather than pretending.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tower.config import NetworkSection

log = logging.getLogger(__name__)

AP_CON = "tower-ap"
UPLINK_CON = "tower-uplink"  # the first known network; others are tower-uplink-2, -3, …
AP_ADDRESS = "10.42.0.1"  # NetworkManager's default for ipv4.method shared
# The Pi's WiFi dozes when idle by default, so the first request after a quiet
# spell fails ("No route to host") until it wakes. 2 = disable power saving.
POWERSAVE_OFF = "2"
# Read by the dnsmasq NetworkManager starts for the AP. Created by install.sh,
# owned by the tower user so the app can rewrite it (the directory is root's).
SHARING_CONF = Path("/etc/NetworkManager/dnsmasq-shared.d/tower-ap.conf")
LOCAL_ONLY = ("# Managed by Towerboard (network.ap_share_internet = false): the access point is\n"
              "# local only. Phones are offered no default route, so they keep their mobile data.\n"
              "dhcp-option=option:router\n")
SHARED = "# Managed by Towerboard (network.ap_share_internet = true): phones may use the Pi's internet.\n"

Runner = Callable[..., subprocess.CompletedProcess]


def _run(argv: list[str], timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


def uplink_con(index: int) -> str:
    return UPLINK_CON if index == 0 else f"{UPLINK_CON}-{index + 1}"


def is_uplink_con(name: str) -> bool:
    return name == UPLINK_CON or (name.startswith(UPLINK_CON + "-") and name[len(UPLINK_CON) + 1:].isdigit())


@dataclass
class ApplyResult:
    requested: str
    effective: str  # what the radios are actually doing now
    ok: bool
    detail: str

    def as_dict(self) -> dict:
        return {"requested": self.requested, "effective": self.effective,
                "ok": self.ok, "detail": self.detail}


class NetworkManager:
    def __init__(self, cfg: NetworkSection, runner: Runner | None = None,
                 sharing_conf: Path = SHARING_CONF) -> None:
        self.cfg = cfg
        self.runner = runner or _run
        self._available = runner is not None or shutil.which("nmcli") is not None
        self.sharing_conf = sharing_conf
        self.sharing_error: str | None = None

    def available(self) -> bool:
        return self._available

    @property
    def networks(self) -> list[tuple[str, str]]:
        return self.cfg.uplink_networks()

    # --- inspection ------------------------------------------------------

    def wifi_devices(self) -> list[str]:
        out = self._nmcli("-t", "-f", "DEVICE,TYPE", "device").stdout
        rows = (_split_terse(line) for line in out.splitlines() if line)
        return [dev for dev, kind in rows if kind == "wifi"]

    def dongle(self) -> str | None:
        """First WiFi device that is not the onboard AP radio."""
        return next((d for d in self.wifi_devices() if d != self.cfg.ap_interface), None)

    def cable_connected(self) -> bool:
        """Whether a wired connection is up (a cable plugged in and an address obtained)."""
        out = self._nmcli("-t", "-f", "TYPE,STATE", "device").stdout
        return any(_split_terse(line) == ("ethernet", "connected") for line in out.splitlines())

    def active(self) -> dict[str, str]:
        out = self._nmcli("-t", "-f", "NAME,DEVICE", "connection", "show", "--active").stdout
        return dict(_split_terse(line) for line in out.splitlines() if line)

    def status(self) -> dict:
        if not self.available():
            return {"available": False, "detail": "nmcli not found (not running on the Pi)",
                    "mode": self.cfg.mode}
        try:
            active = self.active()
            uplink_dev = self.cfg.ap_interface if self.cfg.mode == "joined" else self.dongle()
            return {
                "available": True,
                "mode": self.cfg.mode,
                "ap_active": AP_CON in active,
                "uplink_active": any(is_uplink_con(n) for n in active),
                "cable_connected": self.cable_connected(),
                "ap_share_internet": self.cfg.ap_share_internet,
                "sharing_error": self.sharing_error,
                "connected_ssid": self.connected_ssid(uplink_dev) if uplink_dev else None,
                "wifi_devices": self.wifi_devices(),
                "dongle": self.dongle(),
                "ap_ssid": self.cfg.ap_ssid,
                "uplinks": [ssid for ssid, _ in self.networks],
            }
        except (OSError, subprocess.SubprocessError, RuntimeError) as e:
            return {"available": True, "mode": self.cfg.mode, "error": str(e)}

    def in_effect(self) -> bool:
        """Whether the configured mode is already what the radios are doing.

        Being on a known network counts whichever profile got there: a Pi
        imaged with WiFi settings joins through the OS's own profile, and
        switching it to ``tower-uplink`` would drop the connection (and any SSH
        session over it) for nothing.
        """
        active = self.active()
        uplink_up = any(is_uplink_con(n) for n in active)
        if self.cfg.mode == "ap":
            return AP_CON in active and not uplink_up
        if self.cfg.mode == "joined":
            if self.cable_connected():
                return AP_CON in active and not uplink_up
            return uplink_up or self._on_known_network(self.cfg.ap_interface)
        if AP_CON not in active:
            return False
        dongle = self.dongle()
        return dongle is None or uplink_up or self._on_known_network(dongle)

    def connected_ssid(self, device: str) -> str | None:
        """The network ``device`` is connected to, from NetworkManager's last scan (no rescan)."""
        r = self.runner(["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi", "list",
                         "ifname", device, "--rescan", "no"], timeout=30)
        if r.returncode != 0:
            return None
        for line in r.stdout.splitlines():
            flag, ssid = _split_terse(line)
            if flag == "yes":
                return ssid
        return None

    def visible_ssids(self, device: str) -> set[str]:
        r = self.runner(["nmcli", "-t", "-f", "SSID", "device", "wifi", "list",
                         "ifname", device, "--rescan", "yes"], timeout=60)
        if r.returncode != 0:
            return set()
        return {_unescape(line) for line in r.stdout.splitlines() if line}

    def _on_known_network(self, device: str) -> bool:
        ssids = {ssid for ssid, _ in self.networks}
        return bool(ssids) and self.connected_ssid(device) in ssids

    # --- applying modes ----------------------------------------------------

    def apply(self) -> ApplyResult:
        mode = self.cfg.mode
        if mode == "ap":
            return self._apply_ap()
        if mode == "joined":
            return self._apply_joined()
        return self._apply_dual()

    def fall_back_to_ap(self, reason: str) -> ApplyResult:
        """Single radio, no known network: run the AP until reboot.

        Nothing persistent changes: the AP does not autoconnect and the known
        networks still do, so the next boot tries them again.
        """
        log.warning("%s; running the access point until reboot", reason)
        self._ensure_ap(autoconnect=False)
        for name in self.active():
            if is_uplink_con(name):
                self._down(name)
        up = self._up(AP_CON)
        if up.returncode != 0:
            return ApplyResult(self.cfg.mode, "none", False, f"{reason}; access point failed: {up.stderr.strip()}")
        return ApplyResult(self.cfg.mode, "ap", False, f"{reason}; running the access point until the Pi restarts")

    def _apply_ap(self) -> ApplyResult:
        self._ensure_ap(autoconnect=True)
        for name in self._uplink_profiles():
            # Their higher priority would otherwise win at the next boot,
            # rejoining a network instead of starting the AP.
            self._set_autoconnect(name, False)
            self._down(name)
        up = self._up(AP_CON)
        if up.returncode != 0:
            return ApplyResult("ap", "none", False, f"access point failed: {up.stderr.strip()}")
        return ApplyResult("ap", "ap", True, "access point up")

    def _apply_joined(self) -> ApplyResult:
        if self.cable_connected():
            # The cable is the internet connection: the radio is free for the AP.
            # Not persistent: at boot the known networks autoconnect, and the app
            # moves the radio back to the AP if the cable is still there.
            self._ensure_ap(autoconnect=False)
            for name in self.active():
                if is_uplink_con(name):
                    self._down(name)
            up = self._up(AP_CON)
            if up.returncode != 0:
                return ApplyResult("joined", "none", False, f"access point failed: {up.stderr.strip()}")
            return ApplyResult("joined", "ap+cable", True,
                               "network cable connected: internet over the cable, access point on WiFi")
        if not self.networks:
            return self.fall_back_to_ap("no known networks configured")
        self._ensure_ap(autoconnect=False)
        self._ensure_uplinks(self.cfg.ap_interface)
        self._down(AP_CON)  # one radio: it can be an AP or a client, not both
        joined, detail = self._join(self.cfg.ap_interface)
        if joined:
            return ApplyResult("joined", "joined", True, detail)
        return self.fall_back_to_ap(detail)

    def _apply_dual(self) -> ApplyResult:
        self._ensure_ap(autoconnect=True)
        up = self._up(AP_CON)
        if up.returncode != 0:
            return ApplyResult("dual", "none", False, f"access point failed: {up.stderr.strip()}")
        dongle = self.dongle()
        if dongle is None:
            for name in self._uplink_profiles():
                self._down(name)
            return ApplyResult("dual", "ap", False, "no USB WiFi dongle found; running AP only")
        if not self.networks:
            return ApplyResult("dual", "ap", False, "no known networks configured; running AP only")
        self._ensure_uplinks(dongle)
        joined, detail = self._join(dongle)
        if joined:
            return ApplyResult("dual", "dual", True, f"AP on {self.cfg.ap_interface}; {detail} on {dongle}")
        return ApplyResult("dual", "ap", False, f"{detail}; running AP only")

    def _join(self, device: str) -> tuple[bool, str]:
        """Try the known networks in range, in order of preference."""
        visible = self.visible_ssids(device)
        candidates = [(i, ssid) for i, (ssid, _) in enumerate(self.networks) if ssid in visible]
        if not candidates:
            names = ", ".join(ssid for ssid, _ in self.networks)
            return False, f"none of the known networks ({names}) is in range"
        errors = []
        for i, ssid in candidates:
            r = self._up(uplink_con(i), wait=self.cfg.join_timeout_s)
            if r.returncode == 0:
                return True, f"joined {ssid}"
            errors.append(f"{ssid}: {r.stderr.strip() or 'failed'}")
            log.error("could not join %s: %s", ssid, r.stderr.strip())
        return False, "could not join " + "; ".join(errors)

    # --- nmcli primitives -------------------------------------------------

    def _connections(self) -> set[str]:
        out = self._nmcli("-t", "-f", "NAME", "connection", "show").stdout
        return {_unescape(line) for line in out.splitlines() if line}

    def _uplink_profiles(self) -> list[str]:
        return sorted(n for n in self._connections() if is_uplink_con(n))

    def _ensure_ap(self, autoconnect: bool) -> None:
        self._write_sharing()  # before the AP (re)starts, so its dnsmasq reads it
        self._ensure(AP_CON, self.cfg.ap_interface, [
            "connection.autoconnect", _yn(autoconnect),
            "connection.autoconnect-priority", "10",
            "802-11-wireless.ssid", self.cfg.ap_ssid,
            "802-11-wireless.mode", "ap",
            "802-11-wireless.band", "bg",
            "802-11-wireless.powersave", POWERSAVE_OFF,
            "ipv4.method", "shared",
            "ipv6.method", "disabled",
            "wifi-sec.key-mgmt", "wpa-psk",
            "wifi-sec.psk", self.cfg.ap_psk,
        ])

    def _write_sharing(self) -> None:
        """Write whether the AP offers internet. Rewritten in place: the directory is root's."""
        want = SHARED if self.cfg.ap_share_internet else LOCAL_ONLY
        try:
            if self.sharing_conf.read_text() == want:
                self.sharing_error = None
                return
            with open(self.sharing_conf, "r+") as f:
                f.truncate(0)
                f.write(want)
                f.flush()
                os.fsync(f.fileno())
            self.sharing_error = None
        except OSError as e:
            self.sharing_error = (f"cannot set internet sharing ({e}); "
                                  "rerun install.sh to create the setting file")
            log.error("%s", self.sharing_error)

    def _ensure_uplinks(self, interface: str) -> None:
        """One profile per known network, preferred first; profiles for removed networks go."""
        existing = set(self._uplink_profiles())
        count = len(self.networks)
        for i, (ssid, psk) in enumerate(self.networks):
            name = uplink_con(i)
            props = [
                "connection.autoconnect", "yes",
                "connection.autoconnect-priority", str(40 - min(i, 19)),  # above the AP's 10
                "802-11-wireless.ssid", ssid,
                "802-11-wireless.mode", "infrastructure",
                "802-11-wireless.powersave", POWERSAVE_OFF,
                "ipv4.method", "auto",
            ]
            if psk:
                props += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", psk]
            elif name in existing:
                # Open network: drop security left over from a previous password.
                # Not an error if there was none.
                self.runner(["nmcli", "connection", "modify", name, "remove", "wifi-sec"], timeout=30)
            self._ensure(name, interface, props)
        for name in existing - {uplink_con(i) for i in range(count)}:
            self.runner(["nmcli", "connection", "delete", name], timeout=30)

    def _ensure(self, name: str, interface: str, props: list[str]) -> None:
        props = ["connection.interface-name", interface, *props]
        if name in self._connections():
            self._nmcli("connection", "modify", name, *props)
        else:
            self._nmcli("connection", "add", "type", "wifi", "con-name", name,
                        "ifname", interface, *props)

    def _set_autoconnect(self, name: str, on: bool) -> None:
        self._nmcli("connection", "modify", name, "connection.autoconnect", _yn(on))

    def _up(self, name: str, wait: float = 30) -> subprocess.CompletedProcess:
        return self.runner(["nmcli", "--wait", str(int(wait)), "connection", "up", name],
                           timeout=wait + 15)

    def _down(self, name: str) -> None:
        # Not an error if it was already down or never existed.
        self.runner(["nmcli", "connection", "down", name], timeout=30)

    def _nmcli(self, *args: str) -> subprocess.CompletedProcess:
        r = self.runner(["nmcli", *args], timeout=30)
        if r.returncode != 0:
            raise RuntimeError(f"nmcli {' '.join(args[:3])}: {r.stderr.strip()}")
        return r


class Watchdog:
    """Single radio: run the AP until reboot if no known network for ``fallback_after_s``.

    Called every few seconds by the app. Counts from start-up too, so a Pi
    that boots out of range of every known network still becomes reachable.
    """

    def __init__(self, net: NetworkManager, now: float) -> None:
        self.net = net
        self.last_ok = now
        self.fell_back: ApplyResult | None = None
        self.cable: bool | None = None  # last seen; None until the first check

    def reset(self, now: float) -> None:
        """After a deliberate change on the admin page: start watching afresh."""
        self.last_ok = now
        self.fell_back = None

    def check(self, now: float) -> ApplyResult | None:
        """Returns a result whenever it changed the network, else None.

        A cable plugged in or out is a deliberate change: the network is
        re-applied at once, even after a fallback.
        """
        if self.net.cfg.mode != "joined" or not self.net.available():
            return None
        try:
            cable = self.net.cable_connected()
        except RuntimeError as e:
            log.warning("could not read network state: %s", e)
            return None
        if self.cable is not None and cable != self.cable:
            self.cable = cable
            log.info("network cable %s; re-applying the network", "connected" if cable else "disconnected")
            self.reset(now)
            result = self.net.apply()
            if result.effective == "ap":  # no cable and no known network: on the AP until reboot
                self.fell_back = result
            return result
        self.cable = cable
        if self.fell_back:
            return None
        try:
            if self.net.in_effect():
                self.last_ok = now
                return None
        except RuntimeError as e:
            log.warning("could not read network state: %s", e)
            return None
        if now - self.last_ok < self.net.cfg.fallback_after_s:
            return None
        names = ", ".join(ssid for ssid, _ in self.net.networks) or "none configured"
        self.fell_back = self.net.fall_back_to_ap(
            f"no known network ({names}) for {int(now - self.last_ok)} s")
        return self.fell_back


def _yn(v: bool) -> str:
    return "yes" if v else "no"


def _unescape(field: str) -> str:
    return field.replace("\\:", ":").replace("\\\\", "\\")


def _split_terse(line: str) -> tuple[str, str]:
    """Split one ``nmcli -t`` line of two fields, honouring ``\\:`` escapes."""
    i = 0
    while i < len(line):
        if line[i] == "\\":
            i += 2
            continue
        if line[i] == ":":
            return _unescape(line[:i]), _unescape(line[i + 1:])
        i += 1
    return _unescape(line), ""
