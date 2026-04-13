from __future__ import annotations

import io
import json
import lzma
import tarfile
from pathlib import Path
from typing import Iterator

from .models import InputReleaseRecord


def resolve_musicbrainz_input(input_path: Path) -> Path:
    if not input_path.exists():
        raise ValueError(f"MusicBrainz input not found: {input_path}")

    if input_path.is_file():
        return input_path

    candidates = sorted(
        path
        for path in input_path.iterdir()
        if path.is_file() and is_supported_musicbrainz_input_file_name(path.name)
    )
    if not candidates:
        raise ValueError(f"No MusicBrainz release input found under: {input_path}")
    return candidates[0]


def iter_musicbrainz_records(input_file: Path) -> Iterator[InputReleaseRecord]:
    normalized_name = input_file.name.lower()

    if normalized_name.endswith(".tar.xz") or normalized_name.endswith(".txz"):
        yield from _iter_tar_xz_records(input_file)
        return

    if normalized_name.endswith(".xz"):
        with lzma.open(input_file, "rt", encoding="utf-8") as handle:
            yield from _iter_json_lines(handle)
        return

    with input_file.open("r", encoding="utf-8") as handle:
        yield from _iter_json_lines(handle)


def parse_release_line(line_number: int, json_line: str) -> InputReleaseRecord:
    data = json.loads(json_line)
    source_id = ((data.get("id") or f"musicbrainz-line-{line_number}") or "").strip()
    artist_credit = data.get("artist-credit") or []

    credits: list[str] = []
    for credit in artist_credit:
        if not isinstance(credit, dict):
            continue
        name = (credit.get("name") or "").strip()
        joinphrase = credit.get("joinphrase") or ""
        if name:
            credits.append(name + joinphrase)

    return InputReleaseRecord(
        line_number=line_number,
        source_id=source_id,
        artist_name="".join(credits).strip(),
        release_title=((data.get("title") or "")).strip(),
        release_date=((data.get("date") or "")).strip(),
        upc=((data.get("barcode") or "")).strip(),
    )


def is_supported_musicbrainz_input_file_name(file_name: str) -> bool:
    normalized_name = file_name.lower()
    if normalized_name.endswith(".tar.xz") or normalized_name.endswith(".txz"):
        return "release" in normalized_name
    if normalized_name.endswith(".xz"):
        return "release" in normalized_name
    return is_supported_musicbrainz_payload_name(normalized_name)


def is_supported_musicbrainz_payload_name(file_name: str) -> bool:
    normalized_path = file_name.replace("\\", "/").lower()
    base_name = normalized_path.rsplit("/", 1)[-1]
    if base_name in {"release", "release.json", "release.jsonl"}:
        return True
    return "release" in base_name and (base_name.endswith(".json") or base_name.endswith(".jsonl"))


def _iter_tar_xz_records(archive_path: Path) -> Iterator[InputReleaseRecord]:
    with tarfile.open(archive_path, mode="r:xz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            if not is_supported_musicbrainz_payload_name(member.name):
                continue

            extracted = archive.extractfile(member)
            if extracted is None:
                break

            with extracted:
                with io.TextIOWrapper(extracted, encoding="utf-8") as handle:
                    yield from _iter_json_lines(handle)
            return

    raise ValueError(f"No MusicBrainz release file found in archive: {archive_path}")


def _iter_json_lines(handle: io.TextIOBase) -> Iterator[InputReleaseRecord]:
    for line_number, line in enumerate(handle, start=1):
        if not line.strip():
            continue
        yield parse_release_line(line_number, line)
