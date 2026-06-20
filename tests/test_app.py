"""Integration tests for cli/app.py using Typer's CliRunner.

All heavy I/O (filesystem, subprocess, prompts) is mocked so tests run
instantly without touching the real system.
"""
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.core.exceptions import SpawnError
from spawn.core.models import ProjectConfig
from spawn.github.exceptions import GitHubPublishError

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_CONFIG = ProjectConfig(name="demo", template="python", use_git=True)
_VALID_CONFIG_NO_GIT = ProjectConfig(name="demo", template="python", use_git=False)


def _fake_generate(_config: ProjectConfig) -> Path:
    """Stub that returns a plausible project path without touching the FS."""
    return Path("demo")


# ---------------------------------------------------------------------------
# spawn version
# ---------------------------------------------------------------------------


def test_version_prints_version_string():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Spawn v" in result.output


# ---------------------------------------------------------------------------
# spawn create — happy path (use_git=True, decline GitHub publish)
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG)
@patch("spawn.cli.app.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.Confirm.ask", return_value=False)
def test_create_happy_path_declines_github(
    mock_confirm, mock_show_success, mock_generator_cls, mock_config
):
    mock_generator_cls.return_value.generate.side_effect = _fake_generate

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 0
    mock_show_success.assert_called_once()
    # Declined publish → no "Published" text
    assert "Published" not in result.output


# ---------------------------------------------------------------------------
# spawn create — use_git=False skips GitHub publish entirely
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG_NO_GIT)
@patch("spawn.cli.app.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.Confirm.ask")
def test_create_no_git_skips_publish_prompt(
    mock_confirm, mock_show_success, mock_generator_cls, mock_config
):
    mock_generator_cls.return_value.generate.side_effect = _fake_generate

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 0
    assert "GitHub publishing requires Git" in result.output
    # Confirm.ask must never be called because we returned before it
    mock_confirm.assert_not_called()


# ---------------------------------------------------------------------------
# spawn create — generation raises SpawnError
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG)
@patch("spawn.cli.app.ProjectGenerator")
def test_create_generation_error_prints_message(mock_generator_cls, mock_config):
    mock_generator_cls.return_value.generate.side_effect = SpawnError("disk full")

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 0
    assert "❌" in result.output
    assert "disk full" in result.output


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG)
@patch("spawn.cli.app.ProjectGenerator")
@patch("spawn.cli.app.GitHubPublisher")
def test_create_generation_error_does_not_attempt_publish(
    mock_publisher_cls, mock_generator_cls, mock_config
):
    mock_generator_cls.return_value.generate.side_effect = SpawnError("oops")

    runner.invoke(app, ["create"])

    mock_publisher_cls.return_value.publish.assert_not_called()


# ---------------------------------------------------------------------------
# spawn create — GitHub publish success
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG)
@patch("spawn.cli.app.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.Confirm.ask", return_value=True)
@patch("spawn.cli.app.Prompt.ask", return_value="https://github.com/user/repo.git")
@patch("spawn.cli.app.GitHubPublisher")
def test_create_github_publish_success(
    mock_publisher_cls,
    mock_prompt,
    mock_confirm,
    mock_show_success,
    mock_generator_cls,
    mock_config,
):
    mock_generator_cls.return_value.generate.side_effect = _fake_generate
    mock_publisher_cls.return_value.publish.return_value = None

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 0
    assert "Published successfully" in result.output


# ---------------------------------------------------------------------------
# spawn create — GitHub publish raises GitHubPublishError
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG)
@patch("spawn.cli.app.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.Confirm.ask", return_value=True)
@patch("spawn.cli.app.Prompt.ask", return_value="https://github.com/user/repo.git")
@patch("spawn.cli.app.GitHubPublisher")
def test_create_github_publish_error_prints_message(
    mock_publisher_cls,
    mock_prompt,
    mock_confirm,
    mock_show_success,
    mock_generator_cls,
    mock_config,
):
    mock_generator_cls.return_value.generate.side_effect = _fake_generate
    mock_publisher_cls.return_value.publish.side_effect = GitHubPublishError(
        "push rejected"
    )

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 0
    assert "❌" in result.output
    assert "push rejected" in result.output


# ---------------------------------------------------------------------------
# spawn doctor — path validation
# ---------------------------------------------------------------------------


def test_doctor_nonexistent_path(tmp_path):
    nonexistent = str(tmp_path / "does_not_exist")
    result = runner.invoke(app, ["doctor", nonexistent])
    assert result.exit_code == 1
    assert "Path does not exist" in result.output


def test_doctor_path_is_file_not_directory(tmp_path):
    f = tmp_path / "somefile.txt"
    f.write_text("hello", encoding="utf-8")
    result = runner.invoke(app, ["doctor", str(f)])
    assert result.exit_code == 1
    assert "Path is not a directory" in result.output
