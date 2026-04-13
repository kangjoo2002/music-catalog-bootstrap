from __future__ import annotations

import re
from pathlib import Path

from .models import TargetProfile


SAFE_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")


class TargetProfileLoader:
    def load(self, profile_path: Path) -> TargetProfile:
        if not profile_path.exists():
            raise ValueError(f"Target profile not found: {profile_path}")

        properties = self._read_properties(profile_path)
        profile = TargetProfile(
            engine=self._required(properties, "target.engine"),
            write_mode=(properties.get("target.write_mode") or "insert-ignore").strip(),
            artist_table=self._required(properties, "artist.table"),
            artist_id_column=(properties.get("artist.id.column") or "id").strip(),
            artist_lookup_column=(properties.get("artist.lookup.column") or "name_key").strip(),
            artist_name_column=self._required(properties, "artist.name.column"),
            artist_name_key_column=self._required(properties, "artist.name_key.column"),
            release_table=self._required(properties, "release.table"),
            release_artist_id_column=self._required(properties, "release.artist_id.column"),
            release_title_column=self._required(properties, "release.title.column"),
            release_title_key_column=self._required(properties, "release.title_key.column"),
            release_date_column=self._required(properties, "release.date.column"),
            release_upc_column=self._required(properties, "release.upc.column"),
            apply_mode=self._optional(properties, "target.apply.mode"),
            apply_command=self._optional(properties, "target.apply.command"),
            apply_host=self._optional(properties, "target.apply.host"),
            apply_port=self._optional_int(properties, "target.apply.port"),
            apply_database=self._optional(properties, "target.apply.database"),
            apply_user=self._optional(properties, "target.apply.user"),
            apply_password_env=self._optional(properties, "target.apply.password_env"),
        )
        self._validate(profile)
        return profile

    def _read_properties(self, profile_path: Path) -> dict[str, str]:
        properties: dict[str, str] = {}
        for raw_line in profile_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            if "=" not in line:
                raise ValueError(f"Invalid target profile line: {raw_line}")
            key, value = line.split("=", 1)
            properties[key.strip()] = value.strip()
        return properties

    def _required(self, properties: dict[str, str], key: str) -> str:
        value = (properties.get(key) or "").strip()
        if not value:
            raise ValueError(f"Missing required target profile key: {key}")
        return value

    def _optional(self, properties: dict[str, str], key: str) -> str | None:
        value = (properties.get(key) or "").strip()
        if not value:
            return None
        return value

    def _optional_int(self, properties: dict[str, str], key: str) -> int | None:
        value = self._optional(properties, key)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"Invalid integer value for {key}: {value}") from exc

    def _validate(self, profile: TargetProfile) -> None:
        if profile.engine.lower() not in {"mysql", "postgresql"}:
            raise ValueError("Only mysql and postgresql target.engine values are supported.")

        if profile.write_mode.lower() != "insert-ignore":
            raise ValueError("Only insert-ignore write mode is supported in this MVP.")

        identifiers = {
            "artist.table": profile.artist_table,
            "artist.id.column": profile.artist_id_column,
            "artist.lookup.column": profile.artist_lookup_column,
            "artist.name.column": profile.artist_name_column,
            "artist.name_key.column": profile.artist_name_key_column,
            "release.table": profile.release_table,
            "release.artist_id.column": profile.release_artist_id_column,
            "release.title.column": profile.release_title_column,
            "release.title_key.column": profile.release_title_key_column,
            "release.date.column": profile.release_date_column,
            "release.upc.column": profile.release_upc_column,
        }
        for key, value in identifiers.items():
            if not SAFE_IDENTIFIER.match(value):
                raise ValueError(f"Invalid SQL identifier for {key}: {value}")

        if profile.apply_command and not Path(profile.apply_command).name.strip():
            raise ValueError("target.apply.command must not be blank.")

        if profile.apply_mode and profile.apply_mode.lower() not in {"driver", "command"}:
            raise ValueError("target.apply.mode must be either driver or command.")

        if profile.apply_password_env and not SAFE_IDENTIFIER.match(profile.apply_password_env):
            raise ValueError(
                f"Invalid environment variable name for target.apply.password_env: {profile.apply_password_env}"
            )

        if profile.apply_port is not None and profile.apply_port <= 0:
            raise ValueError("target.apply.port must be a positive integer.")

        has_apply_configuration = any(
            value is not None
            for value in [
                profile.apply_mode,
                profile.apply_command,
                profile.apply_host,
                profile.apply_port,
                profile.apply_database,
                profile.apply_user,
                profile.apply_password_env,
            ]
        )
        if has_apply_configuration:
            required_keys = {
                "target.apply.host": profile.apply_host,
                "target.apply.database": profile.apply_database,
                "target.apply.user": profile.apply_user,
            }
            for key, value in required_keys.items():
                if value is None or not value.strip():
                    raise ValueError(f"Missing required apply setting: {key}")
