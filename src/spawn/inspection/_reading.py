"""Bounded, read-only text loading shared by inspection analyzers (#56)."""

from __future__ import annotations

import os
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

if os.name == "nt":
    from spawn.inspection import _windows_fs

MAX_FILE_SIZE = 1_000_000
HAS_DIR_FDS = (
    os.open in os.supports_dir_fd
    and hasattr(os, "O_NOFOLLOW")
    and hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NONBLOCK")
)
DIR_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_DIRECTORY", 0)


def _read_utf8(fh: BinaryIO, limit: int) -> str | None:
    data = fh.read(limit + 1)
    if len(data) > limit:
        return None
    return data.decode("utf-8-sig")


@contextmanager
def open_directory(root: Path, parts: tuple[str, ...] = ()):
    """Open a POSIX directory without reparsing any component of its path."""
    if not HAS_DIR_FDS or not root.is_absolute() or ".." in root.parts:
        raise OSError("Cannot anchor this repository filesystem")
    fd = os.open(root.anchor, DIR_FLAGS)
    try:
        components = (*root.parts[1:], *parts)
        for index, component in enumerate(components):
            flags = DIR_FLAGS
            if index < len(components) - 1:
                flags |= getattr(os, "O_PATH", 0)
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


def read_inventory_text(
    root: Path, relative: str, limit: int = MAX_FILE_SIZE
) -> str | None:
    """Read bounded UTF-8 from an anchored regular file, refusing links."""
    parts = tuple(relative.split("/"))
    if any(part in ("", ".", "..") or "\0" in part for part in parts):
        raise OSError("Expected a repository-relative inventory file")
    if os.name == "nt":
        with _windows_fs.open_file(root, parts) as stream:
            return _read_utf8(stream, limit)
    with open_directory(root, parts[:-1]) as parent:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        fd = os.open(parts[-1], flags, dir_fd=parent)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError("Inventory file is no longer a regular file")
            return _read_utf8(stream, limit)
