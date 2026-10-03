import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tower import fsutil


class AtomicWriteTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_writes_with_mode_despite_umask(self):
        path = self.dir / "sub" / "secret.json"
        old = os.umask(0o077)
        try:
            fsutil.atomic_write(path, '{"a": 1}', 0o644)
        finally:
            os.umask(old)
        self.assertEqual(path.read_text(), '{"a": 1}')
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)
        self.assertEqual(list(path.parent.iterdir()), [path])  # no temp file left

    def test_data_is_synced_before_the_rename(self):
        """The fix for empty files after a power cut: fsync the file, then the directory."""
        calls = []
        real_fsync, real_replace = os.fsync, os.replace
        with mock.patch.object(os, "fsync", lambda fd: (calls.append("fsync"), real_fsync(fd))[1]), \
             mock.patch.object(os, "replace", lambda a, b: (calls.append("replace"), real_replace(a, b))[1]):
            fsutil.atomic_write(self.dir / "x", b"data")
        self.assertEqual(calls, ["fsync", "replace", "fsync"])

    def test_replaces_existing(self):
        path = self.dir / "x"
        path.write_text("old")
        fsutil.atomic_write(path, "new")
        self.assertEqual(path.read_text(), "new")
