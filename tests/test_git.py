import subprocess
from unittest.mock import MagicMock, patch

import pytest

from spawn.core.exceptions import SpawnError
from spawn.utils.git import (
    add_all,
    add_remote,
    commit,
    initialize_git,
    is_git_repository,
    push_origin_main,
    remote_exists,
    rename_main_branch,
    run_git_command,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cpe(stderr: str = "") -> subprocess.CalledProcessError:
    exc = subprocess.CalledProcessError(returncode=1, cmd=["git", "init"])
    exc.stderr = stderr
    return exc


# ---------------------------------------------------------------------------
# initialize_git
# ---------------------------------------------------------------------------


@patch("subprocess.run")
def test_initialize_git_success(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    initialize_git(tmp_path)  # should not raise
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_initialize_git_file_not_found(mock_run, tmp_path):
    mock_run.side_effect = FileNotFoundError
    with pytest.raises(SpawnError, match="Git is not installed"):
        initialize_git(tmp_path)


@patch("subprocess.run")
def test_initialize_git_called_process_error(mock_run, tmp_path):
    mock_run.side_effect = _cpe("fatal: already a git repo")
    with pytest.raises(SpawnError, match="Failed to initialize Git repository"):
        initialize_git(tmp_path)


# ---------------------------------------------------------------------------
# run_git_command
# ---------------------------------------------------------------------------


@patch("subprocess.run")
def test_run_git_command_success(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    run_git_command(tmp_path, "status")  # should not raise
    mock_run.assert_called_once_with(
        ["git", "status"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )


@patch("subprocess.run")
def test_run_git_command_file_not_found(mock_run, tmp_path):
    mock_run.side_effect = FileNotFoundError
    with pytest.raises(SpawnError, match="Git is not installed"):
        run_git_command(tmp_path, "status")


@patch("subprocess.run")
def test_run_git_command_cpe_with_stderr(mock_run, tmp_path):
    mock_run.side_effect = _cpe("error: pathspec 'main' did not match")
    with pytest.raises(SpawnError, match="pathspec 'main' did not match"):
        run_git_command(tmp_path, "checkout", "main")


@patch("subprocess.run")
def test_run_git_command_cpe_empty_stderr_uses_fallback(mock_run, tmp_path):
    mock_run.side_effect = _cpe("")
    with pytest.raises(SpawnError, match="Git command failed"):
        run_git_command(tmp_path, "push")


@patch("subprocess.run")
def test_run_git_command_cpe_is_chained(mock_run, tmp_path):
    original = _cpe("some error")
    mock_run.side_effect = original
    with pytest.raises(SpawnError) as exc_info:
        run_git_command(tmp_path, "push")
    assert exc_info.value.__cause__ is original


# ---------------------------------------------------------------------------
# add_all / commit / rename_main_branch / add_remote / push_origin_main
# — each should delegate to run_git_command with the correct args
# ---------------------------------------------------------------------------


@patch("spawn.utils.git.run_git_command")
def test_add_all_calls_run_git_command(mock_rgc, tmp_path):
    add_all(tmp_path)
    mock_rgc.assert_called_once_with(tmp_path, "add", ".")


@patch("spawn.utils.git.run_git_command")
def test_commit_calls_run_git_command(mock_rgc, tmp_path):
    commit(tmp_path, "Initial commit")
    mock_rgc.assert_called_once_with(tmp_path, "commit", "-m", "Initial commit")


@patch("spawn.utils.git.run_git_command")
def test_rename_main_branch_calls_run_git_command(mock_rgc, tmp_path):
    rename_main_branch(tmp_path)
    mock_rgc.assert_called_once_with(tmp_path, "branch", "-M", "main")


@patch("spawn.utils.git.run_git_command")
def test_add_remote_calls_run_git_command(mock_rgc, tmp_path):
    add_remote(tmp_path, "https://github.com/user/repo.git")
    mock_rgc.assert_called_once_with(
        tmp_path,
        "remote",
        "add",
        "origin",
        "https://github.com/user/repo.git",
    )


@patch("spawn.utils.git.run_git_command")
def test_push_origin_main_calls_run_git_command(mock_rgc, tmp_path):
    push_origin_main(tmp_path)
    mock_rgc.assert_called_once_with(tmp_path, "push", "-u", "origin", "main")


# ---------------------------------------------------------------------------
# remote_exists
# ---------------------------------------------------------------------------


@patch("subprocess.run")
def test_remote_exists_returns_true_when_origin_present(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0, stdout="origin\nupstream\n")
    assert remote_exists(tmp_path) is True


@patch("subprocess.run")
def test_remote_exists_returns_false_when_origin_absent(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0, stdout="upstream\n")
    assert remote_exists(tmp_path) is False


@patch("subprocess.run")
def test_remote_exists_returns_false_on_cpe(mock_run, tmp_path):
    mock_run.side_effect = _cpe("not a git repository")
    assert remote_exists(tmp_path) is False


@patch("subprocess.run")
def test_remote_exists_raises_spawn_error_when_git_missing(mock_run, tmp_path):
    mock_run.side_effect = FileNotFoundError
    with pytest.raises(SpawnError, match="Git is not installed"):
        remote_exists(tmp_path)


# ---------------------------------------------------------------------------
# is_git_repository
# ---------------------------------------------------------------------------


def test_is_git_repository_true(tmp_path):
    (tmp_path / ".git").mkdir()
    assert is_git_repository(tmp_path) is True


def test_is_git_repository_false(tmp_path):
    assert is_git_repository(tmp_path) is False
