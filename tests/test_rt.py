"""The RT process: pulses in, strikes scheduled and announced, controls obeyed."""

import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from tests.test_audio import impulse_pack
from tower import config, ipc
from tower.clock import FakeClock
from tower.events import from_dict
from tower.rt import main as rt_main
from tower.rt.audio import WavOutput
from tower.rt.source import PulseEvent

ROOT = Path(__file__).resolve().parent.parent


class RtProcessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(dir="/tmp"))
        self.cfg = config.load(tower_path=self.tmp / "none", overrides_path=self.tmp / "none.json", cli={
            "paths": {"state_dir": str(self.tmp / "state"), "opt_dir": str(self.tmp / "opt")},
            "ipc": {"run_dir": str(self.tmp / "run")},
        })
        self.events = ipc.Receiver(self.tmp / "run" / ipc.EVENTS)
        self.addCleanup(self.events.close)
        self.clock = FakeClock(100.0)
        self.out = WavOutput(self.tmp / "out.wav", self.clock, 44100, 1, 256, 3)
        self.rt = rt_main.RtProcess(self.cfg, self.clock, None, "live", self.out)
        self.rt.engine.set_pack(impulse_pack(8))
        self.rt.pack = self.rt.engine.pack
        self.addCleanup(self.rt.events.close)

    def received(self):
        out = []
        while (obj := self.events.recv(timeout=0.05)) is not None:
            out.append(from_dict(obj))
        return out

    def render_until(self, t):
        while self.clock.now() < t:
            self.rt.engine.render_period()

    def test_pulse_becomes_announced_strike_at_calibrated_time(self):
        self.rt.calibration.set(2, "hand", 250)
        self.render_until(100.2)
        t_pulse = self.clock.now()
        self.rt.on_pulse(PulseEvent(bell=2, t_src=t_pulse, t_rx=t_pulse, seq=1))
        [env] = self.received()
        self.assertEqual(env.type, "strike")
        self.assertEqual(env.payload["bell"], 2)
        self.assertEqual(env.payload["stroke"], "hand")
        self.assertEqual(env.payload["source"], "live")
        self.assertAlmostEqual(env.t - env.payload["t_pulse"], 0.25, places=6)
        self.render_until(env.t + 0.1)
        self.out.close()
        with wave.open(str(self.tmp / "out.wav")) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), "<i2")
        onset = np.flatnonzero(x)[0]
        self.assertLessEqual(abs(onset - round((env.t - self.out.started) * 44100)), 1)
        self.assertEqual(self.rt.engine.stats.late, 0)

    def test_strokes_alternate_and_reset_by_control(self):
        for i in range(3):
            self.rt.on_pulse(PulseEvent(1, 100 + i, 100 + i, i))
        self.rt.handle_control({"cmd": "reset_strokes"})
        self.rt.on_pulse(PulseEvent(1, 103.5, 103.5, 4))
        self.assertEqual([e.payload["stroke"] for e in self.received()], ["hand", "back", "hand", "hand"])

    def test_calibration_reload_control(self):
        cal = self.tmp / "state" / "calibration.json"
        cal.parent.mkdir(parents=True, exist_ok=True)
        cal.write_text(json.dumps({"offsets_ms": {"4": {"hand": 40, "back": 0}}}))
        self.rt.handle_control({"cmd": "reload_calibration"})
        self.assertAlmostEqual(self.rt.offset_s(4, "hand"), 0.04)

    def test_test_strike(self):
        self.render_until(100.2)
        self.rt.handle_control({"cmd": "test_strike", "bell": 3})
        [env] = self.received()
        self.assertEqual((env.payload["bell"], env.payload["source"]), (3, "simulated"))
        self.render_until(env.t + 0.1)
        self.assertEqual(self.rt.engine.stats.strikes, 1)

    def test_bad_control_ignored(self):
        with self.assertLogs("tower.rt", "WARNING"):
            self.rt.handle_control({"cmd": "self_destruct"})
            self.rt.handle_control({"cmd": "test_strike", "bell": 99})  # out of range
        self.assertEqual(self.received(), [])

    def test_status_is_small_enough_for_a_datagram(self):
        self.rt.emit("system", self.clock.now(), {"rt": self.rt.status()})
        [env] = self.received()
        st = env.payload["rt"]
        self.assertEqual(st["source"]["kind"], "live")
        self.assertEqual(st["pack"]["id"], "imp")
        self.assertIn("late", st["audio"])

    def test_missing_pack_falls_back_to_synthetic(self):
        with self.assertLogs("tower.rt", "ERROR"):
            pack = self.rt._load_pack("not-installed")
        self.assertEqual(pack.id, "synthetic")
        self.assertIn("not installed", self.rt.pack_error)


class RenderTest(unittest.TestCase):
    def test_offline_render_cli(self):
        out = Path(tempfile.mkdtemp()) / "touch.wav"
        r = subprocess.run([sys.executable, "-m", "tower", "rt", "--render", str(out), "--seconds", "5",
                            "--config", "/nonexistent.toml", "--overrides", "/nonexistent.json"],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("'late': 0", r.stderr)
        with wave.open(str(out)) as w:
            self.assertGreater(w.getnframes() / w.getframerate(), 5)
            x = np.frombuffer(w.readframes(w.getnframes()), "<i2")
        self.assertGreater(int(np.abs(x).max()), 1000)  # it rang
