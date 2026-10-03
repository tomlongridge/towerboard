"""Hard real-time process (design §1.4): ``python -m tower rt``.

pulse source → clock discipline → strike scheduler → audio engine → ALSA

Strike events go to the app over a non-blocking datagram socket; nothing in
the app can stall this process. Status goes the same way every two seconds,
which is what the app's health check and diagnostics read.

Off the Pi there is no ALSA: audio reports itself unavailable and the
process carries on emitting events, so the wall display can be developed on
a Mac (``--source synthetic``). ``--render out.wav`` instead renders a
synthetic touch offline, deterministically, to listen to anywhere.
"""

from __future__ import annotations

import argparse
import gc
import logging
import signal
import sys
import threading
from pathlib import Path
from typing import Iterable, Sequence

from tower import config, ipc, version
from tower.clock import Clock, FakeClock, SystemClock
from tower.events import Sequencer, strike_payload
from tower.rt import soundpack
from tower.rt.audio import AlsaOutput, AudioEngine, AudioOutput, AudioUnavailable, WavOutput
from tower.rt.calibration import Calibration
from tower.rt.discipline import OffsetEstimator
from tower.rt.sched import StrikeScheduler
from tower.rt.serial_source import SerialSource, SourceStats
from tower.rt.source import PulseEvent, SyntheticParams, SyntheticSource

log = logging.getLogger("tower.rt")

STATUS_INTERVAL_S = 2.0
AUDIO_RETRY_S = 10.0
TEST_STRIKE_LEAD_S = 0.05
# The synthetic "sensor" fires this long before its strike, as a real photohead
# does, so the scheduler has lead time and synthetic strikes are not all late.
SYNTHETIC_SENSOR_LEAD_S = 0.1


class RtProcess:
    def __init__(self, cfg: config.Config, clock: Clock, source: Iterable[PulseEvent] | None,
                 source_name: str, output: AudioOutput | None = None, send_events: bool = True) -> None:
        self.cfg = cfg
        self.clock = clock
        self.source = source
        self.source_name = source_name
        self.calibration = Calibration(cfg.state_dir / "calibration.json")
        self.pack_error = ""
        self.pack = self._load_pack(cfg.audio.pack)
        self.discipline = OffsetEstimator()
        self.sched = StrikeScheduler(self.offset_s, cfg.strikes.touch_gap_s)
        self.engine: AudioEngine | None = None
        self.audio_detail = "disabled in config" if not cfg.audio.enabled else "not started"
        if output is not None:
            self.engine = self._make_engine(output)
        self.events = ipc.Sender(cfg.run_dir / ipc.EVENTS) if send_events else None
        self.seq = Sequencer()
        self.stop = threading.Event()
        self._lock = threading.Lock()  # pulses and controls touch the scheduler from two threads

    # --- strikes -------------------------------------------------------------

    def offset_s(self, bell: int, stroke: str) -> float:
        b = self.pack.bells.get(bell)
        pack_ms = b.offset_ms.get(stroke, 0.0) if b else 0.0
        lead = SYNTHETIC_SENSOR_LEAD_S if self.source_name == "synthetic" else 0.0
        return (pack_ms + self.calibration.get(bell, stroke)) / 1000 + lead

    def on_pulse(self, pulse: PulseEvent) -> None:
        with self._lock:
            self.discipline.add(pulse.t_src, pulse.t_rx)
            strike = self.sched.strike(pulse.bell, self.discipline.to_local(pulse.t_src))
        if self.engine:
            self.engine.schedule(strike.bell, strike.t)
        payload = strike_payload(strike.bell, strike.stroke, self.source_name)
        payload["t_pulse"] = round(strike.t_pulse, 6)  # additive: allowed without a version bump
        self.emit("strike", strike.t, payload)

    def emit(self, type_: str, t: float, payload: dict) -> None:
        if self.events:
            self.events.send(self.seq.emit(type_, t, payload).to_dict())

    # --- control (app → RT) -----------------------------------------------------

    def handle_control(self, msg: dict) -> None:
        cmd = msg.get("cmd")
        if cmd == "reload_calibration":
            self.calibration.load()
        elif cmd == "reset_strokes":
            with self._lock:
                self.sched.reset_strokes()
        elif cmd == "volume" and isinstance(msg.get("db"), (int, float)):
            if self.engine:
                self.engine.set_volume(float(msg["db"]))
        elif cmd == "pack" and isinstance(msg.get("id"), str):
            # Decoding a real pack takes a moment: do it off the control thread's hot path,
            # and keep the old pack sounding until the new one is ready.
            threading.Thread(target=self._swap_pack, args=(msg["id"],), daemon=True).start()
        elif cmd == "test_strike" and isinstance(msg.get("bell"), int) and 1 <= msg["bell"] <= 16:
            t = self.clock.now() + TEST_STRIKE_LEAD_S
            if self.engine:
                self.engine.schedule(msg["bell"], t)
            self.emit("strike", t, strike_payload(msg["bell"], msg.get("stroke", "hand")
                                                  if msg.get("stroke") in ("hand", "back") else "hand",
                                                  "simulated"))
        else:
            log.warning("ignoring control %r", msg)

    def _swap_pack(self, pack_id: str) -> None:
        pack = self._load_pack(pack_id)
        if self.engine:
            self.engine.set_pack(pack)
        self.pack = pack

    def _load_pack(self, pack_id: str) -> soundpack.SoundPack:
        try:
            pack = soundpack.load(pack_id, self.cfg.state_dir / "soundpacks", self.cfg.audio.rate)
            self.pack_error = ""
        except (soundpack.PackError, OSError) as e:
            log.error("sound pack %r: %s; using synthetic bells", pack_id, e)
            self.pack_error = f"{pack_id}: {e}"
            pack = soundpack.synthetic(16, self.cfg.audio.rate)
        return pack

    # --- status ---------------------------------------------------------------

    def status(self) -> dict:
        stats = getattr(self.source, "stats", None)
        source = stats.as_dict() if isinstance(stats, SourceStats) else {"status": "open"}
        audio = self.engine.stats.as_dict() if self.engine else {"status": "unavailable"}
        audio["detail"] = audio.get("detail") or self.audio_detail
        offset = self.discipline.offset
        return {
            "version": version.full_version(),
            "source": {"kind": self.source_name, **source},
            "audio": audio,
            "pack": {"id": self.pack.id, "name": self.pack.name, "bells": len(self.pack.bells),
                     "error": self.pack_error},
            "clock_offset_ms": None if offset is None else round(offset * 1000, 3),
            "clock_reseeds": self.discipline.reseeds,
            "events": {"sent": self.events.sent, "dropped": self.events.dropped} if self.events else None,
        }

    # --- threads ---------------------------------------------------------------

    def _make_engine(self, output: AudioOutput) -> AudioEngine:
        a = self.cfg.audio
        return AudioEngine(output, self.pack, self.clock, voices=a.voices, volume_db=a.volume_db)

    def _audio_loop(self) -> None:
        """Open the device, play until stopped; if it fails, say why and retry (USB speakers)."""
        a = self.cfg.audio
        while not self.stop.is_set():
            if self.engine is None:
                try:
                    out = AlsaOutput(a.device, a.rate, a.channels, a.period_frames, a.periods)
                except AudioUnavailable as e:
                    self.audio_detail = str(e)
                    self.stop.wait(AUDIO_RETRY_S)
                    continue
                self.engine = self._make_engine(out)
                self.audio_detail = ""
                log.info("audio on %s: %d Hz, period %d frames, buffer %d frames",
                         a.device, out.rate, out.period_frames, out.buffer_frames)
            self.engine.stop = self.stop
            try:
                self.engine.run()
            except Exception as e:  # noqa: BLE001 — the device went away mid-ring
                log.exception("audio failed")
                self.audio_detail = f"failed: {e}; reopening"
                self.engine = None
                self.stop.wait(1.0)

    def _source_loop(self) -> None:
        if self.source is None:
            return
        for pulse in self.source:
            if self.stop.is_set():
                break
            self.on_pulse(pulse)

    def _control_loop(self) -> None:
        rx = ipc.Receiver(self.cfg.run_dir / ipc.CONTROL)
        try:
            while not self.stop.is_set():
                msg = rx.recv(timeout=0.5)
                if isinstance(msg, dict):
                    self.handle_control(msg)
        finally:
            rx.close()

    def run(self) -> None:
        threads = [threading.Thread(target=self._control_loop, name="control", daemon=True),
                   threading.Thread(target=self._source_loop, name="source", daemon=True)]
        if self.cfg.audio.enabled:
            threads.append(threading.Thread(target=self._audio_loop, name="audio", daemon=True))
        for t in threads:
            t.start()
        gc.collect()
        gc.freeze()  # everything loaded so far is long-lived: keep it out of GC scans
        while not self.stop.wait(STATUS_INTERVAL_S):
            self.emit("system", self.clock.now(), {"rt": self.status()})
        stop_source = getattr(self.source, "stop", None)
        if isinstance(stop_source, threading.Event):
            stop_source.set()
        if self.events:
            self.events.close()


def build_source(cfg: config.Config, kind: str, clock: Clock) -> tuple[Iterable[PulseEvent], str]:
    if kind == "serial":
        s = cfg.serial
        return SerialSource(usb_ids=list(s.usb_ids), charmap=s.charmap, clock=clock,
                            port=s.port, baud=s.baud), "live"
    syn = cfg.synthetic
    return SyntheticSource(SyntheticParams(
        bells=syn.bells, gap=syn.gap_ms / 1000, uplift=syn.uplift_ms / 1000,
        error_sd=syn.error_ms / 1000, latency=syn.latency_ms / 1000, jitter=syn.jitter_ms / 1000,
        rows=syn.rows or None, seed=syn.seed), clock), "synthetic"


def render_offline(cfg: config.Config, seconds: float, out_path: Path) -> AudioEngine:
    """Render a synthetic touch to a WAV file, deterministically, at faster than real time."""
    src_clock = FakeClock()
    pulses = []
    source, _ = build_source(cfg, "synthetic", src_clock)
    for p in source:
        if p.t_rx > seconds:
            break
        pulses.append(p)
    clock = FakeClock()
    a = cfg.audio
    out = WavOutput(out_path, clock, a.rate, a.channels, a.period_frames, a.periods)
    rt = RtProcess(cfg, clock, None, "synthetic", out, send_events=False)
    assert rt.engine is not None
    i = 0
    while clock.now() < seconds + 3:
        # Deliver each pulse when it would have arrived, a period ahead of rendering.
        while i < len(pulses) and pulses[i].t_rx <= clock.now():
            rt.on_pulse(pulses[i])
            i += 1
        rt.engine.render_period()
    out.close()
    return rt.engine


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m tower rt")
    p.add_argument("--config", type=Path)
    p.add_argument("--overrides", type=Path)
    p.add_argument("--dev", action="store_true", help="state and sockets under ./.dev")
    p.add_argument("--source", choices=config.SOURCE_KINDS)
    p.add_argument("--render", type=Path, metavar="WAV",
                   help="render a synthetic touch offline to this file and exit")
    p.add_argument("--seconds", type=float, default=30.0, help="length for --render")
    args = p.parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")

    cli: dict[str, dict] = {}
    tower_path, overrides_path = args.config, args.overrides
    if args.dev:
        dev = Path(".dev").resolve()
        tower_path = tower_path or dev / "tower.toml"
        overrides_path = overrides_path or dev / "state" / "overrides.json"
        cli["paths"] = {"state_dir": str(dev / "state"), "opt_dir": str(dev / "opt")}
        cli["ipc"] = {"run_dir": str(dev / "run")}
    if args.source:
        cli["source"] = {"kind": args.source}
    try:
        cfg = config.load(tower_path=tower_path, overrides_path=overrides_path, cli=cli)
    except config.ConfigError as e:
        log.error("%s", e)
        return 2

    if args.render:
        engine = render_offline(cfg, args.seconds, args.render)
        log.info("rendered %.0f s to %s: %s", args.seconds, args.render, engine.stats.as_dict())
        return 0

    clock = SystemClock()
    source, name = build_source(cfg, cfg.source.kind, clock)
    rt = RtProcess(cfg, clock, source, name)
    signal.signal(signal.SIGTERM, lambda *_: rt.stop.set())
    signal.signal(signal.SIGINT, lambda *_: rt.stop.set())
    log.info("tower rt %s: source=%s, pack=%s", version.full_version(), cfg.source.kind, rt.pack.id)
    rt.run()
    return 0
