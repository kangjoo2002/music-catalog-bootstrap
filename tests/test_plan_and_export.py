from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from music_catalog_bootstrap.services import CatalogImportService, SqlExportService, TargetPlanService


class TargetPlanAndSqlExportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.import_service = CatalogImportService()
        self.target_plan_service = TargetPlanService()
        self.sql_export_service = SqlExportService()

    def test_plan_reports_canonical_counts_and_latest_run_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            self.import_service.import_snapshot(ROOT / "fixtures" / "sample_releases.csv", data_dir)

            report = self.target_plan_service.plan(ROOT / "fixtures" / "sample-target.properties", data_dir)

            self.assertEqual("mysql", report.target_engine)
            self.assertEqual("insert-ignore", report.write_mode)
            self.assertEqual("service_artists", report.artist_table)
            self.assertEqual("service_releases", report.release_table)
            self.assertEqual(3, report.canonical_artist_count)
            self.assertEqual(3, report.canonical_release_count)
            self.assertTrue(report.latest_run_id.startswith("run_"))
            self.assertEqual(3, report.latest_auto_create_count)
            self.assertEqual(0, report.latest_auto_match_count)
            self.assertEqual(1, report.latest_review_count)
            self.assertEqual(1, report.latest_failure_count)

    def test_export_writes_reviewable_sql_for_canonical_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            output_file = Path(temp_dir) / "out" / "catalog.sql"
            self.import_service.import_snapshot(ROOT / "fixtures" / "sample_releases.csv", data_dir)

            report = self.sql_export_service.export(
                ROOT / "fixtures" / "sample-target.properties",
                data_dir,
                output_file,
            )

            sql = output_file.read_text(encoding="utf-8")

            self.assertTrue(output_file.exists())
            self.assertIn("INSERT IGNORE INTO `service_artists`", sql)
            self.assertIn("'Bjork'", sql)
            self.assertIn("INSERT IGNORE INTO `service_releases`", sql)
            self.assertIn("'OK Computer'", sql)
            self.assertEqual(3, report.canonical_artist_count)
            self.assertEqual(3, report.canonical_release_count)
            self.assertEqual(3, report.latest_auto_create_count)
            self.assertEqual(1, report.latest_review_count)
            self.assertEqual(1, report.latest_failure_count)

    def test_export_writes_postgresql_sql_for_canonical_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            output_file = Path(temp_dir) / "out" / "catalog-postgres.sql"
            self.import_service.import_snapshot(ROOT / "fixtures" / "sample_releases.csv", data_dir)

            report = self.sql_export_service.export(
                ROOT / "fixtures" / "sample-target-postgres.properties",
                data_dir,
                output_file,
            )

            sql = output_file.read_text(encoding="utf-8")

            self.assertTrue(output_file.exists())
            self.assertIn('INSERT INTO "service_artists"', sql)
            self.assertIn("ON CONFLICT DO NOTHING;", sql)
            self.assertIn('INSERT INTO "service_releases"', sql)
            self.assertIn('"service_artists"', sql)
            self.assertEqual("postgresql", report.target_engine)
            self.assertEqual(3, report.canonical_artist_count)
            self.assertEqual(3, report.canonical_release_count)
