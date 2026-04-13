from __future__ import annotations

import csv
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return []

        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({key: value or "" for key, value in row.items()})
        return rows


def write_rows(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(["" if value is None else value for value in row])


class CsvRowWriter:
    def __init__(self, path: Path, headers: list[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = path.open("w", encoding="utf-8", newline="")
        self._writer = csv.writer(self._handle)
        self._writer.writerow(headers)

    def write_row(self, values: list[str]) -> None:
        self._writer.writerow(["" if value is None else value for value in values])

    def close(self) -> None:
        self._handle.close()

    def __enter__(self) -> "CsvRowWriter":
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self.close()
