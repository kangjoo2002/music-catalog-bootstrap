from __future__ import annotations

import lzma
import tarfile
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from music_catalog_bootstrap.services import CatalogImportService


class MusicBrainzImportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CatalogImportService()

    def test_import_musicbrainz_jsonl_creates_canonical_files_and_report(self) -> None:
        fixture = ROOT / "fixtures" / "musicbrainz_release_subset.jsonl"

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            report = self.service.import_musicbrainz(fixture, data_dir)

            self.assertEqual(5, report.total_rows)
            self.assertEqual(3, report.auto_create_count)
            self.assertEqual(0, report.auto_match_count)
            self.assertEqual(1, report.review_count)
            self.assertEqual(1, report.failure_count)
            self.assertTrue((data_dir / "canonical" / "artists.csv").exists())
            self.assertTrue((data_dir / "canonical" / "releases.csv").exists())

    def test_import_musicbrainz_tar_xz_creates_canonical_files_and_report(self) -> None:
        fixture = ROOT / "fixtures" / "musicbrainz_release_subset.jsonl"

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            archive = Path(temp_dir) / "release.tar.xz"
            self._create_tar_xz_archive(fixture, archive, "release")

            report = self.service.import_musicbrainz(archive, data_dir)

            self.assertEqual(5, report.total_rows)
            self.assertEqual(3, report.auto_create_count)
            self.assertEqual(0, report.auto_match_count)
            self.assertEqual(1, report.review_count)
            self.assertEqual(1, report.failure_count)
            self.assertTrue((data_dir / "canonical" / "artists.csv").exists())
            self.assertTrue((data_dir / "canonical" / "releases.csv").exists())

    def _create_tar_xz_archive(self, source_file: Path, archive_path: Path, entry_name: str) -> None:
        with lzma.open(archive_path, "wb") as xz_stream:
            with tarfile.open(fileobj=xz_stream, mode="w") as archive:
                archive.add(source_file, arcname=entry_name)
