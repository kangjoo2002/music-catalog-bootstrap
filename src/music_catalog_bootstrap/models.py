from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DecisionType(str, Enum):
    AUTO_CREATE = "AUTO_CREATE"
    AUTO_MATCH = "AUTO_MATCH"
    REVIEW = "REVIEW"
    FAILURE = "FAILURE"


@dataclass(frozen=True)
class InputReleaseRecord:
    line_number: int
    source_id: str
    artist_name: str
    release_title: str
    release_date: str
    upc: str

    @classmethod
    def from_row(cls, line_number: int, row: dict[str, str]) -> "InputReleaseRecord":
        return cls(
            line_number=line_number,
            source_id=(row.get("source_id") or "").strip(),
            artist_name=(row.get("artist_name") or "").strip(),
            release_title=(row.get("release_title") or "").strip(),
            release_date=(row.get("release_date") or "").strip(),
            upc=(row.get("upc") or "").strip(),
        )


@dataclass(frozen=True)
class StagingReleaseRecord:
    line_number: int
    source_id: str
    artist_name: str
    artist_key: str
    release_title: str
    release_key: str
    release_date: str
    upc: str


@dataclass(frozen=True)
class CanonicalArtist:
    artist_id: int
    artist_name: str
    artist_key: str


@dataclass(frozen=True)
class CanonicalRelease:
    release_id: int
    artist_id: int
    artist_name: str
    artist_key: str
    release_title: str
    release_key: str
    release_date: str
    upc: str


@dataclass(frozen=True)
class ImportDecision:
    source_id: str
    decision_type: DecisionType
    reason_code: str
    canonical_release_id: str


@dataclass(frozen=True)
class LatestRunDecisionSummary:
    run_id: str
    auto_create_count: int
    auto_match_count: int
    review_count: int
    failure_count: int


@dataclass(frozen=True)
class TargetProfile:
    engine: str
    write_mode: str
    artist_table: str
    artist_id_column: str
    artist_lookup_column: str
    artist_name_column: str
    artist_name_key_column: str
    release_table: str
    release_artist_id_column: str
    release_title_column: str
    release_title_key_column: str
    release_date_column: str
    release_upc_column: str
    apply_mode: str | None = None
    apply_command: str | None = None
    apply_host: str | None = None
    apply_port: int | None = None
    apply_database: str | None = None
    apply_user: str | None = None
    apply_password_env: str | None = None


@dataclass(frozen=True)
class ImportReport:
    run_id: str
    total_rows: int
    auto_create_count: int
    auto_match_count: int
    review_count: int
    failure_count: int

    def to_console_text(self) -> str:
        return "\n".join(
            [
                f"Run ID: {self.run_id}",
                f"Total rows: {self.total_rows}",
                f"Auto create: {self.auto_create_count}",
                f"Auto match: {self.auto_match_count}",
                f"Review: {self.review_count}",
                f"Failure: {self.failure_count}",
            ]
        )


@dataclass(frozen=True)
class TargetPlanReport:
    target_engine: str
    write_mode: str
    artist_table: str
    release_table: str
    canonical_artist_count: int
    canonical_release_count: int
    latest_run_id: str
    latest_auto_create_count: int
    latest_auto_match_count: int
    latest_review_count: int
    latest_failure_count: int

    def to_console_text(self) -> str:
        return "\n".join(
            [
                f"Target engine: {self.target_engine}",
                f"Write mode: {self.write_mode}",
                f"Artist table: {self.artist_table}",
                f"Release table: {self.release_table}",
                f"Canonical artists: {self.canonical_artist_count}",
                f"Canonical releases: {self.canonical_release_count}",
                f"Latest run: {self.latest_run_id}",
                f"Latest auto create: {self.latest_auto_create_count}",
                f"Latest auto match: {self.latest_auto_match_count}",
                f"Latest review: {self.latest_review_count}",
                f"Latest failure: {self.latest_failure_count}",
            ]
        )


@dataclass(frozen=True)
class ApplyReport:
    command: str
    sql_file: Path


@dataclass(frozen=True)
class BootstrapReport:
    mode: str
    import_report: ImportReport
    plan_report: TargetPlanReport
    run_dir: Path
    review_queue_file: Path
    review_summary_file: Path
    review_queue_count: int
    catalog_updated: bool
    sql_file: Path | None = None
    apply_report: ApplyReport | None = None

    def to_console_text(self) -> str:
        lines = [
            "Bootstrap summary",
            "",
            f"Mode:                   {self.mode}",
            f"Run ID:                 {self.import_report.run_id}",
            f"Run directory:          {self.run_dir}",
            "",
            "Decision summary",
            f"Input rows:             {self.import_report.total_rows}",
            f"AUTO_CREATE:            {self.import_report.auto_create_count}",
            f"AUTO_MATCH:             {self.import_report.auto_match_count}",
            f"REVIEW:                 {self.import_report.review_count}",
            f"FAILURE:                {self.import_report.failure_count}",
            "",
            "Catalog state",
            f"Canonical artists:      {self.plan_report.canonical_artist_count}",
            f"Canonical releases:     {self.plan_report.canonical_release_count}",
            "",
            "Target",
            f"Engine:                 {self.plan_report.target_engine}",
            f"Artist table:           {self.plan_report.artist_table}",
            f"Release table:          {self.plan_report.release_table}",
            "",
            "Artifacts",
            f"Review queue rows:      {self.review_queue_count}",
            f"Review queue:           {self.review_queue_file}",
            f"Review summary:         {self.review_summary_file}",
        ]
        if self.sql_file is not None:
            lines.append(f"SQL file:               {self.sql_file}")
        lines.append("")
        lines.append("Result")
        if self.apply_report is None:
            if self.sql_file is None:
                lines.append("No changes have been applied.")
                lines.append(f"Canonical catalog updated: {'yes' if self.catalog_updated else 'no'}")
                if self.catalog_updated:
                    lines.append("Run again with --apply when ready.")
                else:
                    lines.append("Dry-run did not change the canonical catalog.")
                    lines.append("Run again with --export-sql or --apply when ready.")
            else:
                lines.append("No changes have been applied.")
                lines.append(f"Canonical catalog updated: {'yes' if self.catalog_updated else 'no'}")
                lines.append("The generated SQL file can be inspected or applied manually.")
        else:
            lines.append("Changes have been applied.")
            lines.append(f"Canonical catalog updated: {'yes' if self.catalog_updated else 'no'}")
            lines.append(f"Apply method:           {self.apply_report.command}")
        if self.review_queue_count > 0:
            lines.append(f"Review the flagged rows in {self.review_queue_file}.")
        return "\n".join(lines)
