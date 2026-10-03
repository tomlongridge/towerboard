import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tower import version


class VersionTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        version.info.cache_clear()
        self.addCleanup(version.info.cache_clear)
        patcher = mock.patch.object(version, "release_root", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_source_checkout(self):
        self.assertTrue(version.full_version().endswith("+dev"))

    def test_release(self):
        (self.root / "RELEASE.json").write_text(json.dumps({"version": "0.4.0+g1a2b3c4", "git_sha": "1a2b3c4"}))
        self.assertEqual(version.full_version(), "0.4.0+g1a2b3c4")
        self.assertIsNone(version.info()["hot"])

    def test_hot_patched_release_says_so(self):
        """make hot: the release no longer matches what was signed."""
        (self.root / "RELEASE.json").write_text(json.dumps({"version": "0.4.0+g1a2b3c4"}))
        (self.root / "HOT").write_text("20261003190000\n")
        self.assertEqual(version.full_version(), "0.4.0+g1a2b3c4.hot.20261003190000")
        self.assertEqual(version.info()["hot"], "20261003190000")

    def test_hot_without_build_metadata(self):
        (self.root / "RELEASE.json").write_text(json.dumps({"version": "0.4.0"}))
        (self.root / "HOT").write_text("20261003190000")
        self.assertEqual(version.full_version(), "0.4.0+hot.20261003190000")
