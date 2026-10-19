"""Filesystem fixtures for Issue #54; no project code is executed."""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from spawn.inspection import DiscoveryInventory, InspectionError, InspectionTarget
from spawn.inspection import discovery
from spawn.inspection.discovery import (
    DEFAULT_EXCLUDED_DIRECTORIES,
    discover_repository,
    validate_inspection_root,
)


def _file(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_valid_root_returns_resolved_target(tmp_path):
    target = validate_inspection_root(tmp_path / ".")
    assert isinstance(target, InspectionTarget)
    assert target.path == tmp_path.resolve()
    assert target.path.is_absolute()


@pytest.mark.parametrize("bad_path", ["missing", "regular.txt"])
def test_invalid_root_rejected(tmp_path, bad_path):
    (tmp_path / "regular.txt").write_text("x")
    with pytest.raises(InspectionError, match="root"):
        discover_repository(tmp_path / bad_path)


def test_root_symlink_loop_is_rejected_cleanly(tmp_path):
    loop = tmp_path / "loop"
    _symlink(loop, loop, directory=True)
    with pytest.raises(InspectionError, match="Cannot access inspection root"):
        discover_repository(loop)


def test_unreadable_root_rejected(tmp_path, monkeypatch):
    real_scandir = discovery.os.scandir

    def denial(path):
        if Path(path) == tmp_path:
            raise PermissionError(errno.EACCES, "Access denied")
        return real_scandir(path)

    monkeypatch.setattr(discovery.os, "scandir", denial)
    with pytest.raises(InspectionError, match="Cannot access"):
        discover_repository(tmp_path)


def test_empty_repository(tmp_path):
    inventory = discover_repository(tmp_path)
    assert inventory == DiscoveryInventory((), (), (), ())


def test_normalized_paths_and_deterministic_order(tmp_path):
    for name in ("z.py", "one/two/x.py", "one/a.txt", "B/test.py", "école/💫 wow.py"):
        _file(tmp_path / name)
    first = discover_repository(tmp_path)
    assert first.files == (
        "B/test.py",
        "one/a.txt",
        "one/two/x.py",
        "z.py",
        "école/💫 wow.py",
    )
    assert first.directories == ("B", "one", "one/two", "école")
    assert first.skipped == ()
    assert first.diagnostics == ()
    assert all(
        not item.startswith(("/", "./")) and "\\" not in item
        for item in (*first.files, *first.directories)
    )
    assert all(discover_repository(tmp_path) == first for _ in range(4))


def test_default_exclusions_at_all_depths(tmp_path):
    for ignored in DEFAULT_EXCLUDED_DIRECTORIES:
        _file(tmp_path / ignored / "nested" / "secret.py")
        _file(tmp_path / "src" / ignored / "secret.py")
    _file(tmp_path / "src" / "main.py")
    inventory = discover_repository(tmp_path)
    assert inventory.files == ("src/main.py",)
    assert inventory.directories == ("src",)
    assert len(inventory.skipped) == 2 * len(DEFAULT_EXCLUDED_DIRECTORIES)
    assert set(inventory.skipped) == (
        set(DEFAULT_EXCLUDED_DIRECTORIES)
        | {f"src/{item}" for item in DEFAULT_EXCLUDED_DIRECTORIES}
    )
    assert inventory.diagnostics == ()


def test_exclusion_names_follow_spawn_gitignore_conventions(tmp_path):
    for directory in (
        "venv",
        "env",
        ".uv",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "htmlcov",
        ".tox",
        ".nox",
    ):
        _file(tmp_path / directory / "ignored.py")
        assert directory in DEFAULT_EXCLUDED_DIRECTORIES
    _file(tmp_path / "src" / "main.py")
    result = discover_repository(tmp_path)
    assert result.files == ("src/main.py",)
    assert result.directories == ("src",)
    assert set(result.skipped) == {
        "venv",
        "env",
        ".uv",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "htmlcov",
        ".tox",
        ".nox",
    }


def test_custom_exclusions_replace_defaults(tmp_path):
    _file(tmp_path / "node_modules" / "a.js")
    _file(tmp_path / "PRIVATE" / "secret.txt")
    inventory = discover_repository(tmp_path, excluded_directories=("private",))
    assert inventory.files == ("node_modules/a.js",)
    assert inventory.directories == ("node_modules",)
    assert inventory.skipped == ("PRIVATE",)
    assert discover_repository(tmp_path, excluded_directories=()).skipped == ()


def test_single_custom_exclusion_name_is_not_split_into_letters(tmp_path):
    _file(tmp_path / "vendor" / "a.txt")
    _file(tmp_path / "v" / "b.txt")
    result = discover_repository(tmp_path, excluded_directories="vendor")
    assert result.files == ("v/b.txt",)
    assert result.skipped == ("vendor",)


@pytest.mark.parametrize("bad", ["", "..", ".", "a/b", "\0"])
def test_invalid_exclusions_rejected(tmp_path, bad):
    with pytest.raises(ValueError, match="single name"):
        discover_repository(tmp_path, excluded_directories=[bad])


def test_accepts_inspection_target(tmp_path):
    _file(tmp_path / "a.txt")
    assert discover_repository(validate_inspection_root(tmp_path)).files == ("a.txt",)


def _symlink(link: Path, target: Path, *, directory: bool = False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlinks unavailable: {exc}")


def test_file_symlink_never_in_inventory(tmp_path):
    _file(tmp_path / "inside.txt")
    _symlink(tmp_path / "linked.txt", tmp_path / "inside.txt")
    inventory = discover_repository(tmp_path)
    assert inventory.files == ("inside.txt",)
    assert inventory.skipped == ("linked.txt",)
    assert [d.code for d in inventory.diagnostics] == ["discovery.symlink_skipped"]


def test_directory_symlink_outside_root_not_followed(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    _file(tmp_path / "outside" / "secret.txt")
    _symlink(root / "escape", tmp_path / "outside", directory=True)
    inventory = discover_repository(root)
    assert inventory.files == ()
    assert inventory.directories == ()
    assert inventory.skipped == ("escape",)


def test_internal_directory_symlink_not_followed(tmp_path):
    _file(tmp_path / "real" / "file.txt")
    _symlink(tmp_path / "alias", tmp_path / "real", directory=True)
    inventory = discover_repository(tmp_path)
    assert inventory.directories == ("real",)
    assert inventory.files == ("real/file.txt",)
    assert inventory.skipped == ("alias",)


def test_broken_and_loop_symlinks_do_not_crash(tmp_path):
    _symlink(tmp_path / "broken", tmp_path / "absent", directory=True)
    _symlink(tmp_path / "loop", tmp_path / "loop", directory=True)
    inventory = discover_repository(tmp_path)
    assert inventory.skipped == ("broken", "loop")
    assert len(inventory.diagnostics) == 2


def test_root_symlink_resolves_once(tmp_path):
    root = tmp_path / "actual"
    root.mkdir()
    _file(root / "abc.txt")
    _symlink(tmp_path / "linked", root, directory=True)
    assert discover_repository(tmp_path / "linked").files == ("abc.txt",)


def test_unreadable_child_directory_returns_partial_inventory(tmp_path, monkeypatch):
    _file(tmp_path / "a" / "one.txt")
    _file(tmp_path / "b" / "two.txt")
    real_open = discovery.os.open

    def denied_open(path, *args, **kwargs):
        if path == "a" and "dir_fd" in kwargs:
            raise PermissionError(errno.EACCES, "Access denied")
        return real_open(path, *args, **kwargs)

    if not discovery._USE_DIR_FDS:
        pytest.skip("dirfd-specific failure simulation")
    monkeypatch.setattr(discovery.os, "open", denied_open)
    inventory = discover_repository(tmp_path)
    assert inventory.files == ("b/two.txt",)
    assert inventory.directories == ("a", "b")
    assert inventory.skipped == ("a",)
    assert inventory.diagnostics[0].path == "a"
    assert inventory.diagnostics[0].code == "discovery.permission_denied"
    assert inventory.diagnostics[0].fatal is False


def test_directory_disappears_before_open(tmp_path, monkeypatch):
    (tmp_path / "gone").mkdir()
    _file(tmp_path / "safe.txt")
    if not discovery._USE_DIR_FDS:
        pytest.skip("dirfd-specific failure simulation")
    real_open = discovery.os.open

    def gone_open(path, *args, **kwargs):
        if path == "gone" and "dir_fd" in kwargs:
            raise FileNotFoundError(errno.ENOENT, "No such file")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(discovery.os, "open", gone_open)
    result = discover_repository(tmp_path)
    assert result.files == ("safe.txt",)
    assert result.skipped == ("gone",)
    assert result.diagnostics[0].code == "discovery.entry_disappeared"


def test_symlink_swap_race_does_not_traverse(tmp_path, monkeypatch):
    (tmp_path / "now_link").mkdir()
    _file(tmp_path / "ok.txt")
    if not discovery._USE_DIR_FDS:
        pytest.skip("dirfd-specific race simulation")
    real_open = discovery.os.open

    def loop_open(path, *args, **kwargs):
        if path == "now_link" and "dir_fd" in kwargs:
            raise OSError(errno.ELOOP, "Symlink loop")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(discovery.os, "open", loop_open)
    result = discover_repository(tmp_path)
    assert result.files == ("ok.txt",)
    assert result.skipped == ("now_link",)
    assert result.diagnostics[0].code == "discovery.symlink_race"


def test_unsupported_entry_type_with_fifo(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO not supported")
    os.mkfifo(tmp_path / "fifo")
    _file(tmp_path / "regular")
    result = discover_repository(tmp_path)
    assert result.files == ("regular",)
    assert result.skipped == ("fifo",)
    assert result.diagnostics[0].code == "discovery.unsupported_entry_type"


def test_no_import_execution_subprocess_or_writes(tmp_path, monkeypatch):
    import subprocess

    _file(tmp_path / "src" / "evil.py", 'raise RuntimeError("should never run")\n')
    marker = tmp_path / "marker.txt"
    _file(marker, "before")
    before = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }

    def forbidden(*args, **kwargs):
        raise AssertionError("Execution attempted")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    result = discover_repository(tmp_path)
    assert result.files == ("marker.txt", "src/evil.py")
    after = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert before == after
    assert marker.read_text() == "before"


def test_diagnostics_sorted_stably(tmp_path):
    (tmp_path / "z").symlink_to(tmp_path / "missing-z")
    (tmp_path / "a").symlink_to(tmp_path / "missing-a")
    result = discover_repository(tmp_path)
    assert [d.path for d in result.diagnostics] == ["a", "z"]
    assert all(d.source == "discovery" and not d.fatal for d in result.diagnostics)


def test_deleted_entry_during_stat_is_recorded(tmp_path, monkeypatch):
    from contextlib import contextmanager

    class VanishedEntry:
        name = "vanished.txt"

        def stat(self, *, follow_symlinks):
            assert follow_symlinks is False
            raise FileNotFoundError(errno.ENOENT, "removed during scan")

    original = discovery._directory_entries

    @contextmanager
    def disappearing(root, parts, root_fd):
        with original(root, parts, root_fd) as entries:
            if not parts:
                entries.append(VanishedEntry())
            yield entries

    monkeypatch.setattr(discovery, "_directory_entries", disappearing)
    _file(tmp_path / "still-here.txt")
    result = discover_repository(tmp_path)
    assert result.files == ("still-here.txt",)
    assert result.skipped == ("vanished.txt",)
    assert result.diagnostics[0].code == "discovery.entry_disappeared"


def test_unknown_io_failure_does_not_abort_other_subtrees(tmp_path, monkeypatch):
    from contextlib import contextmanager

    _file(tmp_path / "bad" / "ignored.txt")
    _file(tmp_path / "good" / "found.txt")
    original = discovery._directory_entries

    @contextmanager
    def failing(root, parts, root_fd):
        if parts == ("bad",):
            raise OSError(errno.EIO, "Disk IO error")
        with original(root, parts, root_fd) as entries:
            yield entries

    monkeypatch.setattr(discovery, "_directory_entries", failing)
    result = discover_repository(tmp_path)
    assert result.files == ("good/found.txt",)
    assert result.skipped == ("bad",)
    assert result.diagnostics[0].code == "discovery.filesystem_error"


def test_actual_symlink_swap_cannot_escape_on_posix(tmp_path, monkeypatch):
    """Replace a scanned directory by a symlink immediately before opening it."""
    if not discovery._USE_DIR_FDS:
        pytest.skip("O_NOFOLLOW directory descriptors not available")
    root = tmp_path / "project"
    (root / "replace").mkdir(parents=True)
    _file(tmp_path / "external" / "do-not-list.txt")
    _file(root / "safe.txt")
    real_open = discovery.os.open
    swapped = False

    def swap_open(path, *args, **kwargs):
        nonlocal swapped
        if path == "replace" and "dir_fd" in kwargs and not swapped:
            swapped = True
            (root / "replace").rmdir()
            _symlink(root / "replace", tmp_path / "external", directory=True)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(discovery.os, "open", swap_open)
    result = discover_repository(root)
    assert swapped
    assert result.files == ("safe.txt",)
    assert result.skipped == ("replace",)
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].path == "replace"
    assert result.diagnostics[0].code == "discovery.symlink_race"


def test_path_based_fallback_keeps_relative_paths_and_skips_links(tmp_path, monkeypatch):
    """Exercise the fallback used on platforms without scandir(dirfd)."""
    _file(tmp_path / "nested" / "good.txt")
    _file(tmp_path / "outside-file.txt")
    _symlink(tmp_path / "alias", tmp_path / "nested", directory=True)
    monkeypatch.setattr(discovery, "_USE_DIR_FDS", False)
    result = discover_repository(tmp_path)
    assert result.files == ("nested/good.txt", "outside-file.txt")
    assert result.directories == ("nested",)
    assert result.skipped == ("alias",)


def test_deep_nesting_is_iterative_and_stable(tmp_path):
    # Windows may not have long-path support enabled; keep its fixture short.
    depth = 30 if os.name == "nt" else 180
    path = tmp_path
    for _ in range(depth):
        path = path / "d"
        path.mkdir()
    _file(path / "leaf.txt")
    result = discover_repository(tmp_path)
    expected = "/".join(["d"] * depth)
    assert result.files == (f"{expected}/leaf.txt",)
    assert len(result.directories) == depth
    assert result.directories[-1] == expected
    assert discover_repository(tmp_path) == result


def test_unusual_but_valid_filenames_are_preserved(tmp_path):
    names = ("my project/notes [final] #1!.txt", "src/a+b @work(2).py")
    for name in names:
        _file(tmp_path / name)
    result = discover_repository(tmp_path)
    assert result.files == tuple(sorted(names))
    assert result.directories == ("my project", "src")
    assert result.diagnostics == ()


def test_posix_backslash_filename_is_preserved_as_literal(tmp_path):
    if os.name == "nt":
        pytest.skip("Backslash is a directory separator on Windows")
    _file(tmp_path / "literal\\backslash.txt")
    result = discover_repository(tmp_path)
    assert result.files == ("literal\\backslash.txt",)
    assert result.diagnostics == ()


def test_backslash_named_directory_exclusion_is_platform_aware(tmp_path):
    if os.name == "nt":
        with pytest.raises(ValueError, match="single name"):
            discover_repository(tmp_path, excluded_directories=("a\\b",))
    else:
        _file(tmp_path / "a\\b" / "secret.txt")
        result = discover_repository(tmp_path, excluded_directories=("a\\b",))
        assert result.skipped == ("a\\b",)
        assert result.files == ()
