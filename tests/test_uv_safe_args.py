"""Regression tests for Issue 10: safe uv argument handling.

Ensures that option-like dependency values are separated from uv flags
using '--' so they cannot be misinterpreted as uv command-line flags.
"""

from __future__ import annotations

from unittest.mock import patch

from spawn.utils.uv import install_packages


def _captured_cmd(mock_run) -> list[str]:
    return mock_run.call_args[0][0]


# ---------------------------------------------------------------------------
# '--' separator is always present between uv flags and packages
# ---------------------------------------------------------------------------


@patch("subprocess.run")
def test_separator_present_for_normal_packages(mock_run, tmp_path):
    mock_run.return_value = None
    install_packages(tmp_path, ["requests", "fastapi"])
    cmd = _captured_cmd(mock_run)
    assert "--" in cmd
    sep_idx = cmd.index("--")
    assert "requests" in cmd[sep_idx:]
    assert "fastapi" in cmd[sep_idx:]


@patch("subprocess.run")
def test_separator_present_with_dev_flag(mock_run, tmp_path):
    mock_run.return_value = None
    install_packages(tmp_path, ["pytest"], dev=True)
    cmd = _captured_cmd(mock_run)
    assert "--dev" in cmd
    assert "--" in cmd
    # '--' must come after '--dev'
    dev_idx = cmd.index("--dev")
    sep_idx = cmd.index("--", dev_idx + 1)
    assert cmd[sep_idx] == "--"
    assert "pytest" in cmd[sep_idx:]


# ---------------------------------------------------------------------------
# Option-like dependency values cannot be mis-parsed as uv flags
# ---------------------------------------------------------------------------


@patch("subprocess.run")
def test_option_like_package_treated_as_positional(mock_run, tmp_path):
    """An option-looking value must appear *after* '--' so uv treats it as a
    package specifier, not a flag."""
    mock_run.return_value = None
    install_packages(tmp_path, ["--index-url=https://pypi.org/simple/"])
    cmd = _captured_cmd(mock_run)
    sep_idx = cmd.index("--")
    # The suspicious value must come after the separator.
    assert "--index-url=https://pypi.org/simple/" in cmd[sep_idx + 1 :]


@patch("subprocess.run")
def test_single_hyphen_package_treated_as_positional(mock_run, tmp_path):
    mock_run.return_value = None
    install_packages(tmp_path, ["-e", "git+https://github.com/example/pkg"])
    cmd = _captured_cmd(mock_run)
    sep_idx = cmd.index("--")
    tail = cmd[sep_idx + 1 :]
    assert "-e" in tail


# ---------------------------------------------------------------------------
# Command structure invariants still hold
# ---------------------------------------------------------------------------


@patch("subprocess.run")
def test_command_starts_with_uv_add(mock_run, tmp_path):
    mock_run.return_value = None
    install_packages(tmp_path, ["black"])
    cmd = _captured_cmd(mock_run)
    assert cmd[0] == "uv"
    assert cmd[1] == "add"


@patch("subprocess.run")
def test_empty_packages_skips_subprocess(mock_run, tmp_path):
    install_packages(tmp_path, [])
    mock_run.assert_not_called()


@patch("subprocess.run")
def test_dev_true_includes_dev_before_separator(mock_run, tmp_path):
    mock_run.return_value = None
    install_packages(tmp_path, ["mypy"], dev=True)
    cmd = _captured_cmd(mock_run)
    dev_idx = cmd.index("--dev")
    sep_idx = cmd.index("--", dev_idx + 1)
    assert dev_idx < sep_idx


@patch("subprocess.run")
def test_dev_false_no_dev_flag(mock_run, tmp_path):
    mock_run.return_value = None
    install_packages(tmp_path, ["requests"], dev=False)
    cmd = _captured_cmd(mock_run)
    assert "--dev" not in cmd
