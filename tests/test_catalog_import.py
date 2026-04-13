from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from music_catalog_bootstrap.services import CatalogImportService


class CatalogImportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CatalogImportService()

    def test_import_creates_canonical_files_and_report(self) -> None:
        fixture = ROOT / "fixtures" / "sample_releases.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            report = self.service.import_snapshot(fixture, data_dir)

            self.assertEqual(5, report.total_rows)
            self.assertEqual(3, report.auto_create_count)
            self.assertEqual(0, report.auto_match_count)
            self.assertEqual(1, report.review_count)
            self.assertEqual(1, report.failure_count)
            self.assertTrue((data_dir / "canonical" / "artists.csv").exists())
            self.assertTrue((data_dir / "canonical" / "releases.csv").exists())
            self.assertTrue((data_dir / "runs" / report.run_id / "review_queue.csv").exists())

    def test_same_snapshot_can_be_imported_twice_without_creating_duplicates(self) -> None:
        fixture = ROOT / "fixtures" / "sample_releases.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            self.service.import_snapshot(fixture, data_dir)
            second_report = self.service.import_snapshot(fixture, data_dir)

            self.assertEqual(0, second_report.auto_create_count)
            self.assertEqual(3, second_report.auto_match_count)
            self.assertEqual(1, second_report.review_count)
            self.assertEqual(1, second_report.failure_count)
            review_queue = (data_dir / "runs" / second_report.run_id / "review_queue.csv").read_text(encoding="utf-8")
            self.assertIn("SAME_ARTIST_TITLE_DIFFERENT_DATE", review_queue)
            self.assertIn("MISSING_REQUIRED_FIELD", review_queue)
            self.assertIn("candidate_release_id", review_queue)
            self.assertIn(",2,Radiohead,OK Computer,1997-05-21", review_queue)
