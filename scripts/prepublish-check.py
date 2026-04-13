from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    steps = [
        ("Unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("Build release ZIP", [sys.executable, "scripts/build-release.py"]),
        ("Smoke test release ZIP", [sys.executable, "scripts/smoke-release.py"]),
        ("PostgreSQL direct-apply smoke", smoke_apply_command("postgresql")),
        ("MySQL direct-apply smoke", smoke_apply_command("mysql")),
    ]

    for label, command in steps:
        print(f"==> {label}", flush=True)
        run(command)

    print("Prepublish checks passed.", flush=True)
    return 0


def smoke_apply_command(engine: str) -> list[str]:
    script = ROOT / "scripts" / "smoke-apply.ps1"
    if os.name == "nt":
        return ["PowerShell", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Engine", engine, "-Cleanup"]
    return ["sh", "./scripts/smoke-apply", "-Engine", engine, "-Cleanup"]


def run(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
