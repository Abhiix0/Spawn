"""Regression tests for Issue 1: doctor --fix symlink write-escape prevention.

Covers:
- Symlink pointing outside the project root is rejected.
- Dangling symlink is rejected.
- Nested symlink that escapes is rejected.
- Safe symlink inside the root is allowed.
- Normal (non-symlink) paths continue to work.
"""

from __future__ import annotations

import os
import sys

import pytest

from spawn.core.exceptions import FilesystemError
from spawn.utils.doctor_fix import _safe_write_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_symlink(link: "os.PathLike[str]", target: "os.PathLike[str]") -> None:
    """Create a symlink, skipping on Windows if privileges are absent."""
    try:
        os.symlink(target, link)
    except (NotImplementedError, OSError) as e:
        if sys.platform == "win32" and "privilege" in str(e).lower():
            pytest.skip(
                f"Symlink creation requires elevated privileges on Windows: {e}"
            )
        raise


# ---------------------------------------------------------------------------
# Normal paths — must succeed
# ---------------------------------------------------------------------------


def test_safe_write_path_normal_file(tmp_path):
    """A plain filename with no symlinks returns a resolved path inside root."""
    result = _safe_write_path(tmp_path, "README.md")
    assert result.is_relative_to(tmp_path.resolve())


def test_safe_write_path_nested_normal(tmp_path):
    """A nested path with no symlinks is accepted."""
    result = _safe_write_path(tmp_path, ".github/workflows/ci.yml")
    assert result.is_relative_to(tmp_path.resolve())


# ---------------------------------------------------------------------------
# Symlink pointing outside the project root — must be rejected
# ---------------------------------------------------------------------------


def test_symlink_escaping_root_rejected(tmp_path):
    """A symlink inside the project that points outside must be rejected."""
    outside = tmp_path.parent / "outside_target.txt"
    outside.write_text("secret", encoding="utf-8")

    link = tmp_path / ".gitignore"
    _make_symlink(link, outside)

    with pytest.raises(
        FilesystemError, match="escapes the project root|outside the project root"
    ):
        _safe_write_path(tmp_path, ".gitignore")


def test_nested_symlink_escaping_root_rejected(tmp_path):
    """A directory component that is a symlink pointing outside must be rejected."""
    outside_dir = tmp_path.parent / "outside_dir"
    outside_dir.mkdir()

    link_dir = tmp_path / "subdir"
    _make_symlink(link_dir, outside_dir)

    with pytest.raises(
        FilesystemError, match="escapes the project root|outside the project root"
    ):
        _safe_write_path(tmp_path, "subdir/secrets.txt")


# ---------------------------------------------------------------------------
# Dangling symlink — must be rejected
# ---------------------------------------------------------------------------


def test_dangling_symlink_rejected(tmp_path):
    """A symlink pointing to a non-existent target must be rejected."""
    link = tmp_path / ".gitignore"
    _make_symlink(link, tmp_path / "nonexistent_target")

    with pytest.raises(FilesystemError, match="dangling symlink"):
        _safe_write_path(tmp_path, ".gitignore")


# ---------------------------------------------------------------------------
# Safe symlink inside the root — must succeed
# ---------------------------------------------------------------------------


def test_symlink_inside_root_allowed(tmp_path):
    """A symlink that stays within the project root must be accepted."""
    real_file = tmp_path / "real_readme.md"
    real_file.write_text("# Real", encoding="utf-8")

    link = tmp_path / "README.md"
    _make_symlink(link, real_file)

    # Should not raise — the symlink resolves inside the root.
    result = _safe_write_path(tmp_path, "README.md")
    assert result.is_relative_to(tmp_path.resolve())


# ---------------------------------------------------------------------------
# plan_fixes / apply_fixes integration: symlink escape is caught as "failed"
# ---------------------------------------------------------------------------


def test_plan_apply_symlink_escape_reports_failed(tmp_path):
    """apply_fixes must report status='failed' when the target escapes the root."""
    outside = tmp_path.parent / "escape_target.md"
    outside.write_text("owned by OS", encoding="utf-8")

    project = tmp_path / "project"
    project.mkdir()

    link = project / "README.md"
    _make_symlink(link, outside)

    from spawn.utils.doctor import ProjectHealthChecker
    from spawn.utils.doctor_fix import apply_fixes, plan_fixes

    checker = ProjectHealthChecker(project)
    checks = checker.run_all_checks()
    actions, _ = plan_fixes(project, checks, license_kind=None)

    readme_actions = [a for a in actions if a.check == "README.md"]
    # README.md already "exists" as a symlink so the checker sees it as present —
    # the action may not exist.  If it does exist, it must fail safely.
    if readme_actions:
        results = apply_fixes(readme_actions)
        for r in results:
            assert r.status in ("failed", "skipped")
        # The outside file must be unmodified.
        assert outside.read_text(encoding="utf-8") == "owned by OS"
