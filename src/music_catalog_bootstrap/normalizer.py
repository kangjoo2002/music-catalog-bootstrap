from __future__ import annotations

import re
import unicodedata


NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
SPACE_PATTERN = re.compile(r"\s+")


def normalize_key(text: str | None) -> str:
    if text is None:
        return ""

    normalized = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    lowered = without_marks.lower()
    collapsed = NON_ALNUM_PATTERN.sub(" ", lowered).strip()
    return SPACE_PATTERN.sub(" ", collapsed)
