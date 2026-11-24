"""Conservative pruning of literal directory entries from .git/info/exclude."""

import hashlib
import re
import struct
from pathlib import Path

from spawn.inspection._reading import read_inventory_text, read_repository_bytes

_RULE_LIMIT = 64 * 1024
_INDEX_LIMIT = 4 * 1024 * 1024
_DIRECTORY = re.compile(r"/?([a-zA-Z0-9_.-]+)/")


def _indexed_roots(data: bytes) -> set[bytes] | None:
    """Read top-level names from a conventional SHA-1 Git index v2 or v3."""
    if len(data) < 32 or data[:4] != b"DIRC":
        return None
    version, count = struct.unpack_from(">II", data, 4)
    end = len(data) - 20
    if (
        version not in (2, 3)
        or count > (end - 12) // 64
        or hashlib.sha1(data[:end], usedforsecurity=False).digest() != data[end:]
    ):
        return None
    offset = 12
    names = set()
    for _ in range(count):
        if offset + 62 >= end:
            return None
        flags = struct.unpack_from(">H", data, offset + 60)[0]
        start = offset + 62
        if flags & 0x4000:
            if version == 2:
                return None
            start += 2
        terminator = data.find(b"\0", start, end)
        if terminator <= start:
            return None
        name = data[start:terminator]
        if min(len(name), 0xFFF) != flags & 0xFFF:
            return None
        names.add(name.split(b"/", 1)[0].lower())
        offset += (terminator - offset + 8) & ~7
        if offset > end or any(data[terminator:offset]):
            return None
    while offset < end:
        # Unknown required extensions (including split/sparse indexes) can
        # carry additional tracked paths, so do not prune in that case.
        if offset + 8 > end or not b"A" <= data[offset : offset + 1] <= b"Z":
            return None
        size = struct.unpack_from(">I", data, offset + 4)[0]
        offset += 8 + size
    return names if offset == end else None


def root_exclusions(root: Path) -> set[str]:
    """Return only top-level directories that can safely be pruned.

    Unsupported, missing, or ambiguous Git metadata leaves discovery unchanged.
    """
    try:
        local = read_inventory_text(root, ".git/info/exclude", _RULE_LIMIT)
        if not local:
            return set()
        rules = local.replace("\r\n", "\n").split("\n")
        candidates = {
            match[1]
            for line in rules
            if (match := _DIRECTORY.fullmatch(line)) and match[1] not in {".", ".."}
        }
        if not candidates or any(line.startswith("!") for line in rules):
            return set()
        try:
            ignore = read_inventory_text(root, ".gitignore", _RULE_LIMIT)
        except FileNotFoundError:
            ignore = ""
        if ignore is None or any(line.startswith("!") for line in ignore.split("\n")):
            return set()
        index = read_repository_bytes(root, ".git/index", _INDEX_LIMIT)
    except (OSError, UnicodeError):
        return set()
    tracked = _indexed_roots(index) if index is not None else None
    if tracked is None:
        return set()
    return {name for name in candidates if name.lower().encode("ascii") not in tracked}
