"""End-to-end: `python -m tower --source=synthetic` as a subprocess."""

import hashlib
import os
import subprocess
import sys
import unittest
from pathlib import Path

from tower.events import from_json

ROOT = Path(__file__).resolve().parent.parent

# Output of `--fast --rows 10 --seed 1` must be byte-identical on every platform
# (Mac, desk Pi, CI). If an intentional change alters it, update this digest.
GOLDEN_SHA256 = "bd94df416482ffa8e0fe771466b4f6ecf3ac8cfa5a090dc7efb0aaad9d54d5fe"


def run_tower(*args):
    env = {**os.environ, "TOWER_CONFIG": "/nonexistent/tower.toml",
           "TOWER_OVERRIDES": "/nonexistent/overrides.json"}
    return subprocess.run([sys.executable, "-m", "tower", *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=60)


class MainTest(unittest.TestCase):
    def test_synthetic_emits_valid_strike_envelopes(self):
        r = run_tower("--source=synthetic", "--fast", "--rows", "4", "--bells", "6")
        self.assertEqual(r.returncode, 0, r.stderr)
        envs = [from_json(line) for line in r.stdout.splitlines()]
        self.assertEqual(len(envs), 24)
        self.assertTrue(all(e.type == "strike" for e in envs))
        self.assertEqual([e.seq for e in envs], list(range(1, 25)))
        strokes = [e.payload["stroke"] for e in envs]
        self.assertEqual(strokes, ["hand"] * 6 + ["back"] * 6 + ["hand"] * 6 + ["back"] * 6)

    def test_golden_output(self):
        r = run_tower("--source=synthetic", "--fast", "--rows", "10", "--seed", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(hashlib.sha256(r.stdout.encode()).hexdigest(), GOLDEN_SHA256)

    def test_bad_config_exits_2(self):
        r = run_tower("--source=synthetic", "--bells", "40")
        self.assertEqual(r.returncode, 2)
        self.assertIn("bells", r.stderr)

    def test_version(self):
        r = run_tower("--version")
        self.assertEqual(r.returncode, 0)
        self.assertIn("events v1", r.stdout)


class ServeTest(unittest.TestCase):
    """`python -m tower serve` as a real process: starts, migrates, answers, stops on SIGTERM."""

    def test_serve_starts_and_stops(self):
        import json
        import signal
        import socket
        import tempfile
        import time
        import urllib.request

        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        tmp = Path(tempfile.mkdtemp(dir="/tmp"))
        toml = tmp / "tower.toml"
        toml.write_text(f'[paths]\nstate_dir = "{tmp / "state"}"\nopt_dir = "{tmp / "opt"}"\n'
                        f'[web]\nhost = "127.0.0.1"\nport = {port}\n'
                        f'[ipc]\nrun_dir = "{tmp / "run"}"\n[rt]\nexpected = false\n')
        env = {**os.environ, "TOWER_OVERRIDES": str(tmp / "overrides.json")}
        proc = subprocess.Popen([sys.executable, "-m", "tower", "serve", "--config", str(toml)],
                                cwd=ROOT, env=env, stderr=subprocess.PIPE, text=True)
        try:
            body = None
            for _ in range(100):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as r:
                        body = json.loads(r.read())
                    break
                except OSError:
                    time.sleep(0.1)
            self.assertIsNotNone(body, "server never answered")
            self.assertEqual(body["status"], "ok")
            self.assertTrue((tmp / "state" / "migrations.json").is_file())
        finally:
            proc.send_signal(signal.SIGTERM)
            _, err = proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 0, err)
