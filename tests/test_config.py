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
        self.assertEqual(cfg.source.kind, "synthetic")

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
        with self.assertRaises(config.ConfigError):
            self.load()

    def test_unsupported_source_kind(self):
        self.tower.write_text('[source]\nkind = "serial"\n')
        with self.assertRaisesRegex(config.ConfigError, "source.kind"):
            self.load()

    def test_env_vars_locate_files(self):
        self.tower.write_text('[tower]\nname = "From env"\n')
        with mock.patch.dict(os.environ, {"TOWER_CONFIG": str(self.tower),
                                          "TOWER_OVERRIDES": str(self.overrides)}):
            self.assertEqual(config.load().tower.name, "From env")
