from __future__ import annotations

from pathlib import Path

from .csv_support import read_rows, write_rows
from .models import CanonicalArtist, CanonicalRelease, DecisionType, LatestRunDecisionSummary


class CanonicalCatalog:
    def __init__(self, artists: list[CanonicalArtist], releases: list[CanonicalRelease]) -> None:
        self._artists = list(artists)
        self._releases = list(releases)

    @property
    def artists(self) -> list[CanonicalArtist]:
        return list(self._artists)

    @property
    def releases(self) -> list[CanonicalRelease]:
        return list(self._releases)

    def find_artist_by_key(self, artist_key: str) -> CanonicalArtist | None:
        for artist in self._artists:
            if artist.artist_key == artist_key:
                return artist
        return None

    def find_release_by_upc(self, upc: str) -> CanonicalRelease | None:
        if not upc:
            return None
        for release in self._releases:
            if release.upc == upc:
                return release
        return None

    def find_release_by_exact_key(self, release_key: str) -> CanonicalRelease | None:
        for release in self._releases:
            if release.release_key == release_key:
                return release
        return None

    def find_release_by_artist_and_title(self, artist_key: str, release_title_key: str) -> CanonicalRelease | None:
        prefix = f"{artist_key}|{release_title_key}|"
        for release in self._releases:
            if release.artist_key == artist_key and release.release_key.startswith(prefix):
                return release
        return None

    def ensure_artist(self, artist_name: str, artist_key: str) -> CanonicalArtist:
        existing = self.find_artist_by_key(artist_key)
        if existing is not None:
            return existing

        next_id = max((artist.artist_id for artist in self._artists), default=0) + 1
        created = CanonicalArtist(next_id, artist_name, artist_key)
        self._artists.append(created)
        return created

    def create_release(
        self,
        artist: CanonicalArtist,
        release_title: str,
        release_key: str,
        release_date: str,
        upc: str,
    ) -> CanonicalRelease:
        next_id = max((release.release_id for release in self._releases), default=0) + 1
        created = CanonicalRelease(
            release_id=next_id,
            artist_id=artist.artist_id,
            artist_name=artist.artist_name,
            artist_key=artist.artist_key,
            release_title=release_title,
            release_key=release_key,
            release_date=release_date,
            upc=upc,
        )
        self._releases.append(created)
        return created


class CatalogStore:
    COMMITTED_MARKER = "committed.txt"

    def load(self, data_dir: Path, create_if_missing: bool = True) -> CanonicalCatalog:
        canonical_dir = data_dir / "canonical"
        if create_if_missing:
            canonical_dir.mkdir(parents=True, exist_ok=True)

        artists = self._read_artists(canonical_dir / "artists.csv")
        releases = self._read_releases(canonical_dir / "releases.csv")
        return CanonicalCatalog(artists, releases)

    def save(self, data_dir: Path, catalog: CanonicalCatalog) -> None:
        canonical_dir = data_dir / "canonical"
        canonical_dir.mkdir(parents=True, exist_ok=True)

        write_rows(
            canonical_dir / "artists.csv",
            ["artist_id", "artist_name", "artist_key"],
            [
                [str(artist.artist_id), artist.artist_name, artist.artist_key]
                for artist in catalog.artists
            ],
        )

        write_rows(
            canonical_dir / "releases.csv",
            [
                "release_id",
                "artist_id",
                "artist_name",
                "artist_key",
                "release_title",
                "release_key",
                "release_date",
                "upc",
            ],
            [
                [
                    str(release.release_id),
                    str(release.artist_id),
                    release.artist_name,
                    release.artist_key,
                    release.release_title,
                    release.release_key,
                    release.release_date,
                    release.upc,
                ]
                for release in catalog.releases
            ],
        )

    def mark_run_committed(self, run_dir: Path) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / self.COMMITTED_MARKER).write_text("committed\n", encoding="utf-8")

    def load_latest_run_summary(self, data_dir: Path) -> LatestRunDecisionSummary | None:
        runs_dir = data_dir / "runs"
        if not runs_dir.exists():
            return None

        run_dirs = sorted(
            [
                path
                for path in runs_dir.iterdir()
                if path.is_dir() and (path / self.COMMITTED_MARKER).exists()
            ],
            key=lambda path: path.name,
        )
        if not run_dirs:
            return None

        latest_run_dir = run_dirs[-1]
        decisions_file = latest_run_dir / "decisions.csv"
        if not decisions_file.exists():
            return None

        auto_create_count = 0
        auto_match_count = 0
        review_count = 0
        failure_count = 0

        for row in read_rows(decisions_file):
            decision_type = DecisionType(row["decision_type"])
            if decision_type is DecisionType.AUTO_CREATE:
                auto_create_count += 1
            elif decision_type is DecisionType.AUTO_MATCH:
                auto_match_count += 1
            elif decision_type is DecisionType.REVIEW:
                review_count += 1
            elif decision_type is DecisionType.FAILURE:
                failure_count += 1

        return LatestRunDecisionSummary(
            run_id=latest_run_dir.name,
            auto_create_count=auto_create_count,
            auto_match_count=auto_match_count,
            review_count=review_count,
            failure_count=failure_count,
        )

    def _read_artists(self, path: Path) -> list[CanonicalArtist]:
        return [
            CanonicalArtist(
                artist_id=int(row["artist_id"]),
                artist_name=row["artist_name"],
                artist_key=row["artist_key"],
            )
            for row in read_rows(path)
        ]

    def _read_releases(self, path: Path) -> list[CanonicalRelease]:
        return [
            CanonicalRelease(
                release_id=int(row["release_id"]),
                artist_id=int(row["artist_id"]),
                artist_name=row["artist_name"],
                artist_key=row["artist_key"],
                release_title=row["release_title"],
                release_key=row["release_key"],
                release_date=row["release_date"],
                upc=row["upc"],
            )
            for row in read_rows(path)
        ]
