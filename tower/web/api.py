"""The app's JSON API and its admin routes (design C10, C15, C16, C17).

Public: ``/api/health``, ``/api/info``, ``/api/diagnostics``, the QR codes.
Diagnostics are public on purpose: it is the page someone in a tower reads
down a phone line, and they may not know the PIN. It holds no secrets.

Admin (PIN session): releases, update upload, rollback, network mode.
"""

from __future__ import annotations

import logging
import shutil
import threading
import time
from dataclasses import replace
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Callable

from tower import config, version
from tower.clock import Clock
from tower.net import AP_ADDRESS, NetworkManager
from tower.release import ReleaseError, ReleaseManager, host
from tower.web import qr
from tower.web.auth import AdminAuth, AuthError
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
        self._update_lock = threading.Lock()

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
        }

    def _admin(self, route: Callable[[Request], Response]) -> Callable[[Request], Response]:
        def guarded(req: Request) -> Response:
            if not self.auth.check(req.cookie(COOKIE)):
                raise HttpError(HTTPStatus.UNAUTHORIZED, "admin PIN required")
            return route(req)

        return guarded

    # --- public --------------------------------------------------------------

    def health(self, req: Request) -> Response:
        # M2 adds real checks: audio device opens, sensor opens or is absent-but-expected.
        checks = {"http": "ok", "audio": "not implemented (M2)", "source": "not implemented (M2)"}
        return json_response({"status": "ok", "version": version.full_version(), "checks": checks})

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
        return json_response({
            "version": version.info(),
            "uptime_s": round(self.clock.now() - self.started, 1),
            "wall_clock": {
                "now": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "trusted": "unknown (NTP/browser time arrives in M2)",
            },
            "update": {**self.releases.status(), "systemd": host.systemd_available()},
            "network": {**net, "last_apply": self._net_result},
            "disk": disk,
            "source": "not implemented (M2): no dropped-byte count yet",
            "audio": "not implemented (M2): no underrun or voice-steal counts yet",
            "sse": "not implemented (M2): no client or drop counts yet",
            "clock_offset": "not implemented (M2)",
        })

    # --- admin session -----------------------------------------------------

    def session(self, req: Request) -> Response:
        return json_response({"has_pin": self.auth.has_pin(),
                              "logged_in": self.auth.check(req.cookie(COOKIE))})

    def login(self, req: Request) -> Response:
        pin = str(req.json().get("pin", ""))
        try:
            token = self.auth.login(pin)
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
        return json_response({**status, "last_apply": self._net_result,
                              "uplink_psk_set": bool(self.cfg.network.uplink_psk)})

    def set_network(self, req: Request) -> Response:
        """Persist the mode, then apply it in the background.

        The response must go out first: applying may take down the very AP
        this request arrived on.
        """
        body = req.json()
        allowed = {"mode", "ap_ssid", "ap_psk", "uplink_ssid", "uplink_psk"}
        values = {k: v for k, v in body.items() if k in allowed}
        if not values:
            raise HttpError(HTTPStatus.BAD_REQUEST, f"expected some of {sorted(allowed)}")
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

    def apply_network(self) -> None:
        with self._net_lock:
            # Let the response reach the phone before the AP drops.
            self.clock.sleep_until(self.clock.now() + 1.0)
            try:
                self._net_result = self.net.apply().as_dict()
            except Exception as e:  # noqa: BLE001
                log.exception("network apply failed")
                self._net_result = {"ok": False, "detail": str(e)}
