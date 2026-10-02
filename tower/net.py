"""Network manager (design C16): ``ap`` | ``joined`` | ``dual`` via NetworkManager.

* ``ap`` — onboard radio runs the ringers' access point. Default; needs no dongle.
* ``joined`` — onboard radio joins the tower's WiFi instead.
* ``dual`` — onboard radio stays the AP; a USB dongle joins the upstream network.

The dongle is optional in every mode: without it, ``dual`` degrades to ``ap``.
A failed join always falls back to the AP, so a typo in a passphrase
cannot lock everyone out of the admin page.

Two NetworkManager profiles are owned by the app, ``tower-ap`` and
``tower-uplink``, and modified in place so the change survives reboot
through NM's own autoconnect. Nothing hand-rolls hostapd or dnsmasq; the AP
uses ``ipv4.method shared`` (NM's built-in DHCP, gateway 10.42.0.1).

All behaviour goes through ``nmcli`` via an injected runner. Off the Pi
there is no ``nmcli``, and ``available()`` says so rather than pretending.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable

from tower.config import NetworkSection

log = logging.getLogger(__name__)

AP_CON = "tower-ap"
UPLINK_CON = "tower-uplink"
AP_ADDRESS = "10.42.0.1"  # NetworkManager's default for ipv4.method shared

Runner = Callable[..., subprocess.CompletedProcess]


def _run(argv: list[str], timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


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
    def __init__(self, cfg: NetworkSection, runner: Runner | None = None) -> None:
        self.cfg = cfg
        self.runner = runner or _run
        self._available = runner is not None or shutil.which("nmcli") is not None

    def available(self) -> bool:
        return self._available

    # --- inspection ------------------------------------------------------

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

    def status(self) -> dict:
        if not self.available():
            return {"available": False, "detail": "nmcli not found (not running on the Pi)",
                    "mode": self.cfg.mode}
        try:
            active = self.active()
            return {
                "available": True,
                "mode": self.cfg.mode,
                "ap_active": AP_CON in active,
                "uplink_active": UPLINK_CON in active,
                "wifi_devices": self.wifi_devices(),
                "dongle": self.dongle(),
                "ap_ssid": self.cfg.ap_ssid,
                "uplink_ssid": self.cfg.uplink_ssid or None,
            }
        except (OSError, subprocess.SubprocessError, RuntimeError) as e:
            return {"available": True, "mode": self.cfg.mode, "error": str(e)}

    def in_effect(self) -> bool:
        """Whether the configured mode is already what the radios are doing."""
        active = self.active()
        if self.cfg.mode == "ap":
            return AP_CON in active and UPLINK_CON not in active
        if self.cfg.mode == "joined":
            return UPLINK_CON in active
        return AP_CON in active and (UPLINK_CON in active or self.dongle() is None)

    # --- applying modes ----------------------------------------------------

    def apply(self) -> ApplyResult:
        mode = self.cfg.mode
        if mode == "ap":
            return self._apply_ap(mode, "access point up")
        if mode == "joined":
            return self._apply_joined()
        return self._apply_dual()

    def _apply_ap(self, requested: str, detail: str) -> ApplyResult:
        self._ensure_ap(autoconnect=True)
        self._down(UPLINK_CON)
        up = self._up(AP_CON)
        if up.returncode != 0:
            return ApplyResult(requested, "none", False, f"access point failed: {up.stderr.strip()}")
        return ApplyResult(requested, "ap", requested == "ap", detail)

    def _apply_joined(self) -> ApplyResult:
        if not self.cfg.uplink_ssid:
            return self._apply_ap("joined", "no uplink SSID configured; staying in AP mode")
        self._ensure_ap(autoconnect=False)
        self._ensure_uplink(self.cfg.ap_interface)
        self._down(AP_CON)  # one radio: it can be an AP or a client, not both
        joined = self._up(UPLINK_CON, wait=self.cfg.join_timeout_s)
        if joined.returncode == 0:
            return ApplyResult("joined", "joined", True, f"joined {self.cfg.uplink_ssid}")
        log.error("join failed, falling back to AP: %s", joined.stderr.strip())
        self._set_autoconnect(UPLINK_CON, False)
        return self._apply_ap("joined", f"could not join {self.cfg.uplink_ssid}: "
                                        f"{joined.stderr.strip()}; fell back to AP")

    def _apply_dual(self) -> ApplyResult:
        self._ensure_ap(autoconnect=True)
        up = self._up(AP_CON)
        if up.returncode != 0:
            return ApplyResult("dual", "none", False, f"access point failed: {up.stderr.strip()}")
        dongle = self.dongle()
        if dongle is None:
            self._down(UPLINK_CON)
            return ApplyResult("dual", "ap", False, "no USB WiFi dongle found; running AP only")
        if not self.cfg.uplink_ssid:
            return ApplyResult("dual", "ap", False, "no uplink SSID configured; running AP only")
        self._ensure_uplink(dongle)
        joined = self._up(UPLINK_CON, wait=self.cfg.join_timeout_s)
        if joined.returncode == 0:
            return ApplyResult("dual", "dual", True,
                               f"AP on {self.cfg.ap_interface}, joined {self.cfg.uplink_ssid} on {dongle}")
        return ApplyResult("dual", "ap", False,
                           f"could not join {self.cfg.uplink_ssid} on {dongle}: {joined.stderr.strip()}")

    # --- nmcli primitives -------------------------------------------------

    def _connections(self) -> set[str]:
        out = self._nmcli("-t", "-f", "NAME", "connection", "show").stdout
        return {_unescape(line) for line in out.splitlines() if line}

    def _ensure_ap(self, autoconnect: bool) -> None:
        self._ensure(AP_CON, self.cfg.ap_interface, [
            "connection.autoconnect", _yn(autoconnect),
            "connection.autoconnect-priority", "10",
            "802-11-wireless.ssid", self.cfg.ap_ssid,
            "802-11-wireless.mode", "ap",
            "802-11-wireless.band", "bg",
            "ipv4.method", "shared",
            "ipv6.method", "disabled",
            "wifi-sec.key-mgmt", "wpa-psk",
            "wifi-sec.psk", self.cfg.ap_psk,
        ])

    def _ensure_uplink(self, interface: str) -> None:
        props = [
            "connection.autoconnect", "yes",
            "connection.autoconnect-priority", "20",
            "802-11-wireless.ssid", self.cfg.uplink_ssid,
            "802-11-wireless.mode", "infrastructure",
            "ipv4.method", "auto",
        ]
        if self.cfg.uplink_psk:
            props += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", self.cfg.uplink_psk]
        elif UPLINK_CON in self._connections():
            # Open network: drop security left over from a previous passphrase.
            # Not an error if there was none.
            self.runner(["nmcli", "connection", "modify", UPLINK_CON, "remove", "wifi-sec"],
                        timeout=30)
        self._ensure(UPLINK_CON, interface, props)

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
