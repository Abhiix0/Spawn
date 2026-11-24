"""Bounded, read-only text loading shared by inspection analyzers (#56)."""

from __future__ import annotations

import os
import stat
from contextlib import ExitStack
from pathlib import Path
from typing import BinaryIO

MAX_FILE_SIZE = 1_000_000


def read_text_limited(path: Path, limit: int = MAX_FILE_SIZE) -> str | None:
    """Read at most ``limit + 1`` bytes; return None when the file exceeds ``limit``.

    Decodes strictly as UTF-8 (a BOM is accepted). Raises ``OSError`` when the
    file cannot be read and ``UnicodeDecodeError`` when it is not UTF-8; other
    encodings are never guessed.
    """
    with path.open("rb") as fh:
        return _read_utf8(fh, limit)


def _read_utf8(fh: BinaryIO, limit: int) -> str | None:
    data = fh.read(limit + 1)
    if len(data) > limit:
        return None
    return data.decode("utf-8-sig")


def read_inventory_text(root: Path, relative: str) -> str | None:
    """Read an inventory file, refusing links and nonregular files.

    POSIX descriptor-relative opens also prevent descendant link swaps.
    On other platforms the checks assume the tree is stable during the read.
    """
    parts = relative.split("/")
    if any(
        part in ("", ".", "..") or any(c in part for c in ("\\", ":", "\0"))
        for part in parts
    ):
        raise ValueError("Expected a repository-relative inventory file")

    if (
        os.open in os.supports_dir_fd
        and hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "O_DIRECTORY")
    ):
        flags = os.O_RDONLY | os.O_NOFOLLOW
        with ExitStack() as stack:
            fd = os.open(root, flags | os.O_DIRECTORY)
            stack.callback(os.close, fd)
            for part in parts[:-1]:
                fd = os.open(part, flags | os.O_DIRECTORY, dir_fd=fd)
                stack.callback(os.close, fd)
            fd = os.open(parts[-1], flags | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(fd, "rb") as fh:
                if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
                    raise OSError("Inventory file is no longer a regular file")
                return _read_utf8(fh, MAX_FILE_SIZE)

    path = root
    for index, part in enumerate(parts):
        path /= part
        info = path.lstat()
        expected = stat.S_ISREG if index == len(parts) - 1 else stat.S_ISDIR
        if not expected(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise OSError("Inventory path is no longer a regular file or directory")
    return read_text_limited(path)
