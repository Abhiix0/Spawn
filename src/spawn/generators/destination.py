"""Filesystem safety helpers shared by the project generators."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from spawn.core.exceptions import FilesystemError, InvalidInputError

_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def resolve_destination(name: str, destination: Path | None = None) -> Path:
    """Return the absolute project path for *name* (cwd/name by default)."""
    if not name or name in {".", ".."} or "/" in name or "\\" in name or "\0" in name:
        raise InvalidInputError(
            f"Invalid project name '{name}': must be a single directory name."
        )
    base = Path.cwd() / name if destination is None else Path(destination)
    if not base.name:
        return base.resolve()
    return base.parent.resolve() / base.name


def assert_available(path: Path, message: str) -> None:
    """Raise FilesystemError(message) if *path* exists in any form (incl. symlinks)."""
    if os.path.lexists(path):
        raise FilesystemError(message)


def safe_join(root: Path, relative: str) -> Path:
    """Join *relative* onto *root*, rejecting anything that could escape it."""
    if (
        not relative
        or "\0" in relative
        or "\\" in relative
        or relative.startswith("/")
        or _DRIVE_RE.match(relative)
        or ".." in relative.split("/")
    ):
        raise FilesystemError(f"Unsafe path in project structure: {relative!r}")
    root_resolved = root.resolve()
    joined = (root / relative).resolve()
    if not joined.is_relative_to(root_resolved):
        raise FilesystemError(f"Path escapes the project directory: {relative!r}")
    return root / relative


@dataclass(frozen=True)
class OwnershipToken:
    path: Path
    dev: int
    ino: int


def record_ownership(path: Path) -> OwnershipToken:
    """Capture filesystem identity immediately after creating *path*."""
    stat = os.lstat(path)
    return OwnershipToken(path=path, dev=stat.st_dev, ino=stat.st_ino)


def cleanup_created(
    path: Path,
    root_guard: Path | None = None,
    token: OwnershipToken | None = None,
) -> None:
    """Remove *path* only if it is the exact real directory created by this run.

    Callers must only invoke this for directories created by the current run.
    """
    try:
        if os.path.islink(path) or path.is_symlink():
            return
        if getattr(path, "is_junction", lambda: False)():
            return
        if not path.is_dir():
            return

        stat = os.lstat(path)
        if token is not None:
            if stat.st_dev != token.dev or stat.st_ino != token.ino:
                return

        cwd = Path.cwd().resolve()
        path_parent = path.parent.resolve()
        path_cmp = path_parent / path.name
        home = Path.home().resolve()
        if (
            path_cmp == path_parent  # filesystem root
            or path_cmp == home
            or path_cmp == cwd
            or path_cmp in cwd.parents
            or (
                root_guard is not None
                and path_cmp == (root_guard.parent.resolve() / root_guard.name)
            )
        ):
            return

        shutil.rmtree(path, ignore_errors=True)
    except OSError:
        return
