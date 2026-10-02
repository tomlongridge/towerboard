import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tower import migrate


class MigrateTest(unittest.TestCase):
    def setUp(self):
        self.state = Path(tempfile.mkdtemp()) / "state"

    def test_runs_once_and_records(self):
        self.assertEqual(migrate.run(self.state), ["0001_state_layout"])
        self.assertTrue((self.state / "sessions").is_dir())
        self.assertEqual(migrate.run(self.state), [])
        self.assertEqual(json.loads((self.state / "migrations.json").read_text())["applied"],
                         ["0001_state_layout"])

    def test_every_migration_is_idempotent(self):
        for mid, fn in migrate.MIGRATIONS:
            with self.subTest(mid=mid):
                fn(self.state)
                fn(self.state)

    def test_failure_stops_and_keeps_earlier_record(self):
        def boom(state):
            raise RuntimeError("disk full")

        migrations = migrate.MIGRATIONS + [("0002_boom", boom)]
        with mock.patch.object(migrate, "MIGRATIONS", migrations), self.assertRaises(RuntimeError):
            migrate.run(self.state)
        self.assertEqual(migrate.applied(self.state), ["0001_state_layout"])

    def test_ids_unique_and_ordered(self):
        ids = [mid for mid, _ in migrate.MIGRATIONS]
        self.assertEqual(ids, sorted(set(ids)))
