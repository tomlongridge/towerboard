"""Ringing routes: the live event stream, stroke reset, calibration, sound packs.

Public, because they are the everyday path (design C17): the event stream
and "reset strokes". Admin (PIN): calibration and test strikes, volume,
sound pack upload and selection, and setting the time from a phone.

Changes reach the RT process as control datagrams; anything that must
survive a restart is written to state first (calibration.json, overrides),
so the RT process also picks it up when it next starts.
"""

from __future__ import annotations

import time
from http import HTTPStatus
from typing import TYPE_CHECKING, Callable

from tower import config, version
from tower.rt import soundpack
from tower.rt.calibration import Calibration
from tower.web.events import stream
from tower.web.server import HttpError, Request, Response, Routes, json_response

if TYPE_CHECKING:
    from tower.web.api import TowerApp

MAX_PACK_BYTES = soundpack.MAX_ZIP_BYTES
VOLUME_RANGE_DB = (-40.0, 6.0)


class RingingApi:
    def __init__(self, app: TowerApp) -> None:
        self.app = app
        self.calibration = Calibration(app.cfg.state_dir / "calibration.json")

    @property
    def packs_dir(self):
        return self.app.cfg.state_dir / "soundpacks"

    def routes(self, admin: Callable) -> Routes:
        return {
            ("GET", "/api/events"): self.events,
            ("POST", "/api/strokes/reset"): self.reset_strokes,
            ("GET", "/api/admin/audio"): admin(self.audio_status),
            ("POST", "/api/admin/calibration"): admin(self.calibrate),
            ("POST", "/api/admin/test-strike"): admin(self.test_strike),
            ("POST", "/api/admin/volume"): admin(self.volume),
            ("POST", "/api/admin/soundpack"): admin(self.upload_pack),
            ("POST", "/api/admin/soundpack/select"): admin(self.select_pack),
            ("POST", "/api/admin/time"): admin(self.set_time),
        }

    # --- public ------------------------------------------------------------------

    def snapshot(self) -> dict:
        rt = self.app.bus.rt_status if self.app.bus.rt_fresh() else None
        return {
            # A page that sees this change after a reconnect reloads itself: the
            # wall display is never touched by hand, so an update must reach it.
            "version": version.full_version(),
            "rt_reporting": rt is not None,
            "pack": rt["pack"] if rt else None,
            "source": (rt or {}).get("source", {}).get("status"),
            "audio": (rt or {}).get("audio", {}).get("status"),
        }

    def events(self, req: Request) -> Response:
        bus, stop = self.app.bus, self.app.stop
        return Response(200, content_type="text/event-stream",
                        stream=lambda write: stream(bus, self.snapshot, write, stop))

    def reset_strokes(self, req: Request) -> Response:
        sent = self.app.control.send({"cmd": "reset_strokes"})
        self.app.bus.emit("state", {"strokes_reset": True})
        return json_response({"sent": sent})

    # --- admin: calibration ------------------------------------------------------------

    def audio_status(self, req: Request) -> Response:
        self.calibration.load()
        rt = self.app.bus.rt_status if self.app.bus.rt_fresh() else None
        return json_response({
            "packs": soundpack.installed(self.packs_dir),
            "active": self.app.cfg.audio.pack,
            "volume_db": self.app.cfg.audio.volume_db,
            "calibration_ms": self.calibration.as_dict(),
            "step_ms": 5,
            "rt": rt,
        })

    def calibrate(self, req: Request) -> Response:
        body = req.json()
        bell, stroke = body.get("bell"), body.get("stroke")
        try:
            if "steps" in body and isinstance(body["steps"], int):
                ms = self.calibration.nudge(bell, stroke, body["steps"])
            elif isinstance(body.get("ms"), (int, float)):
                ms = self.calibration.set(bell, stroke, body["ms"])
            else:
                raise ValueError("send steps (int) or ms (number)")
        except (ValueError, TypeError) as e:
            raise HttpError(HTTPStatus.BAD_REQUEST, str(e)) from None
        self.calibration.save()
        sent = self.app.control.send({"cmd": "reload_calibration"})
        return json_response({"bell": bell, "stroke": stroke, "ms": ms, "applied": sent})

    def test_strike(self, req: Request) -> Response:
        body = req.json()
        bell = body.get("bell")
        if not isinstance(bell, int) or not 1 <= bell <= 16:
            raise HttpError(HTTPStatus.BAD_REQUEST, "bell must be 1..16")
        sent = self.app.control.send({"cmd": "test_strike", "bell": bell, "stroke": body.get("stroke", "hand")})
        return json_response({"sent": sent})

    def volume(self, req: Request) -> Response:
        db = req.json().get("db")
        if not isinstance(db, (int, float)) or not VOLUME_RANGE_DB[0] <= db <= VOLUME_RANGE_DB[1]:
            raise HttpError(HTTPStatus.BAD_REQUEST, f"db must be within {VOLUME_RANGE_DB}")
        self._save("audio", {"volume_db": float(db)})
        sent = self.app.control.send({"cmd": "volume", "db": float(db)})
        return json_response({"volume_db": float(db), "applied": sent})

    # --- admin: sound packs -----------------------------------------------------------

    def upload_pack(self, req: Request) -> Response:
        n = req.content_length
        if n == 0:
            raise HttpError(HTTPStatus.BAD_REQUEST, "empty upload")
        if n > MAX_PACK_BYTES:
            raise HttpError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "sound pack too large")
        incoming = self.app.cfg.state_dir / "incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        upload = incoming / f"pack-{time.time_ns()}.zip"
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
                pack = soundpack.install_zip(upload, self.packs_dir, self.app.cfg.audio.rate)
            except soundpack.PackError as e:
                raise HttpError(HTTPStatus.UNPROCESSABLE_ENTITY, f"rejected: {e}") from None
        finally:
            upload.unlink(missing_ok=True)
        if pack.id == self.app.cfg.audio.pack:  # replaced the pack in use: reload it
            self.app.control.send({"cmd": "pack", "id": pack.id})
        return json_response({"installed": pack.summary()}, HTTPStatus.CREATED)

    def select_pack(self, req: Request) -> Response:
        pack_id = req.json().get("id")
        if pack_id not in {p["id"] for p in soundpack.installed(self.packs_dir)}:
            raise HttpError(HTTPStatus.BAD_REQUEST, f"sound pack {pack_id!r} is not installed")
        self._save("audio", {"pack": pack_id})
        sent = self.app.control.send({"cmd": "pack", "id": pack_id})
        return json_response({"active": pack_id, "applied": sent})

    # --- admin: time -------------------------------------------------------------------

    def set_time(self, req: Request) -> Response:
        epoch_ms = req.json().get("epoch_ms")
        if not isinstance(epoch_ms, (int, float)):
            raise HttpError(HTTPStatus.BAD_REQUEST, "epoch_ms required")
        try:
            used = self.app.wallclock.accept_browser(epoch_ms / 1000)
        except ValueError as e:
            raise HttpError(HTTPStatus.BAD_REQUEST, str(e)) from None
        return json_response({"used": used, **self.app.wallclock.status()})

    def _save(self, section: str, values: dict) -> None:
        from dataclasses import replace

        try:
            config.save_overrides(section, values, self.app.overrides_path)
        except config.ConfigError as e:
            raise HttpError(HTTPStatus.BAD_REQUEST, str(e)) from None
        cfg = self.app.cfg
        self.app.cfg = replace(cfg, **{section: replace(getattr(cfg, section), **values)})
