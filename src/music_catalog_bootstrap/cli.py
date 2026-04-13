from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .services import BootstrapService, CatalogImportService, SqlExportService, TargetPlanService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="music-catalog-bootstrap",
        description="Bootstrap a music service catalog from MusicBrainz dumps or normalized CSV snapshots.",
    )
    subparsers = parser.add_subparsers(dest="command")

    import_musicbrainz = subparsers.add_parser("import-musicbrainz", help="Import a MusicBrainz release dump.")
    import_musicbrainz.add_argument("release_input", help="release dump file or directory")
    import_musicbrainz.add_argument("data_dir", nargs="?", default=".catalog-data", help="catalog data directory")

    import_snapshot = subparsers.add_parser("import", help="Import a normalized CSV snapshot.")
    import_snapshot.add_argument("csv_file", help="normalized CSV input file")
    import_snapshot.add_argument("data_dir", nargs="?", default=".catalog-data", help="catalog data directory")

    plan = subparsers.add_parser("plan", help="Print the current catalog and latest run summary.")
    plan.add_argument("target_profile", help="target profile properties file")
    plan.add_argument("data_dir", nargs="?", default=".catalog-data", help="catalog data directory")

    export_sql = subparsers.add_parser("export-sql", help="Generate SQL from the current catalog.")
    export_sql.add_argument("target_profile", help="target profile properties file")
    export_sql.add_argument("output_file", help="output SQL file")
    export_sql.add_argument("data_dir", nargs="?", default=".catalog-data", help="catalog data directory")

    bootstrap = subparsers.add_parser(
        "bootstrap",
        help="Run import, decision classification, review queue export, and dry-run / SQL export / apply in one step.",
    )
    bootstrap.add_argument("input_path", help="CSV file, MusicBrainz dump file, or dump directory")
    bootstrap.add_argument("target_profile", help="target profile properties file")
    bootstrap.add_argument("--data-dir", default=".catalog-data", help="catalog data directory")
    bootstrap.add_argument(
        "--input-kind",
        choices=["auto", "csv", "musicbrainz"],
        default="auto",
        help="force the input type when auto detection is not enough",
    )
    bootstrap.add_argument("--export-sql", help="write generated SQL to this file")
    bootstrap.add_argument(
        "--apply",
        action="store_true",
        help="apply generated SQL to the target database through built-in Python drivers",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_usage()
        return 1

    try:
        if args.command == "import-musicbrainz":
            report = CatalogImportService().import_musicbrainz(Path(args.release_input), Path(args.data_dir))
            print(report.to_console_text())
            return 0

        if args.command == "import":
            report = CatalogImportService().import_snapshot(Path(args.csv_file), Path(args.data_dir))
            print(report.to_console_text())
            return 0

        if args.command == "plan":
            report = TargetPlanService().plan(Path(args.target_profile), Path(args.data_dir))
            print(report.to_console_text())
            return 0

        if args.command == "export-sql":
            report = SqlExportService().export(
                Path(args.target_profile),
                Path(args.data_dir),
                Path(args.output_file),
            )
            print(report.to_console_text())
            print(f"SQL file: {args.output_file}")
            return 0

        if args.command == "bootstrap":
            report = BootstrapService().bootstrap(
                Path(args.input_path),
                Path(args.target_profile),
                Path(args.data_dir),
                input_kind=args.input_kind,
                sql_output_file=Path(args.export_sql) if args.export_sql else None,
                apply_changes=args.apply,
            )
            print(report.to_console_text())
            return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.print_usage()
    return 1


def run() -> None:
    raise SystemExit(main())
