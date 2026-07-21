import subprocess
from unittest.mock import patch

import pytest

from spawn.core.exceptions import SpawnError
from spawn.utils.uv import initialize_uv, install_packages


def _make_called_process_error(stderr: str) -> subprocess.CalledProcessError:
    exc = subprocess.CalledProcessError(
        returncode=1,
        cmd=["uv", "init", "--bare"],
    )
    exc.stderr = stderr
    return exc


@patch("subprocess.run")
def test_uv_stderr_included_in_spawn_error(mock_run, tmp_path):
    mock_run.side_effect = _make_called_process_error(
        "error: Python 3.12 not found"
    )

    with pytest.raises(SpawnError) as exc_info:
        initialize_uv(tmp_path)

    assert "Python 3.12 not found" in str(exc_info.value)


@patch("subprocess.run")
def test_uv_empty_stderr_uses_fallback_message(mock_run, tmp_path):
    mock_run.side_effect = _make_called_process_error("")

    with pytest.raises(SpawnError) as exc_info:
        initialize_uv(tmp_path)

    assert str(exc_info.value) == "Failed to initialize UV environment."


@patch("subprocess.run")
def test_uv_exception_is_chained(mock_run, tmp_path):
    original = _make_called_process_error("disk full")
    mock_run.side_effect = original

    with pytest.raises(SpawnError) as exc_info:
        initialize_uv(tmp_path)

    assert exc_info.value.__cause__ is original


# ─── install_packages — dev flag ──────────────────────────────────────────


@patch("subprocess.run")
def test_install_packages_dev_flag_appends_dev_arg(mock_run, tmp_path):
    """When dev=True, '--dev' must appear in the subprocess command."""
    mock_run.return_value = None
    install_packages(tmp_path, ["ruff", "pytest"], dev=True)

    called_cmd = mock_run.call_args[0][0]
    assert "--dev" in called_cmd
    assert "ruff" in called_cmd
    assert "pytest" in called_cmd


@patch("subprocess.run")
def test_install_packages_dev_flag_absent_by_default(mock_run, tmp_path):
    """When dev is omitted (default False), '--dev' must NOT appear in the command."""
    mock_run.return_value = None
    install_packages(tmp_path, ["requests"])

    called_cmd = mock_run.call_args[0][0]
    assert "--dev" not in called_cmd
    assert "requests" in called_cmd


@patch("subprocess.run")
def test_install_packages_existing_callers_unaffected(mock_run, tmp_path):
    """Positional call install_packages(path, packages) still works with no third arg."""
    mock_run.return_value = None
    install_packages(tmp_path, ["fastapi", "uvicorn"])

    mock_run.assert_called_once()
    called_cmd = mock_run.call_args[0][0]
    assert called_cmd[:2] == ["uv", "add"]
    assert "fastapi" in called_cmd
    assert "uvicorn" in called_cmd
    assert "--dev" not in called_cmd
