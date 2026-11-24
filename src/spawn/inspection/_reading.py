"""Bounded, read-only text loading shared by inspection analyzers (#56)."""

from __future__ import annotations

import os
import stat
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
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
_CACHE_ENTRIES = 4096
_CACHE_BYTES = 8 * 1024 * 1024


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
        with _open_descendant(fd, (*root.parts[1:], *parts)) as directory:
            yield directory
    finally:
        os.close(fd)


@contextmanager
def _open_descendant(parent: int, parts: tuple[str, ...]):
    fd = parent
    try:
        for index, component in enumerate(parts):
            flags = DIR_FLAGS
            if index < len(parts) - 1:
                flags |= getattr(os, "O_PATH", 0)
            next_fd = os.open(component, flags, dir_fd=fd)
            if fd != parent:
                os.close(fd)
            fd = next_fd
        yield fd
    finally:
        if fd != parent:
            os.close(fd)


def _open_root(root: Path):
    return _windows_fs.open_root(root) if os.name == "nt" else open_directory(root)


@contextmanager
def _open_file(handle: int, parts: tuple[str, ...]):
    if os.name == "nt":
        with _windows_fs.open_file(handle, parts) as stream:
            yield stream
    else:
        with _open_descendant(handle, parts[:-1]) as parent:
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            fd = os.open(parts[-1], flags, dir_fd=parent)
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise OSError("Inventory file is no longer a regular file")
                yield stream


def _read_from_root(handle: int, parts: tuple[str, ...], limit: int) -> str | None:
    with _open_file(handle, parts) as stream:
        return _read_utf8(stream, limit)


class _InspectionReads:
    def __init__(self, root: Path, stack: ExitStack):
        self.root = root
        self.stack = stack
        self.handle: int | None = None
        self.cache: dict[tuple[str, int], str | None] = {}
        self.remaining = _CACHE_BYTES

    def read(self, relative: str, parts: tuple[str, ...], limit: int) -> str | None:
        key = (relative, limit)
        if key in self.cache:
            return self.cache[key]
        if self.handle is None:
            self.handle = self.stack.enter_context(_open_root(self.root))
        text = _read_from_root(self.handle, parts, limit)
        # Charge for up to four bytes per Unicode character. Also bound the
        # number of keys so empty and oversized files can't grow the cache.
        size = 4 * len(text or "")
        if size <= self.remaining and len(self.cache) < _CACHE_ENTRIES:
            self.remaining -= size
            self.cache[key] = text
        return text


_ACTIVE_READS = ContextVar[_InspectionReads | None]("inspection_reads", default=None)


@contextmanager
def repository_reads(root: Path):
    """Share bounded, successfully checked reads within one analysis."""
    with ExitStack() as stack:
        token = _ACTIVE_READS.set(_InspectionReads(root, stack))
        try:
            yield
        finally:
            _ACTIVE_READS.reset(token)


def _components(relative: str) -> tuple[str, ...]:
    parts = tuple(relative.split("/"))
    if any(part in ("", ".", "..") or "\0" in part for part in parts):
        raise OSError("Expected a repository-relative inventory file")
    return parts


def read_inventory_text(
    root: Path, relative: str, limit: int = MAX_FILE_SIZE
) -> str | None:
    """Read bounded UTF-8 from an anchored regular file, refusing links."""
    parts = _components(relative)
    reads = _ACTIVE_READS.get()
    if reads is not None and reads.root == root:
        return reads.read(relative, parts, limit)
    with _open_root(root) as handle:
        return _read_from_root(handle, parts, limit)


def read_repository_bytes(root: Path, relative: str, limit: int) -> bytes | None:
    """Read a bounded binary repository resource with the same containment."""
    parts = _components(relative)
    with _open_root(root) as handle, _open_file(handle, parts) as stream:
        data = stream.read(limit + 1)
        return data if len(data) <= limit else None
