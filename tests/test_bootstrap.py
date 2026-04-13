from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from music_catalog_bootstrap.services import BootstrapService, TargetPlanService
from music_catalog_bootstrap.target_profiles import TargetProfileLoader


class BootstrapServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = BootstrapService()
        self.plan_service = TargetPlanService()

    def test_bootstrap_runs_in_dry_run_mode_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            report = self.service.bootstrap(
                ROOT / "fixtures" / "sample_releases.csv",
                ROOT / "fixtures" / "sample-target.properties",
                data_dir,
            )

            self.assertEqual("dry-run", report.mode)
            self.assertIsNone(report.sql_file)
            self.assertIsNone(report.apply_report)
            self.assertTrue(report.review_queue_file.exists())
            self.assertTrue(report.review_summary_file.exists())
            self.assertEqual(2, report.review_queue_count)
            self.assertFalse(report.catalog_updated)
            self.assertEqual(3, report.import_report.auto_create_count)
            self.assertEqual(1, report.import_report.review_count)
            self.assertIn(str(data_dir / "previews"), str(report.run_dir))
            self.assertFalse((data_dir / "canonical").exists())
            self.assertFalse((data_dir / "canonical" / "artists.csv").exists())
            self.assertFalse((data_dir / "canonical" / "releases.csv").exists())
            summary_text = report.review_summary_file.read_text(encoding="utf-8")
            self.assertIn("Rows requiring review: 2", summary_text)
            self.assertIn("REVIEW:SAME_ARTIST_TITLE_DIFFERENT_DATE: 1", summary_text)
            self.assertIn("FAILURE:MISSING_REQUIRED_FIELD: 1", summary_text)
            console_text = report.to_console_text()
            self.assertIn("Bootstrap summary", console_text)
            self.assertIn("Review summary:", console_text)
            self.assertIn("Canonical catalog updated: no", console_text)
            self.assertIn("Dry-run did not change the canonical catalog.", console_text)
            self.assertIn("Run again with --export-sql or --apply when ready.", console_text)

    def test_bootstrap_can_export_sql_in_one_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            sql_file = Path(temp_dir) / "out" / "catalog.sql"
            report = self.service.bootstrap(
                ROOT / "fixtures" / "sample_releases.csv",
                ROOT / "fixtures" / "sample-target.properties",
                data_dir,
                sql_output_file=sql_file,
            )

            self.assertEqual("export-sql", report.mode)
            self.assertEqual(sql_file, report.sql_file)
            self.assertTrue(sql_file.exists())
            self.assertTrue(report.catalog_updated)
            self.assertTrue((data_dir / "canonical" / "artists.csv").exists())
            self.assertIn("INSERT IGNORE INTO `service_artists`", sql_file.read_text(encoding="utf-8"))
            self.assertIn("Canonical catalog updated: yes", report.to_console_text())
            self.assertIn("The generated SQL file can be inspected or applied manually.", report.to_console_text())

    def test_bootstrap_can_apply_with_profile_connection_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            sql_file = Path(temp_dir) / "out" / "catalog.sql"
            profile_path = Path(temp_dir) / "apply-target.properties"
            profile_path.write_text(
                "\n".join(
                    [
                        "target.engine=mysql",
                        "target.write_mode=insert-ignore",
                        "target.apply.mode=command",
                        "target.apply.command=mysql",
                        "target.apply.host=localhost",
                        "target.apply.port=3306",
                        "target.apply.database=music_app",
                        "target.apply.user=bootstrap",
                        "",
                        "artist.table=service_artists",
                        "artist.id.column=id",
                        "artist.lookup.column=name_key",
                        "artist.name.column=name",
                        "artist.name_key.column=name_key",
                        "",
                        "release.table=service_releases",
                        "release.artist_id.column=artist_id",
                        "release.title.column=title",
                        "release.title_key.column=title_key",
                        "release.date.column=released_on",
                        "release.upc.column=upc",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            with patch("music_catalog_bootstrap.services.subprocess.run") as run_mock:
                run_mock.return_value = subprocess.CompletedProcess(
                    args=["mysql"],
                    returncode=0,
                    stdout="",
                    stderr="",
                )

                report = self.service.bootstrap(
                    ROOT / "fixtures" / "sample_releases.csv",
                    profile_path,
                    data_dir,
                    sql_output_file=sql_file,
                    apply_changes=True,
                )

            self.assertEqual("apply", report.mode)
            self.assertIsNotNone(report.apply_report)
            self.assertEqual(sql_file, report.sql_file)
            self.assertTrue(report.catalog_updated)
            self.assertIn("Changes have been applied.", report.to_console_text())
            self.assertIn("Canonical catalog updated: yes", report.to_console_text())
            run_mock.assert_called_once()
            command = run_mock.call_args.args[0]
            self.assertEqual(
                [
                    "mysql",
                    "--host",
                    "localhost",
                    "--port",
                    "3306",
                    "--user",
                    "bootstrap",
                    "--default-character-set=utf8mb4",
                    "music_app",
                ],
                command,
            )
            self.assertIn("INSERT IGNORE INTO `service_artists`", run_mock.call_args.kwargs["input"])

    def test_bootstrap_can_apply_with_driver_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            sql_file = Path(temp_dir) / "out" / "catalog.sql"
            profile_path = Path(temp_dir) / "apply-target.properties"
            profile_path.write_text(
                "\n".join(
                    [
                        "target.engine=postgresql",
                        "target.write_mode=insert-ignore",
                        "target.apply.mode=driver",
                        "target.apply.host=localhost",
                        "target.apply.port=5432",
                        "target.apply.database=music_app",
                        "target.apply.user=bootstrap",
                        "target.apply.password_env=MCB_PG_PASSWORD",
                        "",
                        "artist.table=service_artists",
                        "artist.id.column=id",
                        "artist.lookup.column=name_key",
                        "artist.name.column=name",
                        "artist.name_key.column=name_key",
                        "",
                        "release.table=service_releases",
                        "release.artist_id.column=artist_id",
                        "release.title.column=title",
                        "release.title_key.column=title_key",
                        "release.date.column=released_on",
                        "release.upc.column=upc",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"MCB_PG_PASSWORD": "bootstrap"}, clear=False):
                with patch.object(
                    self.service.apply_service,
                    "_apply_with_driver",
                    return_value="python-driver:postgresql",
                ) as driver_mock:
                    report = self.service.bootstrap(
                        ROOT / "fixtures" / "sample_releases.csv",
                        profile_path,
                        data_dir,
                        sql_output_file=sql_file,
                        apply_changes=True,
                    )

            self.assertEqual("apply", report.mode)
            self.assertIsNotNone(report.apply_report)
            self.assertEqual("python-driver:postgresql", report.apply_report.command)
            self.assertIn("Changes have been applied.", report.to_console_text())
            driver_mock.assert_called_once()

    def test_failed_apply_does_not_persist_canonical_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            sql_file = Path(temp_dir) / "out" / "catalog.sql"

            with patch.object(
                self.service.apply_service,
                "apply",
                side_effect=ValueError("PostgreSQL apply failed: boom"),
            ):
                with self.assertRaisesRegex(ValueError, "PostgreSQL apply failed: boom"):
                    self.service.bootstrap(
                        ROOT / "fixtures" / "sample_releases.csv",
                        ROOT / "fixtures" / "sample-target-postgres-apply.properties",
                        data_dir,
                        sql_output_file=sql_file,
                        apply_changes=True,
                    )

            self.assertFalse((data_dir / "canonical").exists())
            self.assertTrue(sql_file.exists())

    def test_failed_export_does_not_persist_canonical_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            sql_file = Path(temp_dir) / "out" / "catalog.sql"

            with patch.object(
                self.service.export_service,
                "export_for_catalog",
                side_effect=ValueError("export failed"),
            ):
                with self.assertRaisesRegex(ValueError, "export failed"):
                    self.service.bootstrap(
                        ROOT / "fixtures" / "sample_releases.csv",
                        ROOT / "fixtures" / "sample-target.properties",
                        data_dir,
                        sql_output_file=sql_file,
                    )

            self.assertFalse((data_dir / "canonical").exists())

    def test_failed_apply_is_not_counted_as_latest_committed_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / ".catalog-data"
            initial_report = self.service.import_service.import_snapshot(
                ROOT / "fixtures" / "sample_releases.csv",
                data_dir,
            )

            with patch.object(
                self.service.apply_service,
                "apply",
                side_effect=ValueError("PostgreSQL apply failed: boom"),
            ):
                with self.assertRaisesRegex(ValueError, "PostgreSQL apply failed: boom"):
                    self.service.bootstrap(
                        ROOT / "fixtures" / "sample_releases.csv",
                        ROOT / "fixtures" / "sample-target-postgres-apply.properties",
                        data_dir,
                        sql_output_file=Path(temp_dir) / "out" / "catalog.sql",
                        apply_changes=True,
                    )

            plan_report = self.plan_service.plan(ROOT / "fixtures" / "sample-target.properties", data_dir)
            self.assertEqual(initial_report.run_id, plan_report.latest_run_id)

    def test_driver_apply_requires_password_environment_variable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "apply-target.properties"
            profile_path.write_text(
                "\n".join(
                    [
                        "target.engine=postgresql",
                        "target.write_mode=insert-ignore",
                        "target.apply.mode=driver",
                        "target.apply.host=localhost",
                        "target.apply.port=5432",
                        "target.apply.database=music_app",
                        "target.apply.user=bootstrap",
                        "target.apply.password_env=MCB_PG_PASSWORD",
                        "",
                        "artist.table=service_artists",
                        "artist.id.column=id",
                        "artist.lookup.column=name_key",
                        "artist.name.column=name",
                        "artist.name_key.column=name_key",
                        "",
                        "release.table=service_releases",
                        "release.artist_id.column=artist_id",
                        "release.title.column=title",
                        "release.title_key.column=title_key",
                        "release.date.column=released_on",
                        "release.upc.column=upc",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            sql_file = Path(temp_dir) / "apply.sql"
            sql_file.write_text("SELECT 1;\n", encoding="utf-8")

            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(ValueError, "Environment variable not set for MCB_PG_PASSWORD"):
                    self.service.apply_service.apply(profile_path, sql_file)

    def test_command_apply_failure_surfaces_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "apply-target.properties"
            profile_path.write_text(
                "\n".join(
                    [
                        "target.engine=mysql",
                        "target.write_mode=insert-ignore",
                        "target.apply.mode=command",
                        "target.apply.command=mysql",
                        "target.apply.host=localhost",
                        "target.apply.port=3306",
                        "target.apply.database=music_app",
                        "target.apply.user=bootstrap",
                        "",
                        "artist.table=service_artists",
                        "artist.id.column=id",
                        "artist.lookup.column=name_key",
                        "artist.name.column=name",
                        "artist.name_key.column=name_key",
                        "",
                        "release.table=service_releases",
                        "release.artist_id.column=artist_id",
                        "release.title.column=title",
                        "release.title_key.column=title_key",
                        "release.date.column=released_on",
                        "release.upc.column=upc",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            sql_file = Path(temp_dir) / "apply.sql"
            sql_file.write_text("SELECT 1;\n", encoding="utf-8")

            with patch("music_catalog_bootstrap.services.subprocess.run") as run_mock:
                run_mock.return_value = subprocess.CompletedProcess(
                    args=["mysql"],
                    returncode=1,
                    stdout="",
                    stderr="connection refused",
                )

                with self.assertRaisesRegex(ValueError, "Apply command failed: connection refused"):
                    self.service.apply_service.apply(profile_path, sql_file)


class TargetProfileValidationTest(unittest.TestCase):
    def test_invalid_apply_mode_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "invalid.properties"
            profile_path.write_text(
                "\n".join(
                    [
                        "target.engine=mysql",
                        "target.write_mode=insert-ignore",
                        "target.apply.mode=socket",
                        "",
                        "artist.table=service_artists",
                        "artist.id.column=id",
                        "artist.lookup.column=name_key",
                        "artist.name.column=name",
                        "artist.name_key.column=name_key",
                        "",
                        "release.table=service_releases",
                        "release.artist_id.column=artist_id",
                        "release.title.column=title",
                        "release.title_key.column=title_key",
                        "release.date.column=released_on",
                        "release.upc.column=upc",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "target.apply.mode must be either driver or command"):
                TargetProfileLoader().load(profile_path)
