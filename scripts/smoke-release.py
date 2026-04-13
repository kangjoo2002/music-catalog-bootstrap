from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the release ZIP by extracting and running it.")
    parser.add_argument(
        "--archive",
        type=Path,
        default=None,
        help="path to a release ZIP; defaults to the latest ZIP in build/distributions",
    )
    args = parser.parse_args()

    archive = args.archive or find_latest_archive()
    if not archive.exists():
        raise SystemExit(f"Release archive not found: {archive}")

    with tempfile.TemporaryDirectory() as temp_dir:
        extract_root = Path(temp_dir) / "release"
        with zipfile.ZipFile(archive, "r") as handle:
            handle.extractall(extract_root)

        extracted_entries = [path for path in extract_root.iterdir() if path.is_dir()]
        if len(extracted_entries) != 1:
            raise SystemExit("Expected exactly one top-level directory inside the release ZIP.")

        app_root = extracted_entries[0]
        data_dir = app_root / ".catalog-data-smoke-release"
        sql_file = app_root / "out" / "catalog.sql"

        run_command(
            build_launcher_command(
                app_root,
                [
                    "bootstrap",
                    "fixtures/sample_releases.csv",
                    "fixtures/sample-target.properties",
                    "--data-dir",
                    str(data_dir),
                ],
            ),
            cwd=app_root,
        )
        run_command(
            build_launcher_command(
                app_root,
                [
                    "bootstrap",
                    "fixtures/sample_releases.csv",
                    "fixtures/sample-target.properties",
                    "--data-dir",
                    str(data_dir),
                    "--export-sql",
                    str(sql_file),
                ],
            ),
            cwd=app_root,
        )

        if not sql_file.exists():
            raise SystemExit("Release smoke test failed: expected SQL output file was not created.")

        print(f"Release smoke test passed: {archive}")
        return 0


def find_latest_archive() -> Path:
    distributions_dir = ROOT / "build" / "distributions"
    archives = sorted(distributions_dir.glob("music-catalog-bootstrap-*.zip"))
    if not archives:
        return distributions_dir / "missing.zip"
    return archives[-1]


def build_launcher_command(app_root: Path, arguments: list[str]) -> list[str]:
    if os.name == "nt":
        return [str(app_root / "bin" / "music-catalog-bootstrap.bat"), *arguments]
    return ["sh", str(app_root / "bin" / "music-catalog-bootstrap"), *arguments]


def run_command(command: list[str], cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit code {completed.returncode}"
        raise SystemExit(f"Release smoke test command failed: {detail}")


if __name__ == "__main__":
    raise SystemExit(main())
