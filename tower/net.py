"""Network manager (design C16): behaviour follows the hardware; there are no modes.

Phones always connect through the Pi's own access point on the onboard
radio, so the QR codes on the wall work in every tower. The Pi decides how
(and whether) it reaches the internet from what is plugged in:

1. ``cable`` — a network cable is connected: internet over the cable.
2. ``dongle`` — otherwise, a USB WiFi dongle and known networks: the dongle
   joins the first known network in range.
3. ``single`` — otherwise, known networks but one radio: the Pi is offline,
   except during an update check (``go_online`` … ``back_to_ap``), when the
   radio leaves the AP briefly to join a known network.
4. ``offline`` — no known networks: access point only, never online.

The Pi is never left without its access point outside an update check.

The app owns these NetworkManager profiles and modifies them in place:
``tower-ap``, and one per known network: ``tower-uplink``,
``tower-uplink-2``, … On the dongle they autoconnect, so NM itself picks
whichever known network is in range. On the onboard radio they never
autoconnect: the AP does, so the Pi always boots onto its AP. Nothing
hand-rolls hostapd or dnsmasq; the AP uses ``ipv4.method shared`` (NM's
built-in DHCP, gateway 10.42.0.1).

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

PLANS = ("cable", "dongle", "single", "offline")

Runner = Callable[..., subprocess.CompletedProcess]


def _run(argv: list[str], timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


def uplink_con(index: int) -> str:
    return UPLINK_CON if index == 0 else f"{UPLINK_CON}-{index + 1}"


def is_uplink_con(name: str) -> bool:
    return name == UPLINK_CON or (name.startswith(UPLINK_CON + "-") and name[len(UPLINK_CON) + 1:].isdigit())


@dataclass
class ApplyResult:
    plan: str
    ok: bool
    detail: str

    def as_dict(self) -> dict:
        return {"plan": self.plan, "ok": self.ok, "detail": self.detail}


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

    # --- what the hardware says -----------------------------------------------

    def plan(self) -> str:
        if self.cable_connected():
            return "cable"
        if not self.networks:
            return "offline"
        if self.dongle():
            return "dongle"
        return "single"

    def cable_connected(self) -> bool:
        """Whether a wired connection is up (a cable plugged in and an address obtained)."""
        out = self._nmcli("-t", "-f", "TYPE,STATE", "device").stdout
        return any(_split_terse(line) == ("ethernet", "connected") for line in out.splitlines())

    def wifi_devices(self) -> list[str]:
        out = self._nmcli("-t", "-f", "DEVICE,TYPE", "device").stdout
        rows = (_split_terse(line) for line in out.splitlines() if line)
        return [dev for dev, kind in rows if kind == "wifi"]

    def dongle(self) -> str | None:
        """First WiFi device that is not the onboard AP radio."""
        return next((d for d in self.wifi_devices() if d != self.cfg.ap_interface), None)

    def active(self) -> dict[str, str]:
        out = self._nmcli("-t", "-f", "NAME,DEVICE", "connection", "show", "--active").stdout
        return dict(_split_terse(line) for line in out.splitlines() if line)

    def online(self) -> bool:
        """Whether the Pi can reach the internet right now, without disturbing the AP."""
        plan = self.plan()
        if plan == "cable":
            return True
        if plan == "dongle":
            dongle = self.dongle()
            return any(is_uplink_con(n) and d == dongle for n, d in self.active().items())
        return False

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

    def status(self) -> dict:
        if not self.available():
            return {"available": False, "detail": "nmcli not found (not running on the Pi)"}
        try:
            active = self.active()
            plan = self.plan()
            dongle = self.dongle()
            return {
                "available": True,
                "plan": plan,
                "online": self.online(),
                "ap_active": AP_CON in active,
                "cable_connected": plan == "cable",
                "dongle": dongle,
                "connected_ssid": self.connected_ssid(dongle) if dongle else None,
                "ap_share_internet": self.cfg.ap_share_internet,
                "sharing_error": self.sharing_error,
            }
        except (OSError, subprocess.SubprocessError, RuntimeError) as e:
            return {"available": True, "error": str(e)}

    def in_effect(self) -> bool:
        """The AP is up, and the onboard radio is not a client of anything."""
        active = self.active()
        if AP_CON not in active:
            return False
        return not any(is_uplink_con(n) and d == self.cfg.ap_interface for n, d in active.items())

    # --- steady state -------------------------------------------------------------

    def apply(self) -> ApplyResult:
        """Bring the radios into line with the hardware: AP up, dongle (if any) online."""
        plan = self.plan()
        self._ensure_ap()
        dongle = self.dongle()
        if plan == "dongle" and dongle:
            self._ensure_uplinks(dongle, autoconnect=True)
        elif self.networks:
            # Single radio (or the cable makes the dongle unnecessary): the known
            # networks are only joined deliberately, during an update check.
            self._ensure_uplinks(self.cfg.ap_interface if plan == "single" or not dongle else dongle,
                                 autoconnect=False)
        for name, dev in self.active().items():
            if is_uplink_con(name) and (dev == self.cfg.ap_interface or plan == "cable"):
                self._down(name)
        up = self._ap_up()
        if up is not None and up.returncode != 0:
            return ApplyResult(plan, False, f"access point failed: {up.stderr.strip()}")
        if plan == "cable":
            return ApplyResult(plan, True, "network cable connected: internet over the cable, access point on WiFi")
        if plan == "offline":
            return ApplyResult(plan, True, "no known networks: access point only, never online")
        if plan == "single":
            return ApplyResult(plan, True, "single radio: access point on; online only during update checks")
        joined, detail = self._join(dongle)
        return ApplyResult(plan, joined, f"access point on {self.cfg.ap_interface}; {detail} on {dongle}")

    # --- single-radio update check ----------------------------------------------------

    def go_online(self) -> tuple[bool, str]:
        """Single radio: leave the AP and join the first known network that works.

        If none does, the AP comes straight back. Always pair with ``back_to_ap``.
        """
        if not self.networks:
            return False, "no known networks configured"
        self._ensure_uplinks(self.cfg.ap_interface, autoconnect=False)
        self._down(AP_CON)  # one radio: it can be an AP or a client, not both
        ok, detail = self._join(self.cfg.ap_interface)
        if not ok:
            self.back_to_ap()
        return ok, detail

    def back_to_ap(self) -> ApplyResult:
        for name, dev in self.active().items():
            if is_uplink_con(name) and dev == self.cfg.ap_interface:
                self._down(name)
        up = self._ap_up()
        if up is not None and up.returncode != 0:
            return ApplyResult("single", False, f"access point failed: {up.stderr.strip()}")
        return ApplyResult("single", True, "back on the access point")

    # --- internals ------------------------------------------------------------------

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

    def _ap_up(self) -> subprocess.CompletedProcess | None:
        """Start the AP unless it is already up (re-activating it would drop every phone)."""
        if AP_CON in self.active():
            return None
        return self._up(AP_CON)

    def _connections(self) -> set[str]:
        out = self._nmcli("-t", "-f", "NAME", "connection", "show").stdout
        return {_unescape(line) for line in out.splitlines() if line}

    def _uplink_profiles(self) -> list[str]:
        return sorted(n for n in self._connections() if is_uplink_con(n))

    def _ensure_ap(self) -> None:
        self._write_sharing()  # before the AP (re)starts, so its dnsmasq reads it
        self._ensure(AP_CON, self.cfg.ap_interface, [
            "connection.autoconnect", "yes",  # the Pi always boots onto its AP
            "connection.autoconnect-priority", "50",
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

    def _ensure_uplinks(self, interface: str, autoconnect: bool) -> None:
        """One profile per known network, preferred first; profiles for removed networks go."""
        existing = set(self._uplink_profiles())
        count = len(self.networks)
        for i, (ssid, psk) in enumerate(self.networks):
            name = uplink_con(i)
            props = [
                "connection.autoconnect", _yn(autoconnect),
                "connection.autoconnect-priority", str(40 - min(i, 19)),
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


class Supervisor:
    """Keeps the radios in line with the hardware. The app calls ``check`` every few seconds.

    Re-applies when a cable or dongle is plugged in or removed, when the known
    networks change, or when the AP has gone down unexpectedly. Paused while
    an update check has the radio.
    """

    def __init__(self, net: NetworkManager) -> None:
        self.net = net
        self.seen: tuple | None = None
        self.paused = False

    def check(self) -> ApplyResult | None:
        if self.paused or not self.net.available():
            return None
        try:
            now = (self.net.plan(), self.net.dongle(), tuple(self.net.networks))
            if now == self.seen and self.net.in_effect():
                return None
        except RuntimeError as e:
            log.warning("could not read network state: %s", e)
            return None
        if self.seen is not None and now[0] != self.seen[0]:
            log.info("network hardware changed: %s → %s", self.seen[0], now[0])
        self.seen = now
        return self.net.apply()


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
