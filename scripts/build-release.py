from __future__ import annotations

import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_INIT = ROOT / "src" / "music_catalog_bootstrap" / "__init__.py"
VERSION_PATTERN = re.compile(r'__version__ = "([^"]+)"')


def main() -> int:
    version = read_version()
    bundle_name = f"music-catalog-bootstrap-{version}"
    distributions_dir = ROOT / "build" / "distributions"
    staging_root = ROOT / "build" / "release-bundle"
    archive_path = distributions_dir / f"{bundle_name}.zip"
    distributions_dir.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    staging_dir = staging_root / f"{bundle_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    copy_release_tree(staging_dir)
    write_launchers(staging_dir)
    create_zip(staging_dir, archive_path)

    print(f"Release artifact: {archive_path.relative_to(ROOT)}")
    return 0


def read_version() -> str:
    match = VERSION_PATTERN.search(PACKAGE_INIT.read_text(encoding="utf-8"))
    if match is None:
        raise RuntimeError("Could not determine package version.")
    return match.group(1)


def copy_release_tree(staging_dir: Path) -> None:
    shutil.copytree(
        ROOT / "src" / "music_catalog_bootstrap",
        staging_dir / "src" / "music_catalog_bootstrap",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    shutil.copytree(ROOT / "fixtures", staging_dir / "fixtures")
    shutil.copytree(ROOT / "docs", staging_dir / "docs")
    shutil.copytree(ROOT / "examples", staging_dir / "examples", ignore=shutil.ignore_patterns(".catalog-data*"))
    shutil.copytree(
        ROOT / "scripts",
        staging_dir / "scripts",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    shutil.copy2(ROOT / "LICENSE", staging_dir / "LICENSE")
    shutil.copy2(ROOT / "pyproject.toml", staging_dir / "pyproject.toml")
    shutil.copy2(ROOT / "README.md", staging_dir / "README.md")
    shutil.copy2(ROOT / "README.ko.md", staging_dir / "README.ko.md")
    shutil.copy2(ROOT / "CHANGELOG.md", staging_dir / "CHANGELOG.md")
    shutil.copy2(ROOT / "CONTRIBUTING.md", staging_dir / "CONTRIBUTING.md")
    shutil.copy2(ROOT / "ROADMAP.md", staging_dir / "ROADMAP.md")
    shutil.copy2(ROOT / "SECURITY.md", staging_dir / "SECURITY.md")


def write_launchers(staging_dir: Path) -> None:
    bin_dir = staging_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    (bin_dir / "music-catalog-bootstrap").write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        'SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        'APP_HOME=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)\n'
        'export PYTHONPATH="$APP_HOME/src${PYTHONPATH:+:$PYTHONPATH}"\n'
        "if command -v python3 >/dev/null 2>&1; then\n"
        '  exec python3 -m music_catalog_bootstrap "$@"\n'
        "fi\n"
        'exec python -m music_catalog_bootstrap "$@"\n',
        encoding="utf-8",
    )

    (bin_dir / "music-catalog-bootstrap.bat").write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        "set \"SCRIPT_DIR=%~dp0\"\r\n"
        "for %%I in (\"%SCRIPT_DIR%..\") do set \"APP_HOME=%%~fI\"\r\n"
        "set \"PYTHONPATH=%APP_HOME%\\src;%PYTHONPATH%\"\r\n"
        "where py >nul 2>nul\r\n"
        "if %ERRORLEVEL% EQU 0 (\r\n"
        "    py -3 -m music_catalog_bootstrap %*\r\n"
        "    exit /b %ERRORLEVEL%\r\n"
        ")\r\n"
        "python -m music_catalog_bootstrap %*\r\n"
        "exit /b %ERRORLEVEL%\r\n",
        encoding="utf-8",
    )


def create_zip(staging_dir: Path, archive_path: Path) -> None:
    archive_root = archive_path.stem
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(staging_dir.rglob("*")):
            if path.is_dir():
                continue
            archive.write(path, Path(archive_root) / path.relative_to(staging_dir))


if __name__ == "__main__":
    raise SystemExit(main())
