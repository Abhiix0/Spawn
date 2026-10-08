"""Filesystem safety helpers shared by the project generators."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from spawn.core.exceptions import SpawnError

_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def resolve_destination(name: str, destination: Path | None = None) -> Path:
    """Return the absolute project path for *name* (cwd/name by default)."""
    if not name or name in {".", ".."} or "/" in name or "\\" in name or "\0" in name:
        raise SpawnError(
            f"Invalid project name '{name}': must be a single directory name."
        )
    base = Path.cwd() / name if destination is None else Path(destination)
    return base.resolve()


def assert_available(path: Path, message: str) -> None:
    """Raise SpawnError(message) if *path* exists in any form (incl. symlinks)."""
    if os.path.lexists(path):
        raise SpawnError(message)


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
        raise SpawnError(f"Unsafe path in project structure: {relative!r}")
    root_resolved = root.resolve()
    joined = (root / relative).resolve()
    if not joined.is_relative_to(root_resolved):
        raise SpawnError(f"Path escapes the project directory: {relative!r}")
    return root / relative


def cleanup_created(path: Path, root_guard: Path | None = None) -> None:
    """Remove *path* only if it is a real directory that is safe to delete.

    Callers must only invoke this for directories created by the current run.
    """
    if path.is_symlink() or not path.is_dir():
        return
    resolved = path.resolve()
    cwd = Path.cwd().resolve()
    if (
        resolved == resolved.parent  # filesystem root
        or resolved == Path.home().resolve()
        or resolved == cwd
        or resolved in cwd.parents
        or (root_guard is not None and resolved == root_guard.resolve())
    ):
        return
    shutil.rmtree(resolved, ignore_errors=True)
