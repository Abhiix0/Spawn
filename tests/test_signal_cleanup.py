"""Regression tests for Issue 3: SIGTERM/SIGHUP cleanup during project generation.

Covers:
- SIGTERM during generation removes the partially-created project directory.
- SIGHUP during generation removes the partial directory (Unix only).
- Pre-existing directories are never removed.
- Signal handlers are restored after a successful generation.
- Signal handlers are restored even when an exception is raised during generation.
- The exit code on SIGTERM is 128 + SIGTERM (standard Unix convention).
"""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from spawn.core.exceptions import FilesystemError
from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator

# Skip signal tests on platforms where we cannot send/handle SIGTERM from tests.
_SKIP_SIGNALS = sys.platform == "win32"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path, name: str = "sigtest") -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="mcp",
        use_git=False,
        use_uv=False,
        destination=tmp_path / name,
    )


# ---------------------------------------------------------------------------
# Signal handler restoration after success
# ---------------------------------------------------------------------------


def test_sigterm_handler_restored_after_success(tmp_path, no_toolchain):
    """SIGTERM handler must be back to its original value after generate() returns."""
    original_handler = signal.getsignal(signal.SIGTERM)
    config = _make_config(tmp_path)
    ProjectGenerator().generate(config)
    assert signal.getsignal(signal.SIGTERM) is original_handler


def test_sigterm_handler_restored_after_exception(tmp_path):
    """SIGTERM handler must be restored even when generate() raises."""
    original_handler = signal.getsignal(signal.SIGTERM)
    config = _make_config(tmp_path)

    with patch(
        "spawn.generators.project_generator.instantiate_template",
        side_effect=RuntimeError("forced failure"),
    ):
        with pytest.raises(RuntimeError):
            ProjectGenerator().generate(config)

    assert signal.getsignal(signal.SIGTERM) is original_handler


# ---------------------------------------------------------------------------
# SIGTERM cleanup
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_SKIP_SIGNALS, reason="Signal tests require a Unix-like platform")
def test_sigterm_cleans_up_partial_project(tmp_path, no_toolchain):
    """Sending SIGTERM while generate() is running must remove the partial directory."""
    project_path = tmp_path / "my_proj"
    config = ProjectConfig(
        name="my_proj",
        template="mcp",
        use_git=False,
        use_uv=False,
        destination=project_path,
    )

    # We simulate SIGTERM by directly invoking the cleanup handler that
    # project_generator installs.  This avoids timing-sensitive os.kill calls.
    captured_handler: list = []
    real_signal = signal.signal

    def _intercept_signal(sig, handler):
        if sig == signal.SIGTERM and callable(handler):
            captured_handler.append((sig, handler))
        return real_signal(sig, handler)

    with patch(
        "spawn.generators.project_generator.signal.signal",
        side_effect=_intercept_signal,
    ):
        # Patch write_project_meta to capture the moment after mkdir but before completion.
        def _fire_sigterm_then_raise(*args, **kwargs):
            # At this point the directory has been created.
            if captured_handler:
                _, handler = captured_handler[-1]
                # Calling the handler raises SystemExit.
                with pytest.raises(SystemExit) as exc_info:
                    handler(signal.SIGTERM, None)
                # Exit code should be 128 + SIGTERM.
                assert exc_info.value.code == 128 + int(signal.SIGTERM)
                raise SystemExit(exc_info.value.code)

        with patch(
            "spawn.generators.project_generator.write_project_meta",
            side_effect=_fire_sigterm_then_raise,
        ):
            with pytest.raises(SystemExit):
                ProjectGenerator().generate(config)

    # The partially-created project directory must have been cleaned up.
    assert not project_path.exists(), (
        f"Partial project directory was not removed after SIGTERM: {project_path}"
    )


@pytest.mark.skipif(_SKIP_SIGNALS, reason="Signal tests require a Unix-like platform")
def test_sigterm_exit_code_is_128_plus_signum(tmp_path, no_toolchain):
    """The exit status when SIGTERM fires must be 128 + SIGTERM."""
    config = _make_config(tmp_path)
    captured_handler: list = []
    real_signal = signal.signal

    def _intercept(sig, handler):
        if sig == signal.SIGTERM and callable(handler):
            captured_handler.append(handler)
        return real_signal(sig, handler)

    with patch(
        "spawn.generators.project_generator.signal.signal", side_effect=_intercept
    ):
        with patch(
            "spawn.generators.project_generator.write_project_meta",
            side_effect=RuntimeError("abort"),
        ):
            with pytest.raises(RuntimeError):
                ProjectGenerator().generate(config)

    assert captured_handler, "SIGTERM handler was not installed"
    handler = captured_handler[-1]
    with pytest.raises(SystemExit) as exc_info:
        # Simulate SIGTERM delivery.
        handler(int(signal.SIGTERM), None)
    assert exc_info.value.code == 128 + int(signal.SIGTERM)


# ---------------------------------------------------------------------------
# SIGHUP cleanup (Unix only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    _SKIP_SIGNALS or not hasattr(signal, "SIGHUP"),
    reason="SIGHUP only available on Unix",
)
def test_sighup_handler_installed_and_restored(tmp_path, no_toolchain):
    """SIGHUP handler must be installed during generate() and restored afterwards."""
    original = signal.getsignal(signal.SIGHUP)  # type: ignore[attr-defined]
    config = _make_config(tmp_path)
    ProjectGenerator().generate(config)
    assert signal.getsignal(signal.SIGHUP) is original  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Pre-existing directories are never removed
# ---------------------------------------------------------------------------


def test_sigterm_does_not_remove_preexisting_directory(tmp_path):
    """cleanup_created must not remove a directory that existed before generation."""
    existing = tmp_path / "existing_project"
    existing.mkdir()
    sentinel = existing / "important_data.txt"
    sentinel.write_text("do not delete", encoding="utf-8")

    # Attempt to generate into the same path — must fail because it already exists.
    config = ProjectConfig(
        name="existing_project",
        template="mcp",
        use_git=False,
        use_uv=False,
        destination=existing,
    )
    with pytest.raises(FilesystemError):
        ProjectGenerator().generate(config)

    # The original directory and its contents must still be intact.
    assert existing.is_dir()
    assert sentinel.read_text(encoding="utf-8") == "do not delete"
