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
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Iterable

from spawn.inspection._git_exclusions import root_exclusions
from spawn.inspection._reading import DIR_FLAGS, HAS_DIR_FDS, open_directory
from spawn.inspection.exceptions import InspectionError
from spawn.inspection.models import Diagnostic, DiscoveryInventory, InspectionTarget

if os.name == "nt":
    from spawn.inspection import _windows_fs


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
_USE_DIR_FDS = os.scandir in os.supports_fd and HAS_DIR_FDS


def validate_inspection_root(root: str | Path | InspectionTarget) -> InspectionTarget:
    """Resolve and verify a readable directory, or raise ``InspectionError``.

    A symlink supplied as the root is resolved once and its destination becomes
    the approved root.  Descendant symlinks are *never* followed.
    """
    try:
        # Never re-resolve a previously approved root. A replacement link
        # must be refused by the handle open, not become the new root.
        resolved = (
            root.path
            if isinstance(root, InspectionTarget)
            else Path(root).resolve(strict=True)
        )
        if _USE_DIR_FDS:
            with open_directory(resolved) as fd, os.scandir(fd):
                pass
        elif os.name == "nt":
            _windows_fs.check_directory(resolved)
        else:
            raise OSError("Cannot anchor this repository filesystem")
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        raise InspectionError(
            "Cannot access inspection root. Check that the path names a readable directory."
        ) from exc
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
def _directory_entries(root: Path, parts: tuple[str, ...], root_fd: int | None):
    """List one directory without following links (fd anchored when possible)."""
    if root_fd is not None:
        fd = os.dup(root_fd)
        try:
            for name in parts:
                try:
                    next_fd = os.open(name, DIR_FLAGS, dir_fd=fd)
                except OSError as exc:
                    # On Linux O_DIRECTORY | O_NOFOLLOW can report ENOTDIR
                    # (not ELOOP) when a directory is swapped for a symlink.
                    # Recheck without following it so the diagnostic is useful.
                    if exc.errno == errno.ENOTDIR:
                        try:
                            mode = os.stat(
                                name, dir_fd=fd, follow_symlinks=False
                            ).st_mode
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
    elif os.name == "nt":
        yield _windows_fs.list_directory(root, parts)
    else:
        raise OSError("Cannot anchor this repository filesystem")


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
    The default also prunes literal top-level Git-local directory exclusions
    when a supported index confirms they contain no tracked paths.

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
    with ExitStack() as stack:
        if _USE_DIR_FDS:
            try:
                root_fd = stack.enter_context(open_directory(target.path))
            except OSError as exc:
                raise InspectionError("Cannot open inspection root.") from exc
        while pending:
            parts = pending.pop()
            rel_dir = "/".join(parts)
            try:
                with _directory_entries(target.path, parts, root_fd) as entries:
                    local_excluded = (
                        root_exclusions(target.path)
                        if excluded_directories is None
                        and not parts
                        and any(entry.name == ".git" for entry in entries)
                        else set()
                    )
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
                                if (
                                    entry.name.casefold() in excluded
                                    or entry.name in local_excluded
                                ):
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
                    raise InspectionError("Cannot scan inspection root.") from exc
                skipped.append(rel_dir)
                diagnostics.append(_diagnostic(exc, rel_dir))
    return DiscoveryInventory(
        files=tuple(sorted(files)),
        directories=tuple(sorted(directories)),
        skipped=tuple(sorted(set(skipped))),
        diagnostics=tuple(sorted(diagnostics, key=lambda d: (d.path or "", d.code))),
    )
