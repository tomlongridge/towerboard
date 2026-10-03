import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tower import config


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.tower = Path(self.dir.name, "tower.toml")
        self.overrides = Path(self.dir.name, "overrides.json")

    def load(self, **kw):
        return config.load(tower_path=self.tower, overrides_path=self.overrides, **kw)

    def test_defaults_when_no_files(self):
        cfg = self.load()
        self.assertEqual(cfg, config.Config())
        self.assertEqual(cfg.source.kind, "serial")

    def test_layering_order(self):
        self.tower.write_text('[tower]\nname = "St Mary"\n[synthetic]\nbells = 6\nseed = 1\n')
        self.overrides.write_text(json.dumps({"synthetic": {"seed": 2, "gap_ms": 180}}))
        cfg = self.load(cli={"synthetic": {"seed": 3}})
        self.assertEqual(cfg.tower.name, "St Mary")
        self.assertEqual(cfg.synthetic.bells, 6)
        self.assertEqual(cfg.synthetic.gap_ms, 180.0)
        self.assertIsInstance(cfg.synthetic.gap_ms, float)
        self.assertEqual(cfg.synthetic.seed, 3)

    def test_unknown_keys_warn_not_fail(self):
        self.tower.write_text("[future]\nx = 1\n[synthetic]\nnew_knob = 2\n")
        with self.assertLogs("tower.config", "WARNING") as logs:
            cfg = self.load()
        self.assertEqual(cfg, config.Config())
        self.assertEqual(len(logs.records), 2)

    def test_wrong_type_rejected(self):
        for text in ('[synthetic]\nbells = "eight"\n', "[synthetic]\nbells = true\n",
                     "[synthetic]\nbells = 8.5\n", "synthetic = 3\n"):
            with self.subTest(text=text):
                self.tower.write_text(text)
                with self.assertRaises(config.ConfigError):
                    self.load()

    def test_invalid_files(self):
        self.tower.write_text("[[[")
        with self.assertRaises(config.ConfigError):
            self.load()
        self.tower.unlink()
        self.overrides.write_text("[1, 2]")
        with self.assertLogs("tower.config", "ERROR"):
            self.assertEqual(self.load(), config.Config())

    def test_unsupported_source_kind(self):
        self.tower.write_text('[source]\nkind = "carrier-pigeon"\n')
        with self.assertRaisesRegex(config.ConfigError, "source.kind"):
            self.load()

    def test_save_overrides_merges_and_validates(self):
        config.save_overrides("network", {"mode": "dual"}, self.overrides)
        config.save_overrides("network", {"uplink_ssid": "Church"}, self.overrides)
        cfg = self.load()
        self.assertEqual((cfg.network.mode, cfg.network.uplink_ssid), ("dual", "Church"))
        self.assertEqual(self.overrides.stat().st_mode & 0o777, 0o600)
        for section, values in (("network", {"mode": "mesh"}), ("network", {"ap_psk": "short"}),
                                ("nope", {"x": 1}), ("web", {"port": "eighty"})):
            with self.subTest(values=values), self.assertRaises(config.ConfigError):
                config.save_overrides(section, values, self.overrides)
        self.assertEqual(self.load().network.mode, "dual")  # rejected writes changed nothing

    def test_list_values(self):
        self.tower.write_text('[update]\nunits = ["tower.service", "tower-rt.service"]\n')
        self.assertEqual(self.load().update.units, ["tower.service", "tower-rt.service"])
        self.tower.write_text('[update]\nunits = [1]\n')
        with self.assertRaises(config.ConfigError):
            self.load()

    def test_damaged_overrides_do_not_stop_startup(self):
        """A power cut could leave overrides.json empty; the Pi must still start, in AP mode."""
        self.tower.write_text('[tower]\nname = "St Mary"\n')
        self.overrides.write_text("")
        with self.assertLogs("tower.config", "ERROR"):
            cfg = self.load()
        self.assertEqual((cfg.tower.name, cfg.network.mode), ("St Mary", "ap"))
        self.assertFalse(self.overrides.exists())
        self.assertTrue(self.overrides.with_name("overrides.json.damaged").exists())
        config.save_overrides("audio", {"volume_db": -3.0}, self.overrides)  # and saving works again
        self.assertEqual(self.load().audio.volume_db, -3.0)

    def test_env_vars_locate_files(self):
        self.tower.write_text('[tower]\nname = "From env"\n')
        with mock.patch.dict(os.environ, {"TOWER_CONFIG": str(self.tower),
                                          "TOWER_OVERRIDES": str(self.overrides)}):
            self.assertEqual(config.load().tower.name, "From env")
