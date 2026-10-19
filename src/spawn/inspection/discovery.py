"""Read-only, deterministic repository inventory for project inspection (#54).

Directory entries are examined with ``stat(..., follow_symlinks=False)``.
File and directory symlinks are never included or followed.  On platforms
supporting directory descriptors, nested directories are opened relative to
an anchored root descriptor with ``O_NOFOLLOW`` to resist symlink-swap races.
"""

from __future__ import annotations

import errno
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

from spawn.inspection.exceptions import InspectionError
from spawn.inspection.models import Diagnostic, DiscoveryInventory, InspectionTarget


DEFAULT_EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "vendor",
        "dist",
        "build",
        "coverage",
        "htmlcov",
        "target",
        ".next",
        ".nuxt",
        ".cache",
        ".turbo",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".uv",
        ".tox",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    }
)

# Descriptor-relative opens prevent a directory from becoming an out-of-root
# symlink between an initial stat and a subsequent scandir on POSIX systems.
_USE_DIR_FDS = (
    os.scandir in os.supports_fd
    and os.open in os.supports_dir_fd
    and hasattr(os, "O_NOFOLLOW")
    and hasattr(os, "O_DIRECTORY")
)
_DIR_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)


def validate_inspection_root(root: str | Path | InspectionTarget) -> InspectionTarget:
    """Resolve and verify a readable directory, or raise ``InspectionError``.

    A symlink supplied as the root is resolved once and its destination becomes
    the approved root.  Descendant symlinks are *never* followed.
    """
    try:
        supplied = root.path if isinstance(root, InspectionTarget) else Path(root)
        resolved = supplied.resolve(strict=True)
        if not resolved.is_dir():
            raise InspectionError(f"Inspection root is not a directory: {supplied}")
        # Testing scandir, rather than os.access, handles real ACL permissions.
        with os.scandir(resolved):
            pass
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        raise InspectionError(f"Cannot access inspection root {root!s}: {exc}") from exc
    return InspectionTarget(path=resolved)


def _exclusions(names: Iterable[str] | None) -> frozenset[str]:
    # A single basename is accepted as shorthand; do not iterate its letters.
    if names is None:
        selected = DEFAULT_EXCLUDED_DIRECTORIES
    elif isinstance(names, str):
        selected = (names,)
    else:
        selected = names
    result: set[str] = set()
    for name in selected:
        if (
            not isinstance(name, str)
            or not name
            or name in {".", ".."}
            or "/" in name
            or (os.name == "nt" and "\\" in name)
            or "\0" in name
        ):
            raise ValueError(f"Excluded directory must be a single name: {name!r}")
        result.add(name.casefold())
    return frozenset(result)


@contextmanager
def _directory_entries(
    root: Path, parts: tuple[str, ...], root_fd: int | None
) -> Iterator[list[os.DirEntry[str]]]:
    """List one directory without following links (fd anchored when possible)."""
    if root_fd is not None:
        fd = os.dup(root_fd)
        try:
            for name in parts:
                try:
                    next_fd = os.open(name, _DIR_FLAGS, dir_fd=fd)
                except OSError as exc:
                    # On Linux O_DIRECTORY | O_NOFOLLOW can report ENOTDIR
                    # (not ELOOP) when a directory is swapped for a symlink.
                    # Recheck without following it so the diagnostic is useful.
                    if exc.errno == errno.ENOTDIR:
                        try:
                            mode = os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
                        except OSError:
                            pass
                        else:
                            if stat.S_ISLNK(mode):
                                raise OSError(
                                    errno.ELOOP, "Directory became a symlink", name
                                ) from exc
                    raise
                os.close(fd)
                fd = next_fd
            with os.scandir(fd) as entries:
                yield sorted(entries, key=lambda entry: entry.name)
        finally:
            os.close(fd)
    else:
        directory = root.joinpath(*parts)
        # Portable fallback (not race-proof against malicious concurrent edits).
        if directory.is_symlink() or (
            hasattr(directory, "is_junction") and directory.is_junction()
        ):
            raise OSError(errno.ELOOP, "Directory became a link", str(directory))
        resolved = directory.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise OSError(errno.EPERM, "Directory escapes inspection root", str(directory))
        with os.scandir(directory) as entries:
            yield sorted(entries, key=lambda entry: entry.name)


def _diagnostic(exc: OSError, path: str) -> Diagnostic:
    if exc.errno in (errno.EACCES, errno.EPERM):
        code = "discovery.permission_denied"
    elif exc.errno in (errno.ENOENT, errno.ENOTDIR):
        code = "discovery.entry_disappeared"
    elif exc.errno == errno.ELOOP:
        code = "discovery.symlink_race"
    else:
        code = "discovery.filesystem_error"
    return Diagnostic(
        code=code,
        message=f"Unable to inspect {path}: {exc.strerror or str(exc)}",
        severity="warning",
        source="discovery",
        path=path,
    )


def discover_repository(
    root: str | Path | InspectionTarget,
    *,
    excluded_directories: Iterable[str] | None = None,
) -> DiscoveryInventory:
    """Return a sorted ``DiscoveryInventory`` using the approved #53 model.

    ``excluded_directories=None`` uses the default ignore set; passing an
    iterable *replaces* it (pass ``()`` to disable default exclusions).
    Exclusions match directory basenames case-insensitively at any depth.

    The root must be readable; invalid roots raise ``InspectionError``. Errors
    below the root are recoverable and become ``Diagnostic`` entries. Deliberate
    exclusions are listed in ``skipped`` without diagnostics: treating normal
    ignore rules as failures would incorrectly mark every Git repository PARTIAL.
    """
    excluded = _exclusions(excluded_directories)
    target = validate_inspection_root(root)
    files: list[str] = []
    directories: list[str] = []
    skipped: list[str] = []
    diagnostics: list[Diagnostic] = []
    pending: list[tuple[str, ...]] = [()]
    root_fd: int | None = None
    try:
        if _USE_DIR_FDS:
            try:
                root_fd = os.open(target.path, _DIR_FLAGS)
            except OSError as exc:
                raise InspectionError(f"Cannot open inspection root: {exc}") from exc
        while pending:
            parts = pending.pop()
            rel_dir = "/".join(parts)
            try:
                with _directory_entries(target.path, parts, root_fd) as entries:
                    child_directories: list[tuple[str, ...]] = []
                    for entry in entries:
                        child_parts = (*parts, entry.name)
                        rel_path = "/".join(child_parts)
                        try:
                            mode = entry.stat(follow_symlinks=False).st_mode
                            if stat.S_ISLNK(mode):
                                skipped.append(rel_path)
                                diagnostics.append(
                                    Diagnostic(
                                        code="discovery.symlink_skipped",
                                        message=f"Symbolic link not followed: {rel_path}",
                                        severity="info",
                                        source="discovery",
                                        path=rel_path,
                                    )
                                )
                            elif stat.S_ISDIR(mode):
                                # Junctions are not always reported as symlinks.
                                absolute = target.path.joinpath(*child_parts)
                                if hasattr(absolute, "is_junction") and absolute.is_junction():
                                    skipped.append(rel_path)
                                    diagnostics.append(
                                        Diagnostic(
                                            code="discovery.symlink_skipped",
                                            message=f"Directory junction not followed: {rel_path}",
                                            severity="info",
                                            source="discovery",
                                            path=rel_path,
                                        )
                                    )
                                elif entry.name.casefold() in excluded:
                                    skipped.append(rel_path)
                                else:
                                    directories.append(rel_path)
                                    child_directories.append(child_parts)
                            elif stat.S_ISREG(mode):
                                files.append(rel_path)
                            else:
                                skipped.append(rel_path)
                                diagnostics.append(
                                    Diagnostic(
                                        code="discovery.unsupported_entry_type",
                                        message=f"Unsupported filesystem entry skipped: {rel_path}",
                                        severity="warning",
                                        source="discovery",
                                        path=rel_path,
                                    )
                                )
                        except OSError as exc:
                            skipped.append(rel_path)
                            diagnostics.append(_diagnostic(exc, rel_path))
                    # LIFO pending stack: push reverse-sorted dirs for lexical DFS.
                    pending.extend(reversed(child_directories))
            except OSError as exc:
                if not parts:
                    raise InspectionError(f"Cannot scan inspection root: {exc}") from exc
                skipped.append(rel_dir)
                diagnostics.append(_diagnostic(exc, rel_dir))
    finally:
        if root_fd is not None:
            os.close(root_fd)

    return DiscoveryInventory(
        files=tuple(sorted(files)),
        directories=tuple(sorted(directories)),
        skipped=tuple(sorted(set(skipped))),
        diagnostics=tuple(sorted(diagnostics, key=lambda d: (d.path or "", d.code))),
    )
