"""Bounded, read-only text loading shared by inspection analyzers (#56)."""

from __future__ import annotations

from pathlib import Path

MAX_FILE_SIZE = 1_000_000


def read_text_limited(path: Path, limit: int = MAX_FILE_SIZE) -> str | None:
    """Read at most ``limit + 1`` bytes; return None when the file exceeds ``limit``.

    Decodes strictly as UTF-8 (a BOM is accepted). Raises ``OSError`` when the
    file cannot be read and ``UnicodeDecodeError`` when it is not UTF-8; other
    encodings are never guessed.
    """
    with path.open("rb") as fh:
        data = fh.read(limit + 1)
    if len(data) > limit:
        return None
    return data.decode("utf-8-sig")
