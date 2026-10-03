"""The app's JSON API and its admin routes (design C10, C15, C16, C17).

Public: ``/api/health``, ``/api/info``, ``/api/diagnostics``, the QR codes.
Diagnostics are public on purpose: it is the page someone in a tower reads
down a phone line, and they may not know the PIN. It holds no secrets.

Admin (PIN session): releases, update upload, rollback, network mode.
Ringing routes (live events, calibration, sound packs) are in ``ringing.py``.
"""

from __future__ import annotations

import logging
import shutil
import threading
import time
from dataclasses import replace
from http import HTTPStatus
from pathlib import Path
from typing import Callable

from tower import config, ipc, version
from tower.clock import Clock
from tower.net import AP_ADDRESS, NetworkManager, Watchdog
from tower.release import ReleaseError, ReleaseManager, host
from tower.web import qr
from tower.wallclock import WallClock
from tower.web.auth import AdminAuth, AuthError, DamagedPinFile
from tower.web.events import EventBus
from tower.web.server import HttpError, Request, Response, Routes, json_response

log = logging.getLogger(__name__)

COOKIE = "tower_admin"
MAX_BUNDLE_BYTES = 256 * 1024 * 1024

# Hands an activation or rollback to whatever performs it, returning a status line.
Handoff = Callable[[str, "str | None"], str]


def systemd_handoff(state_dir: Path) -> Handoff:
    def handoff(action: str, version_: str | None) -> str:
        if not host.systemd_available():
            return ("not activated: systemd is not available on this host. "
                    "Updates are applied on the Pi.")
        host.write_request(state_dir, action, version_)
        host.start_updater()
        return f"handed to {host.UPDATER_UNIT}; the app will restart"

    return handoff


class TowerApp:
    def __init__(
        self,
        cfg: config.Config,
        clock: Clock,
        overrides_path: Path | None = None,
        net: NetworkManager | None = None,
        handoff: Handoff | None = None,
        wallclock: WallClock | None = None,
    ) -> None:
        self.cfg = cfg
        self.clock = clock
        self.started = clock.now()
        self.overrides_path = overrides_path
        self.auth = AdminAuth(cfg.state_dir / "admin.json", clock, cfg.admin.session_hours * 3600)
        self.releases = ReleaseManager(cfg.opt_dir, cfg.state_dir)
        self.net = net or NetworkManager(cfg.network)
        self.handoff = handoff or systemd_handoff(cfg.state_dir)
        self._net_lock = threading.Lock()
        self._net_result: dict | None = None
        self.watchdog = Watchdog(self.net, clock.now())
        self._update_lock = threading.Lock()
        self.bus = EventBus(clock)
        self.control = ipc.Sender(cfg.run_dir / ipc.CONTROL)  # app → RT, never blocks
        self.wallclock = wallclock or WallClock(cfg.state_dir / "wallclock.json")
        self.stop = threading.Event()  # ends SSE streams on shutdown
        from tower.web.ringing import RingingApi

        self.ringing = RingingApi(self)

    def close(self) -> None:
        self.stop.set()
        self.control.close()

    # --- routing -------------------------------------------------------------

    def routes(self) -> Routes:
        admin = self._admin
        return {
            ("GET", "/api/health"): self.health,
            ("GET", "/api/info"): self.info,
            ("GET", "/api/diagnostics"): self.diagnostics,
            ("GET", "/qr/wifi.svg"): self.qr_wifi,
            ("GET", "/qr/app.svg"): self.qr_app,
            ("GET", "/api/admin/session"): self.session,
            ("POST", "/api/admin/login"): self.login,
            ("POST", "/api/admin/logout"): self.logout,
            ("POST", "/api/admin/pin"): self.set_pin,
            ("GET", "/api/admin/releases"): admin(self.release_status),
            ("POST", "/api/admin/update"): admin(self.upload_update),
            ("POST", "/api/admin/rollback"): admin(self.rollback),
            ("GET", "/api/admin/network"): admin(self.network_status),
            ("POST", "/api/admin/network"): admin(self.set_network),
            **self.ringing.routes(admin),
        }

    def _admin(self, route: Callable[[Request], Response]) -> Callable[[Request], Response]:
        def guarded(req: Request) -> Response:
            if not self.auth.check(req.cookie(COOKIE)):
                raise HttpError(HTTPStatus.UNAUTHORIZED, "admin PIN required")
            return route(req)

        return guarded

    # --- public --------------------------------------------------------------

    def health(self, req: Request) -> Response:
        """Used by the update pipeline's health check (design C15 step 6).

        Checks are always reported; they only fail the status when the RT
        process is expected here (``rt.expected``), i.e. on the Pi.
        """
        checks = {"http": "ok", **self.rt_checks()}
        failing = [k for k, v in checks.items() if v != "ok" and not v.startswith("absent (expected)")]
        ok = not (self.cfg.rt.expected and failing)
        return json_response({"status": "ok" if ok else "degraded", "version": version.full_version(),
                              "checks": checks})

    def rt_checks(self) -> dict[str, str]:
        if not self.bus.rt_fresh():
            missing = "no report from the RT process"
            return {"rt": missing, "audio": missing, "source": missing}
        st = self.bus.rt_status or {}
        audio, source = st.get("audio", {}), st.get("source", {})
        if not self.cfg.audio.enabled:
            audio_check = "ok"
        elif audio.get("status") == "ok":
            audio_check = "ok"
        else:
            audio_check = f"{audio.get('status')}: {audio.get('detail', '')}".strip(": ")
        if source.get("status") == "open":
            source_check = "ok"
        elif source.get("status") == "absent" and not self.cfg.source.required:
            source_check = f"absent (expected): {source.get('detail', '')}"
        else:
            source_check = f"{source.get('status')}: {source.get('detail', '')}".strip(": ")
        rt_version = st.get("version")
        rt_check = "ok" if rt_version == version.full_version() else f"RT runs {rt_version!r}"
        return {"rt": rt_check, "audio": audio_check, "source": source_check}

    def info(self, req: Request) -> Response:
        return json_response({
            "tower": self.cfg.tower.name,
            "version": version.full_version(),
            "ap_ssid": self.cfg.network.ap_ssid,
            "ap_psk": self.cfg.network.ap_psk,  # shown on the wall by design
            "app_url": self._app_url(req),
        })

    def qr_wifi(self, req: Request) -> Response:
        return Response(200, qr.wifi_svg(self.cfg.network.ap_ssid, self.cfg.network.ap_psk),
                        "image/svg+xml")

    def qr_app(self, req: Request) -> Response:
        return Response(200, qr.url_svg(self._app_url(req)), "image/svg+xml")

    def _app_url(self, req: Request) -> str:
        host_header = req.headers.get("Host") or ""
        if not host_header or host_header.startswith(("localhost", "127.")):
            host_header = AP_ADDRESS if self.cfg.web.port == 80 else f"{AP_ADDRESS}:{self.cfg.web.port}"
        return f"http://{host_header}/"

    def diagnostics(self, req: Request) -> Response:
        """Honest about what exists: anything not built yet says so rather than looking healthy."""
        try:
            du = shutil.disk_usage(self.cfg.state_dir)
            disk = {"free_mb": du.free // 2**20, "total_mb": du.total // 2**20,
                    "path": str(self.cfg.state_dir)}
        except OSError as e:
            disk = {"error": str(e)}
        net = self.net.status()
        rt = self.bus.rt_status if self.bus.rt_fresh() else None
        age = None if self.bus.rt_status_at is None else round(self.clock.now() - self.bus.rt_status_at, 1)
        return json_response({
            "version": version.info(),
            "uptime_s": round(self.clock.now() - self.started, 1),
            "wall_clock": self.wallclock.status(),
            "update": {**self.releases.status(), "systemd": host.systemd_available()},
            "network": {**net, "last_apply": self._net_result},
            "disk": disk,
            "rt": {"reporting": rt is not None, "last_report_s_ago": age,
                   "bad_envelopes": self.bus.rt_bad, "control_dropped": self.control.dropped},
            "source": rt["source"] if rt else "no report from the RT process",
            "audio": rt["audio"] if rt else "no report from the RT process",
            "sound_pack": rt["pack"] if rt else None,
            "clock_offset_ms": rt["clock_offset_ms"] if rt else None,
            "sse": self.bus.stats(),
        })

    # --- admin session -----------------------------------------------------

    def session(self, req: Request) -> Response:
        return json_response({"has_pin": self.auth.has_pin(),
                              "logged_in": self.auth.check(req.cookie(COOKIE))})

    def login(self, req: Request) -> Response:
        pin = str(req.json().get("pin", ""))
        try:
            token = self.auth.login(pin)
        except DamagedPinFile as e:
            log.error("%s", e)
            raise HttpError(HTTPStatus.SERVICE_UNAVAILABLE, str(e)) from None
        except AuthError as e:
            raise HttpError(HTTPStatus.UNAUTHORIZED, str(e)) from None
        return self._with_session({"logged_in": True}, token)

    def logout(self, req: Request) -> Response:
        self.auth.logout(req.cookie(COOKIE))
        return json_response({"logged_in": False},
                             headers=[("Set-Cookie", f"{COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict")])

    def set_pin(self, req: Request) -> Response:
        pin = str(req.json().get("pin", ""))
        try:
            token = self.auth.set_pin(pin, req.cookie(COOKIE))
        except AuthError as e:
            raise HttpError(HTTPStatus.BAD_REQUEST, str(e)) from None
        return self._with_session({"logged_in": True}, token)

    def _with_session(self, body: dict, token: str) -> Response:
        max_age = int(self.cfg.admin.session_hours * 3600)
        cookie = f"{COOKIE}={token}; Path=/; Max-Age={max_age}; HttpOnly; SameSite=Strict"
        return json_response(body, headers=[("Set-Cookie", cookie)])

    # --- admin: updates ------------------------------------------------------

    def release_status(self, req: Request) -> Response:
        return json_response({**self.releases.status(), "running": version.full_version(),
                              "systemd": host.systemd_available()})

    def upload_update(self, req: Request) -> Response:
        """Body is the raw ``.tower`` file (no multipart; the stdlib no longer parses it)."""
        n = req.content_length
        if n == 0:
            raise HttpError(HTTPStatus.BAD_REQUEST, "empty upload")
        if n > MAX_BUNDLE_BYTES:
            raise HttpError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "bundle too large")
        if not self._update_lock.acquire(blocking=False):
            raise HttpError(HTTPStatus.CONFLICT, "another update is being staged")
        incoming = self.cfg.state_dir / "incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        upload = incoming / f"upload-{time.time_ns()}.tower"
        try:
            with open(upload, "wb") as f:
                remaining = n
                while remaining:
                    chunk = req.body.read(min(remaining, 1 << 20))
                    if not chunk:
                        raise HttpError(HTTPStatus.BAD_REQUEST, "upload truncated")
                    f.write(chunk)
                    remaining -= len(chunk)
            try:
                staged = self.releases.stage(upload, Path(self.cfg.update.allowed_signers))
            except ReleaseError as e:
                log.error("rejected upload: %s", e)
                raise HttpError(HTTPStatus.UNPROCESSABLE_ENTITY, f"rejected: {e}") from None
        finally:
            upload.unlink(missing_ok=True)
            self._update_lock.release()
        try:
            activation = self.handoff("activate", staged)
        except Exception as e:  # noqa: BLE001
            activation = f"staged but could not start activation: {e}"
        return json_response({"staged": staged, "activation": activation}, HTTPStatus.ACCEPTED)

    def rollback(self, req: Request) -> Response:
        if not self.releases.previous():
            raise HttpError(HTTPStatus.CONFLICT, "no previous release to roll back to")
        try:
            status = self.handoff("rollback", None)
        except Exception as e:  # noqa: BLE001
            raise HttpError(HTTPStatus.INTERNAL_SERVER_ERROR, f"could not start rollback: {e}") from None
        return json_response({"rollback": status}, HTTPStatus.ACCEPTED)

    # --- admin: network ------------------------------------------------------

    def network_status(self, req: Request) -> Response:
        status = self.net.status()
        fallback = self.watchdog.fell_back
        return json_response({
            **status,
            # Settings come from config, not from NetworkManager, so the form can
            # always be filled in, even when nmcli can't be read.
            "mode": self.cfg.network.mode,
            "ap_ssid": self.cfg.network.ap_ssid,
            "ap_share_internet": self.cfg.network.ap_share_internet,
            "last_apply": self._net_result,
            # Passwords never leave the Pi; the page only learns whether one is set.
            "known_networks": [{"ssid": ssid, "password_set": bool(psk)}
                               for ssid, psk in self.cfg.network.uplink_networks()],
            "fallback": fallback.as_dict() if fallback else None,
        })

    def set_network(self, req: Request) -> Response:
        """Persist the mode, then apply it in the background.

        The response must go out first: applying may take down the very AP
        this request arrived on.
        """
        body = req.json()
        allowed = {"mode", "ap_ssid", "ap_psk", "ap_share_internet", "uplinks"}
        values = {k: v for k, v in body.items() if k in allowed}
        if not values:
            raise HttpError(HTTPStatus.BAD_REQUEST, f"expected some of {sorted(allowed)}")
        if "uplinks" in values:
            values.update(self._known_networks(values["uplinks"]))
        try:
            config.save_overrides("network", values, self.overrides_path)
        except config.ConfigError as e:
            raise HttpError(HTTPStatus.BAD_REQUEST, str(e)) from None
        self.cfg = replace(self.cfg, network=replace(self.cfg.network, **values))
        self.net.cfg = self.cfg.network
        if not self.net.available():
            return json_response({"saved": True, "applied": False,
                                  "detail": "saved; nmcli is not available on this host"})
        threading.Thread(target=self.apply_network, name="net-apply", daemon=True).start()
        return json_response({"saved": True, "applied": "in progress"}, HTTPStatus.ACCEPTED)

    def _known_networks(self, entries: object) -> dict:
        """The page's list of known networks → config values.

        A network sent without a password keeps the one already saved for it,
        since the page never receives saved passwords to send back.
        """
        if not isinstance(entries, list) or not all(
                isinstance(e, dict) and isinstance(e.get("ssid"), str) for e in entries):
            raise HttpError(HTTPStatus.BAD_REQUEST, 'uplinks must be a list of {"ssid": ..., "psk": ...}')
        saved = dict(self.cfg.network.uplink_networks())
        uplinks = []
        for e in entries:
            ssid = e["ssid"].strip()
            if not ssid:
                continue
            psk = e.get("psk") or saved.get(ssid, "")
            uplinks.append({"ssid": ssid, "psk": psk})
        # The list replaces the older single-network setting.
        return {"uplinks": uplinks, "uplink_ssid": "", "uplink_psk": ""}

    def apply_network(self) -> None:
        with self._net_lock:
            # Let the response reach the phone before the AP drops.
            self.clock.sleep_until(self.clock.now() + 1.0)
            try:
                result = self.net.apply()
                self._net_result = result.as_dict()
                self.watchdog.reset(self.clock.now())
                if self.cfg.network.mode == "joined" and result.effective == "ap":
                    self.watchdog.fell_back = result  # already on the AP until reboot
            except Exception as e:  # noqa: BLE001
                log.exception("network apply failed")
                self._net_result = {"ok": False, "detail": str(e)}

    def run_watchdog(self, stop: threading.Event, interval_s: float = 10.0) -> None:
        """Single radio: fall back to the AP until reboot when no known network is reachable."""
        while not stop.wait(interval_s):
            if not self._net_lock.acquire(blocking=False):
                continue  # a deliberate change is being applied
            try:
                result = self.watchdog.check(self.clock.now())
                if result:
                    self._net_result = result.as_dict()
            except Exception:  # noqa: BLE001 — never let the watchdog die
                log.exception("network watchdog failed")
            finally:
                self._net_lock.release()
