"""Update pipeline: real signatures, real unpacking, real migrations; restart and health injected."""

import hashlib
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from tests import helpers
from tower.release import ReleaseError, ReleaseManager, bundle


def healthy(version):
    return True, f"healthy on {version}"


class Restarts:
    def __init__(self):
        self.count = 0

    def __call__(self):
        self.count += 1


class BundleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_bundle_has_exactly_payload_and_signature(self):
        b = helpers.build_bundle(self.tmp, "1.0.0")
        self.assertEqual(b.name, "tower-1.0.0.tower")
        with tarfile.open(b) as tar:
            self.assertEqual(sorted(tar.getnames()), [bundle.PAYLOAD, bundle.SIGNATURE])

    def test_manifest_covers_code_vendor_and_deploy(self):
        b = helpers.build_bundle(self.tmp, "1.0.0")
        work = self.tmp / "w"
        work.mkdir()
        manifest = bundle.read_manifest(bundle.open_bundle(b, work, helpers.allowed_signers()))
        files = manifest["files"]
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertIn("tower/__main__.py", files)
        self.assertIn("tower/web/static/index.html", files)
        self.assertIn("vendor/segno/__init__.py", files)
        self.assertIn("deploy/systemd/tower.service", files)
        self.assertIn("deploy/systemd/tower-kiosk.service", files)
        self.assertIn("deploy/pam/tower-kiosk", files)
        self.assertFalse(any("__pycache__" in f or "/." in f for f in files))

    def test_git_version(self):
        version, sha = bundle.git_version(helpers.ROOT, "9.9.9")
        if sha is None:
            self.skipTest("not a git checkout")
        self.assertRegex(version, r"^9\.9\.9\+g[0-9a-f]{7}(\.dirty\.[0-9]{14})?$")
        self.assertRegex(version, bundle.VERSION_RE)

    def test_rejects_bad_version(self):
        with self.assertRaises(ReleaseError):
            helpers.build_bundle(self.tmp, "../../etc")


class StageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.mgr = ReleaseManager(self.tmp / "opt", self.tmp / "state")
        self.out = self.tmp / "dist"
        self.out.mkdir()

    def stage(self, b):
        return self.mgr.stage(b, helpers.allowed_signers())

    def assert_nothing_staged(self):
        self.assertEqual(self.mgr.available(), [])
        leftovers = [p.name for p in (self.tmp / "opt" / "releases").iterdir()]
        self.assertEqual(leftovers, [])

    def test_stage_unpacks_verified_release(self):
        version = self.stage(helpers.build_bundle(self.out, "1.0.0"))
        self.assertEqual(version, "1.0.0")
        root = self.tmp / "opt" / "releases" / "1.0.0"
        self.assertTrue((root / "tower" / "__init__.py").is_file())
        self.assertEqual(json.loads((root / "RELEASE.json").read_text())["version"], "1.0.0")
        self.assertIsNone(self.mgr.current())  # staging never activates

    def test_untrusted_signer_rejected(self):
        b = helpers.build_bundle(self.out, "1.0.0", key=helpers.untrusted_key())
        with self.assertRaisesRegex(ReleaseError, "signature"):
            self.stage(b)
        self.assert_nothing_staged()

    def test_tampered_payload_rejected(self):
        b = helpers.build_bundle(self.out, "1.0.0")
        data = bytearray(b.read_bytes())
        data[len(data) // 3] ^= 0xFF
        b.write_bytes(bytes(data))
        with self.assertRaises(ReleaseError):
            self.stage(b)
        self.assert_nothing_staged()

    def test_missing_signers_file_rejected(self):
        b = helpers.build_bundle(self.out, "1.0.0")
        with self.assertRaisesRegex(ReleaseError, "allowed signers"):
            self.mgr.stage(b, self.tmp / "nope")

    def test_not_a_bundle(self):
        junk = self.out / "junk.tower"
        junk.write_bytes(b"not a tar file at all")
        with self.assertRaisesRegex(ReleaseError, "not a tower bundle"):
            self.stage(junk)

    def test_path_traversal_rejected_even_when_signed(self):
        data = b"owned"
        manifest = {"schema_version": 1, "version": "6.6.6",
                    "files": {"../../evil": hashlib.sha256(data).hexdigest()}}
        b = helpers.craft_bundle(self.out, {"release/../../evil": data}, manifest)
        with self.assertRaisesRegex(ReleaseError, "unsafe path"):
            self.stage(b)
        self.assertFalse((self.tmp / "evil").exists())
        self.assert_nothing_staged()

    def test_checksum_mismatch_rejected(self):
        manifest = {"schema_version": 1, "version": "6.6.6", "files": {"a.txt": "0" * 64}}
        b = helpers.craft_bundle(self.out, {"release/a.txt": b"hello"}, manifest)
        with self.assertRaisesRegex(ReleaseError, "checksum"):
            self.stage(b)
        self.assert_nothing_staged()

    def test_file_missing_from_payload_rejected(self):
        manifest = {"schema_version": 1, "version": "6.6.6", "files": {"a.txt": "0" * 64}}
        b = helpers.craft_bundle(self.out, {}, manifest)
        with self.assertRaisesRegex(ReleaseError, "missing"):
            self.stage(b)

    def test_unlisted_file_rejected(self):
        manifest = {"schema_version": 1, "version": "6.6.6", "files": {}}
        b = helpers.craft_bundle(self.out, {"release/extra.py": b"x"}, manifest)
        with self.assertRaisesRegex(ReleaseError, "not in manifest"):
            self.stage(b)

    def test_no_manifest_rejected(self):
        b = helpers.craft_bundle(self.out, {"release/a.txt": b"x"}, None)
        with self.assertRaisesRegex(ReleaseError, "RELEASE.json"):
            self.stage(b)

    def test_restaging_replaces_non_current_copy(self):
        self.stage(helpers.build_bundle(self.out, "1.0.0"))
        self.stage(helpers.build_bundle(self.out, "1.0.0"))
        self.assertEqual(self.mgr.available(), ["1.0.0"])

    def test_cannot_restage_current(self):
        b = helpers.build_bundle(self.out, "1.0.0")
        self.stage(b)
        self.mgr.activate("1.0.0", Restarts(), healthy)
        with self.assertRaisesRegex(ReleaseError, "already the current"):
            self.stage(b)


class ActivateTest(unittest.TestCase):
    """Steps 4–7. Real migrations run from the staged release."""

    @classmethod
    def setUpClass(cls):
        cls.dist = Path(tempfile.mkdtemp())
        for v in ("1.0.0", "1.1.0", "1.2.0", "2.0.0"):
            helpers.build_bundle(cls.dist, v)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.mgr = ReleaseManager(self.tmp / "opt", self.tmp / "state")

    def install(self, version, health=healthy, restart=None):
        self.mgr.stage(self.dist / f"tower-{version}.tower", helpers.allowed_signers())
        return self.mgr.activate(version, restart or Restarts(), health)

    def test_first_install(self):
        r = self.install("1.0.0")
        self.assertTrue(r.ok, r.detail)
        self.assertEqual(self.mgr.current(), "1.0.0")
        self.assertIsNone(self.mgr.previous())
        self.assertEqual(os.readlink(self.tmp / "opt" / "current"), "releases/1.0.0")

    def test_migrations_ran_from_new_release(self):
        self.install("1.0.0")
        state = self.tmp / "state"
        self.assertIn("0001_state_layout", json.loads((state / "migrations.json").read_text())["applied"])
        self.assertTrue((state / "sessions").is_dir())

    def test_upgrade_sets_previous_and_restarts(self):
        self.install("1.0.0")
        restarts = Restarts()
        r = self.install("1.1.0", restart=restarts)
        self.assertTrue(r.ok)
        self.assertEqual((self.mgr.current(), self.mgr.previous()), ("1.1.0", "1.0.0"))
        self.assertEqual(restarts.count, 1)
        self.assertEqual(self.mgr.last_result()["result"], "ok")

    def test_failed_health_check_rolls_back_unattended(self):
        self.install("1.0.0")
        self.install("1.1.0")
        checked = []

        def health(version):
            checked.append(version)
            return (version != "2.0.0", "boom" if version == "2.0.0" else "fine")

        restarts = Restarts()
        r = self.install("2.0.0", health=health, restart=restarts)
        self.assertFalse(r.ok)
        self.assertIn("rolled back to 1.1.0", r.detail)
        self.assertEqual((self.mgr.current(), self.mgr.previous()), ("1.1.0", "1.0.0"))
        self.assertEqual(checked, ["2.0.0", "1.1.0"])
        self.assertEqual(restarts.count, 2)
        last = self.mgr.last_result()
        self.assertEqual((last["result"], last["version"], last["from"]), ("failed", "2.0.0", "1.1.0"))

    def test_restart_failure_is_a_failed_update(self):
        self.install("1.0.0")

        def restart():
            raise RuntimeError("unit failed")

        r = self.mgr.activate("1.0.0", restart, healthy)  # reactivating is allowed via activate
        self.assertFalse(r.ok)

    def test_first_install_failure_has_nothing_to_roll_back_to(self):
        r = self.install("1.0.0", health=lambda v: (False, "dead"))
        self.assertFalse(r.ok)
        self.assertIn("no previous release", r.detail)

    def test_activate_unstaged(self):
        r = self.mgr.activate("9.9.9", Restarts(), healthy)
        self.assertFalse(r.ok)
        self.assertEqual(r.detail, "not staged")

    def test_manual_rollback_swaps(self):
        self.install("1.0.0")
        self.install("1.1.0")
        r = self.mgr.rollback(Restarts(), healthy)
        self.assertTrue(r.ok)
        self.assertEqual((self.mgr.current(), self.mgr.previous()), ("1.0.0", "1.1.0"))

    def test_rollback_to_broken_previous_stays_put(self):
        self.install("1.0.0")
        self.install("1.1.0")
        r = self.mgr.rollback(Restarts(), lambda v: (v == "1.1.0", "x"))
        self.assertFalse(r.ok)
        self.assertEqual((self.mgr.current(), self.mgr.previous()), ("1.1.0", "1.0.0"))

    def test_rollback_without_previous(self):
        self.install("1.0.0")
        self.assertFalse(self.mgr.rollback(Restarts(), healthy).ok)

    def test_prune_keeps_current_previous_and_one_more(self):
        for v in ("1.0.0", "1.1.0", "1.2.0", "2.0.0"):
            self.install(v)
        self.assertEqual(self.mgr.available(), ["1.1.0", "1.2.0", "2.0.0"])
        self.assertEqual((self.mgr.current(), self.mgr.previous()), ("2.0.0", "1.2.0"))

    def test_status(self):
        self.install("1.0.0")
        s = self.mgr.status()
        self.assertEqual(s["current"], "1.0.0")
        self.assertEqual(s["last_result"]["action"], "activate")

    def test_activated_release_runs(self):
        """The unpacked tree is a working app with its vendored dependency."""
        import subprocess
        import sys

        self.install("1.0.0")
        current = self.tmp / "opt" / "current"
        env = {**os.environ, "PYTHONPATH": f"{current}{os.pathsep}{current / 'vendor'}"}
        r = subprocess.run(
            [sys.executable, "-c", "import tower.version as v, segno, tower.web.qr; print(v.full_version())"],
            cwd=self.tmp, env=env, capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "1.0.0")


class CliTest(unittest.TestCase):
    """`python -m tower.release` as the Pi runs it: build, stage, first-install activate, status."""

    def run_cli(self, *args, cfg=None):
        import subprocess
        import sys

        cmd = [sys.executable, "-m", "tower.release"] + (["--config", str(cfg)] if cfg else []) + list(args)
        env = {**os.environ, "TOWER_OVERRIDES": "/nonexistent/overrides.json"}
        return subprocess.run(cmd, cwd=helpers.ROOT, env=env, capture_output=True, text=True, timeout=120)

    def test_build_stage_activate_status(self):
        tmp = Path(tempfile.mkdtemp())
        r = self.run_cli("build", "--key", str(helpers.signing_key()), "--out", str(tmp / "dist"))
        self.assertEqual(r.returncode, 0, r.stderr)
        b = Path(r.stdout.strip())
        self.assertTrue(b.is_file())

        cfg = tmp / "tower.toml"
        cfg.write_text(f'[paths]\nstate_dir = "{tmp / "state"}"\nopt_dir = "{tmp / "opt"}"\n'
                       f'[update]\nallowed_signers = "{helpers.allowed_signers()}"\n')
        r = self.run_cli("stage", str(b), cfg=cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        version = r.stdout.strip()
        r = self.run_cli("activate", version, "--no-restart", cfg=cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        status = json.loads(self.run_cli("status", cfg=cfg).stdout)
        self.assertEqual(status["current"], version)

    def test_stage_rejection_exits_nonzero(self):
        tmp = Path(tempfile.mkdtemp())
        junk = tmp / "x.tower"
        junk.write_bytes(b"junk")
        cfg = tmp / "tower.toml"
        cfg.write_text(f'[paths]\nstate_dir = "{tmp / "s"}"\nopt_dir = "{tmp / "o"}"\n'
                       f'[update]\nallowed_signers = "{helpers.allowed_signers()}"\n')
        r = self.run_cli("stage", str(junk), cfg=cfg)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not a tower bundle", r.stderr)
