from __future__ import annotations


def identifier(value: str, engine: str) -> str:
    if engine.lower() == "postgresql":
        return f'"{value}"'
    return f"`{value}`"


def string_literal(value: str | None, engine: str) -> str:
    if value is None:
        return "NULL"
    escaped = value.replace("'", "''")
    if engine.lower() == "mysql":
        escaped = escaped.replace("\\", "\\\\")
    return "'" + escaped + "'"
