from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from music_catalog_bootstrap.target_profiles import TargetProfileLoader


class TargetProfileLoaderTest(unittest.TestCase):
    def test_sample_apply_profiles_load(self) -> None:
        loader = TargetProfileLoader()

        postgres = loader.load(ROOT / "fixtures" / "sample-target-postgres-apply.properties")
        mysql = loader.load(ROOT / "fixtures" / "sample-target-mysql-apply.properties")

        self.assertEqual("postgresql", postgres.engine)
        self.assertEqual("driver", postgres.apply_mode)
        self.assertEqual(55432, postgres.apply_port)
        self.assertEqual("MCB_PG_PASSWORD", postgres.apply_password_env)

        self.assertEqual("mysql", mysql.engine)
        self.assertEqual("driver", mysql.apply_mode)
        self.assertEqual(53306, mysql.apply_port)
        self.assertEqual("MCB_MYSQL_PASSWORD", mysql.apply_password_env)

    def test_apply_profile_requires_host_database_and_user(self) -> None:
        loader = TargetProfileLoader()

        with self.assertRaisesRegex(ValueError, "Missing required apply setting: target.apply.host"):
            loader.load(ROOT / "fixtures" / "invalid-apply-missing-host.properties")

    def test_apply_port_must_be_positive(self) -> None:
        loader = TargetProfileLoader()

        with self.assertRaisesRegex(ValueError, "target.apply.port must be a positive integer"):
            loader.load(ROOT / "fixtures" / "invalid-apply-port.properties")
