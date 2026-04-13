from __future__ import annotations

import os
import subprocess
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

from .catalog_store import CanonicalCatalog, CatalogStore
from .csv_support import CsvRowWriter, read_rows
from .models import (
    CanonicalArtist,
    CanonicalRelease,
    DecisionType,
    ApplyReport,
    BootstrapReport,
    ImportDecision,
    ImportReport,
    InputReleaseRecord,
    LatestRunDecisionSummary,
    StagingReleaseRecord,
    TargetPlanReport,
)
from .musicbrainz import iter_musicbrainz_records, is_supported_musicbrainz_input_file_name, resolve_musicbrainz_input
from .normalizer import normalize_key
from .sql_support import identifier, string_literal
from .target_profiles import TargetProfileLoader


@dataclass
class _ImportCounters:
    total_rows: int = 0
    auto_create_count: int = 0
    auto_match_count: int = 0
    review_count: int = 0
    failure_count: int = 0


@dataclass(frozen=True)
class _ImportExecutionResult:
    report: ImportReport
    catalog: CanonicalCatalog
    run_dir: Path


class CatalogImportService:
    def __init__(self) -> None:
        self.catalog_store = CatalogStore()

    def import_snapshot(self, input_file: Path, data_dir: Path) -> ImportReport:
        return self.execute_snapshot(input_file, data_dir).report

    def execute_snapshot(
        self,
        input_file: Path,
        data_dir: Path,
        *,
        persist_catalog: bool = True,
        run_root_name: str = "runs",
    ) -> _ImportExecutionResult:
        if not input_file.exists():
            raise ValueError(f"Input file not found: {input_file}")

        rows = read_rows(input_file)
        inputs = [
            InputReleaseRecord.from_row(index + 2, row)
            for index, row in enumerate(rows)
        ]

        return self._import_records(
            raw_input_file=input_file,
            data_dir=data_dir,
            raw_copy_file_name=input_file.name,
            record_source=lambda: inputs,
            persist_catalog=persist_catalog,
            run_root_name=run_root_name,
        )

    def import_musicbrainz(self, input_path: Path, data_dir: Path) -> ImportReport:
        return self.execute_musicbrainz(input_path, data_dir).report

    def execute_musicbrainz(
        self,
        input_path: Path,
        data_dir: Path,
        *,
        persist_catalog: bool = True,
        run_root_name: str = "runs",
    ) -> _ImportExecutionResult:
        resolved_input = resolve_musicbrainz_input(input_path)
        return self._import_records(
            raw_input_file=resolved_input,
            data_dir=data_dir,
            raw_copy_file_name=resolved_input.name,
            record_source=lambda: iter_musicbrainz_records(resolved_input),
            persist_catalog=persist_catalog,
            run_root_name=run_root_name,
        )

    def _import_records(
        self,
        raw_input_file: Path,
        data_dir: Path,
        raw_copy_file_name: str,
        record_source: Callable[[], Iterable[InputReleaseRecord]],
        *,
        persist_catalog: bool,
        run_root_name: str,
    ) -> _ImportExecutionResult:
        data_dir.mkdir(parents=True, exist_ok=True)
        run_id = self._next_run_id(data_dir, run_root_name)
        run_dir = data_dir / run_root_name / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        shutil.copyfile(raw_input_file, run_dir / raw_copy_file_name)

        catalog = self.catalog_store.load(data_dir, create_if_missing=persist_catalog)
        counters = _ImportCounters()

        with CsvRowWriter(
            run_dir / "staging.csv",
            [
                "line_number",
                "source_id",
                "artist_name",
                "artist_key",
                "release_title",
                "release_key",
                "release_date",
                "upc",
            ],
        ) as staging_writer, CsvRowWriter(
            run_dir / "decisions.csv",
            ["source_id", "decision_type", "reason_code", "canonical_release_id"],
        ) as decision_writer, CsvRowWriter(
            run_dir / "review_queue.csv",
            [
                "line_number",
                "source_id",
                "decision_type",
                "reason_code",
                "artist_name",
                "release_title",
                "release_date",
                "upc",
                "candidate_release_id",
                "candidate_artist_name",
                "candidate_release_title",
                "candidate_release_date",
            ],
        ) as review_writer:
            for input_record in record_source():
                staging_record = self._to_staging(input_record)
                self._write_staging_row(staging_writer, staging_record)
                self._apply_staging_record(catalog, staging_record, decision_writer, review_writer, counters)

        if persist_catalog:
            self.catalog_store.save(data_dir, catalog)
            self.catalog_store.mark_run_committed(run_dir)

        report = ImportReport(
            run_id=run_id,
            total_rows=counters.total_rows,
            auto_create_count=counters.auto_create_count,
            auto_match_count=counters.auto_match_count,
            review_count=counters.review_count,
            failure_count=counters.failure_count,
        )
        (run_dir / "report.txt").write_text(report.to_console_text(), encoding="utf-8")
        return _ImportExecutionResult(report=report, catalog=catalog, run_dir=run_dir)

    def _to_staging(self, input_record: InputReleaseRecord) -> StagingReleaseRecord:
        artist_key = normalize_key(input_record.artist_name)
        title_key = normalize_key(input_record.release_title)
        release_key = f"{artist_key}|{title_key}|{input_record.release_date.strip()}"
        return StagingReleaseRecord(
            line_number=input_record.line_number,
            source_id=input_record.source_id,
            artist_name=input_record.artist_name,
            artist_key=artist_key,
            release_title=input_record.release_title,
            release_key=release_key,
            release_date=input_record.release_date,
            upc=input_record.upc,
        )

    def _apply_staging_record(
        self,
        catalog: CanonicalCatalog,
        staging: StagingReleaseRecord,
        decision_writer: CsvRowWriter,
        review_writer: CsvRowWriter,
        counters: _ImportCounters,
    ) -> None:
        counters.total_rows += 1

        if not staging.artist_key or not staging.release_title.strip():
            decision = ImportDecision(staging.source_id, DecisionType.FAILURE, "MISSING_REQUIRED_FIELD", "")
            self._write_decision(decision_writer, decision)
            self._write_review_item(review_writer, staging, decision, None)
            counters.failure_count += 1
            return

        by_upc = catalog.find_release_by_upc(staging.upc)
        if by_upc is not None:
            self._write_decision(
                decision_writer,
                ImportDecision(staging.source_id, DecisionType.AUTO_MATCH, "UPC_EXACT", str(by_upc.release_id)),
            )
            counters.auto_match_count += 1
            return

        by_exact_key = catalog.find_release_by_exact_key(staging.release_key)
        if by_exact_key is not None:
            self._write_decision(
                decision_writer,
                ImportDecision(
                    staging.source_id,
                    DecisionType.AUTO_MATCH,
                    "TITLE_ARTIST_DATE_EXACT",
                    str(by_exact_key.release_id),
                ),
            )
            counters.auto_match_count += 1
            return

        title_key = normalize_key(staging.release_title)
        by_artist_and_title = catalog.find_release_by_artist_and_title(staging.artist_key, title_key)
        if by_artist_and_title is not None:
            decision = ImportDecision(staging.source_id, DecisionType.REVIEW, "SAME_ARTIST_TITLE_DIFFERENT_DATE", "")
            self._write_decision(decision_writer, decision)
            self._write_review_item(review_writer, staging, decision, by_artist_and_title)
            counters.review_count += 1
            return

        artist = catalog.ensure_artist(staging.artist_name, staging.artist_key)
        created = catalog.create_release(
            artist=artist,
            release_title=staging.release_title,
            release_key=staging.release_key,
            release_date=staging.release_date,
            upc=staging.upc,
        )
        self._write_decision(
            decision_writer,
            ImportDecision(staging.source_id, DecisionType.AUTO_CREATE, "NEW_RELEASE", str(created.release_id)),
        )
        counters.auto_create_count += 1

    def _write_staging_row(self, writer: CsvRowWriter, record: StagingReleaseRecord) -> None:
        writer.write_row(
            [
                str(record.line_number),
                record.source_id,
                record.artist_name,
                record.artist_key,
                record.release_title,
                record.release_key,
                record.release_date,
                record.upc,
            ]
        )

    def _write_decision(self, writer: CsvRowWriter, decision: ImportDecision) -> None:
        writer.write_row(
            [
                decision.source_id,
                decision.decision_type.value,
                decision.reason_code,
                decision.canonical_release_id,
            ]
        )

    def _write_review_item(
        self,
        writer: CsvRowWriter,
        record: StagingReleaseRecord,
        decision: ImportDecision,
        candidate: CanonicalRelease | None,
    ) -> None:
        writer.write_row(
            [
                str(record.line_number),
                decision.source_id,
                decision.decision_type.value,
                decision.reason_code,
                record.artist_name,
                record.release_title,
                record.release_date,
                record.upc,
                "" if candidate is None else str(candidate.release_id),
                "" if candidate is None else candidate.artist_name,
                "" if candidate is None else candidate.release_title,
                "" if candidate is None else candidate.release_date,
            ]
        )

    def _next_run_id(self, data_dir: Path, run_root_name: str) -> str:
        runs_dir = data_dir / run_root_name
        runs_dir.mkdir(parents=True, exist_ok=True)

        base = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"run_{base}"
        suffix = 1
        while (runs_dir / run_id).exists():
            suffix += 1
            run_id = f"run_{base}_{suffix}"
        return run_id


class TargetPlanService:
    def __init__(self) -> None:
        self.catalog_store = CatalogStore()
        self.target_profile_loader = TargetProfileLoader()

    def plan(self, target_profile_path: Path, data_dir: Path) -> TargetPlanReport:
        target_profile = self.target_profile_loader.load(target_profile_path)
        catalog = self.catalog_store.load(data_dir)
        latest_run = self.catalog_store.load_latest_run_summary(data_dir) or LatestRunDecisionSummary(
            run_id="none",
            auto_create_count=0,
            auto_match_count=0,
            review_count=0,
            failure_count=0,
        )

        return self.plan_for_catalog(target_profile, catalog, latest_run)

    def plan_for_catalog(
        self,
        target_profile,
        catalog: CanonicalCatalog,
        latest_run: LatestRunDecisionSummary,
    ) -> TargetPlanReport:
        return TargetPlanReport(
            target_engine=target_profile.engine,
            write_mode=target_profile.write_mode,
            artist_table=target_profile.artist_table,
            release_table=target_profile.release_table,
            canonical_artist_count=len(catalog.artists),
            canonical_release_count=len(catalog.releases),
            latest_run_id=latest_run.run_id,
            latest_auto_create_count=latest_run.auto_create_count,
            latest_auto_match_count=latest_run.auto_match_count,
            latest_review_count=latest_run.review_count,
            latest_failure_count=latest_run.failure_count,
        )


class SqlExportService:
    def __init__(self) -> None:
        self.catalog_store = CatalogStore()
        self.target_profile_loader = TargetProfileLoader()
        self.target_plan_service = TargetPlanService()

    def export(self, target_profile_path: Path, data_dir: Path, output_file: Path) -> TargetPlanReport:
        target_profile = self.target_profile_loader.load(target_profile_path)
        catalog = self.catalog_store.load(data_dir)
        latest_run = self.catalog_store.load_latest_run_summary(data_dir) or LatestRunDecisionSummary(
            run_id="none",
            auto_create_count=0,
            auto_match_count=0,
            review_count=0,
            failure_count=0,
        )
        return self.export_for_catalog(target_profile, catalog, latest_run, output_file)

    def export_for_catalog(
        self,
        target_profile,
        catalog: CanonicalCatalog,
        latest_run: LatestRunDecisionSummary,
        output_file: Path,
    ) -> TargetPlanReport:
        lines = [
            "-- Generated by Music Catalog Bootstrap",
            f"-- Target engine: {target_profile.engine}",
            f"-- Write mode: {target_profile.write_mode}",
            "-- Required unique key on artist lookup column and release natural key is assumed.",
            "",
        ]

        for artist in catalog.artists:
            lines.append(self._build_artist_insert(target_profile, artist))

        lines.append("")

        for release in catalog.releases:
            lines.append(self._build_release_insert(target_profile, release))

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return self.target_plan_service.plan_for_catalog(target_profile, catalog, latest_run)

    def _build_artist_insert(self, profile, artist: CanonicalArtist) -> str:
        if profile.engine.lower() == "postgresql":
            return (
                f"INSERT INTO {identifier(profile.artist_table, profile.engine)} "
                f"({identifier(profile.artist_name_column, profile.engine)}, "
                f"{identifier(profile.artist_name_key_column, profile.engine)}) "
                f"VALUES ({string_literal(artist.artist_name, profile.engine)}, "
                f"{string_literal(artist.artist_key, profile.engine)}) "
                "ON CONFLICT DO NOTHING;"
            )

        return (
            f"INSERT IGNORE INTO {identifier(profile.artist_table, profile.engine)} "
            f"({identifier(profile.artist_name_column, profile.engine)}, "
            f"{identifier(profile.artist_name_key_column, profile.engine)}) "
            f"VALUES ({string_literal(artist.artist_name, profile.engine)}, "
            f"{string_literal(artist.artist_key, profile.engine)});"
        )

    def _build_release_insert(self, profile, release: CanonicalRelease) -> str:
        release_title_key = release.release_key.split("|", 2)[1]
        columns = ", ".join(
            [
                identifier(profile.release_artist_id_column, profile.engine),
                identifier(profile.release_title_column, profile.engine),
                identifier(profile.release_title_key_column, profile.engine),
                identifier(profile.release_date_column, profile.engine),
                identifier(profile.release_upc_column, profile.engine),
            ]
        )
        if profile.engine.lower() == "postgresql":
            return (
                f"INSERT INTO {identifier(profile.release_table, profile.engine)} ({columns}) "
                f"SELECT {identifier(profile.artist_id_column, profile.engine)}, "
                f"{string_literal(release.release_title, profile.engine)}, "
                f"{string_literal(release_title_key, profile.engine)}, "
                f"{string_literal(release.release_date, profile.engine)}, "
                f"{string_literal(release.upc, profile.engine)} "
                f"FROM {identifier(profile.artist_table, profile.engine)} "
                f"WHERE {identifier(profile.artist_lookup_column, profile.engine)} = "
                f"{string_literal(release.artist_key, profile.engine)} "
                "ON CONFLICT DO NOTHING;"
            )

        return (
            f"INSERT IGNORE INTO {identifier(profile.release_table, profile.engine)} ({columns}) "
            f"SELECT {identifier(profile.artist_id_column, profile.engine)}, "
            f"{string_literal(release.release_title, profile.engine)}, "
            f"{string_literal(release_title_key, profile.engine)}, "
            f"{string_literal(release.release_date, profile.engine)}, "
            f"{string_literal(release.upc, profile.engine)} "
            f"FROM {identifier(profile.artist_table, profile.engine)} "
            f"WHERE {identifier(profile.artist_lookup_column, profile.engine)} = "
            f"{string_literal(release.artist_key, profile.engine)};"
        )


class DatabaseApplyService:
    def __init__(self) -> None:
        self.target_profile_loader = TargetProfileLoader()

    def apply(self, target_profile_path: Path, sql_file: Path) -> ApplyReport:
        target_profile = self.target_profile_loader.load(target_profile_path)
        sql_text = sql_file.read_text(encoding="utf-8")
        if self._resolve_apply_mode(target_profile) == "command":
            mode_label = self._apply_with_command(target_profile, sql_text)
        else:
            mode_label = self._apply_with_driver(target_profile, sql_text)
        return ApplyReport(command=mode_label, sql_file=sql_file)

    def _resolve_apply_mode(self, profile) -> str:
        if profile.apply_mode:
            return profile.apply_mode.lower()
        if profile.apply_command:
            return "command"
        return "driver"

    def _apply_with_driver(self, profile, sql_text: str) -> str:
        settings = self._build_driver_settings(profile)
        statements = self._split_sql_statements(sql_text)
        engine = profile.engine.lower()

        if engine == "postgresql":
            try:
                import psycopg
            except ImportError as exc:
                raise ValueError(
                    "PostgreSQL direct apply requires the 'psycopg[binary]' package."
                ) from exc

            connection = psycopg.connect(**settings)
            try:
                with connection.cursor() as cursor:
                    for statement in statements:
                        cursor.execute(statement)
                connection.commit()
            except Exception as exc:
                connection.rollback()
                raise ValueError(f"PostgreSQL apply failed: {exc}") from exc
            finally:
                connection.close()
            return "python-driver:postgresql"

        try:
            import mysql.connector
        except ImportError as exc:
            raise ValueError(
                "MySQL direct apply requires the 'mysql-connector-python' package."
            ) from exc

        connection = mysql.connector.connect(**settings)
        try:
            cursor = connection.cursor()
            try:
                for statement in statements:
                    cursor.execute(statement)
                connection.commit()
            finally:
                cursor.close()
        except Exception as exc:
            connection.rollback()
            raise ValueError(f"MySQL apply failed: {exc}") from exc
        finally:
            connection.close()
        return "python-driver:mysql"

    def _apply_with_command(self, profile, sql_text: str) -> str:
        command, env = self._build_command(profile)
        completed = subprocess.run(
            command,
            input=sql_text,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            detail = stderr or stdout or f"exit code {completed.returncode}"
            raise ValueError(f"Apply command failed: {detail}")
        return " ".join(command)

    def _build_driver_settings(self, profile) -> dict[str, object]:
        settings: dict[str, object] = {
            "host": self._required_apply_value(profile.apply_host, "target.apply.host"),
            "port": profile.apply_port or (5432 if profile.engine.lower() == "postgresql" else 3306),
            "user": self._required_apply_value(profile.apply_user, "target.apply.user"),
            "password": self._load_password(profile.apply_password_env) if profile.apply_password_env else "",
        }
        database = self._required_apply_value(profile.apply_database, "target.apply.database")
        if profile.engine.lower() == "postgresql":
            settings["dbname"] = database
        else:
            settings["database"] = database
            settings["charset"] = "utf8mb4"
        return settings

    def _split_sql_statements(self, sql_text: str) -> list[str]:
        statements: list[str] = []
        current_lines: list[str] = []

        for raw_line in sql_text.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("--"):
                continue
            current_lines.append(raw_line)
            if stripped.endswith(";"):
                statements.append("\n".join(current_lines).strip())
                current_lines = []

        if current_lines:
            raise ValueError("Generated SQL ended with an incomplete statement.")

        return statements

    def _build_command(self, profile) -> tuple[list[str], dict[str, str]]:
        env = os.environ.copy()
        engine = profile.engine.lower()
        command = profile.apply_command or ("psql" if engine == "postgresql" else "mysql")
        host = self._required_apply_value(profile.apply_host, "target.apply.host")
        database = self._required_apply_value(profile.apply_database, "target.apply.database")
        user = self._required_apply_value(profile.apply_user, "target.apply.user")

        if engine == "postgresql":
            port = str(profile.apply_port or 5432)
            if profile.apply_password_env:
                env["PGPASSWORD"] = self._load_password(profile.apply_password_env)
            return (
                [
                    command,
                    "--host",
                    host,
                    "--port",
                    port,
                    "--username",
                    user,
                    "--dbname",
                    database,
                    "-v",
                    "ON_ERROR_STOP=1",
                ],
                env,
            )

        port = str(profile.apply_port or 3306)
        if profile.apply_password_env:
            env["MYSQL_PWD"] = self._load_password(profile.apply_password_env)
        return (
            [
                command,
                "--host",
                host,
                "--port",
                port,
                "--user",
                user,
                "--default-character-set=utf8mb4",
                database,
            ],
            env,
        )

    def _required_apply_value(self, value: str | None, key: str) -> str:
        if value is None or not value.strip():
            raise ValueError(f"Missing required apply setting: {key}")
        return value

    def _load_password(self, env_name: str) -> str:
        password = os.environ.get(env_name)
        if password is None:
            raise ValueError(f"Environment variable not set for {env_name}")
        return password


class BootstrapService:
    def __init__(self) -> None:
        self.import_service = CatalogImportService()
        self.catalog_store = CatalogStore()
        self.plan_service = TargetPlanService()
        self.export_service = SqlExportService()
        self.apply_service = DatabaseApplyService()

    def bootstrap(
        self,
        input_path: Path,
        target_profile_path: Path,
        data_dir: Path,
        input_kind: str = "auto",
        sql_output_file: Path | None = None,
        apply_changes: bool = False,
    ) -> BootstrapReport:
        resolved_input_kind = self._resolve_input_kind(input_path, input_kind)
        target_profile = self.plan_service.target_profile_loader.load(target_profile_path)

        if sql_output_file is None and not apply_changes:
            execution = self._execute_import(
                input_path,
                data_dir,
                resolved_input_kind,
                persist_catalog=False,
                run_root_name="previews",
            )
            mode = "dry-run"
        else:
            execution = self._execute_import(
                input_path,
                data_dir,
                resolved_input_kind,
                persist_catalog=False,
                run_root_name="runs",
            )
            mode = "export-sql"

        import_report = execution.report
        run_dir = execution.run_dir
        review_queue_file = run_dir / "review_queue.csv"
        review_summary_file = run_dir / "review-summary.txt"
        review_queue_rows = read_rows(review_queue_file)
        self._write_review_summary(review_summary_file, review_queue_rows)
        latest_run_summary = LatestRunDecisionSummary(
            run_id=import_report.run_id,
            auto_create_count=import_report.auto_create_count,
            auto_match_count=import_report.auto_match_count,
            review_count=import_report.review_count,
            failure_count=import_report.failure_count,
        )

        if sql_output_file is None and apply_changes:
            sql_output_file = run_dir / "apply.sql"

        apply_report = None
        if sql_output_file is not None:
            plan_report = self.export_service.export_for_catalog(
                target_profile,
                execution.catalog,
                latest_run_summary,
                sql_output_file,
            )
            if apply_changes:
                apply_report = self.apply_service.apply(target_profile_path, sql_output_file)
                mode = "apply"
            self.catalog_store.save(data_dir, execution.catalog)
            self.catalog_store.mark_run_committed(run_dir)
        else:
            plan_report = self.plan_service.plan_for_catalog(
                target_profile,
                execution.catalog,
                latest_run_summary,
            )

        report = BootstrapReport(
            mode=mode,
            import_report=import_report,
            plan_report=plan_report,
            run_dir=run_dir,
            review_queue_file=review_queue_file,
            review_summary_file=review_summary_file,
            review_queue_count=len(review_queue_rows),
            catalog_updated=(mode != "dry-run"),
            sql_file=sql_output_file,
            apply_report=apply_report,
        )
        (run_dir / "bootstrap-report.txt").write_text(report.to_console_text(), encoding="utf-8")
        return report

    def _resolve_input_kind(self, input_path: Path, input_kind: str) -> str:
        normalized = input_kind.lower()
        if normalized in {"csv", "musicbrainz"}:
            return normalized
        if normalized != "auto":
            raise ValueError("input_kind must be one of: auto, csv, musicbrainz")

        if input_path.suffix.lower() == ".csv":
            return "csv"
        if input_path.is_dir():
            return "musicbrainz"
        if is_supported_musicbrainz_input_file_name(input_path.name):
            return "musicbrainz"
        raise ValueError(f"Could not infer input kind from: {input_path}")

    def _execute_import(
        self,
        input_path: Path,
        data_dir: Path,
        input_kind: str,
        *,
        persist_catalog: bool,
        run_root_name: str,
    ) -> _ImportExecutionResult:
        if input_kind == "csv":
            return self.import_service.execute_snapshot(
                input_path,
                data_dir,
                persist_catalog=persist_catalog,
                run_root_name=run_root_name,
            )
        return self.import_service.execute_musicbrainz(
            input_path,
            data_dir,
            persist_catalog=persist_catalog,
            run_root_name=run_root_name,
        )

    def _write_review_summary(self, output_file: Path, rows: list[dict[str, str]]) -> None:
        reason_counts: dict[str, int] = {}
        for row in rows:
            key = f'{row["decision_type"]}:{row["reason_code"]}'
            reason_counts[key] = reason_counts.get(key, 0) + 1

        lines = [
            "Review queue summary",
            "",
            f"Rows requiring review: {len(rows)}",
        ]
        if not rows:
            lines.append("No uncertain records were produced in this run.")
        else:
            lines.extend(
                [
                    "",
                    "Breakdown by reason",
                ]
            )
            for key in sorted(reason_counts):
                lines.append(f"- {key}: {reason_counts[key]}")

            lines.extend(
                [
                    "",
                    "First flagged rows",
                ]
            )
            for row in rows[:5]:
                candidate = ""
                if row["candidate_release_id"]:
                    candidate = (
                        f' -> candidate #{row["candidate_release_id"]} '
                        f'({row["candidate_release_title"]}, {row["candidate_release_date"]})'
                    )
                lines.append(
                    f'- {row["source_id"]}: {row["reason_code"]} '
                    f'[{row["artist_name"]} / {row["release_title"]} / {row["release_date"]}]'
                    f"{candidate}"
                )

        output_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
