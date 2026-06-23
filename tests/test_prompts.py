"""Tests for cli/prompts.py — get_project_config()."""
from unittest.mock import patch

import pytest

from spawn.cli.prompts import get_project_config
from spawn.core.models import ProjectConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_prompt_side_effects(*values):
    """Return a list to use as side_effect for sequential typer.prompt calls."""
    return list(values)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@patch("spawn.cli.prompts.typer.confirm", return_value=True)
@patch("spawn.cli.prompts.typer.prompt", side_effect=["my-project", "1"])
def test_valid_name_and_template_returns_config(mock_prompt, mock_confirm):
    config = get_project_config()

    assert isinstance(config, ProjectConfig)
    assert config.name == "my-project"
    assert config.template == "python"
    assert config.use_git is True


@patch("spawn.cli.prompts.typer.confirm", return_value=False)
@patch("spawn.cli.prompts.typer.prompt", side_effect=["my-project", "2"])
def test_git_false_reflected_in_config(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.use_git is False
    assert config.template == "fastapi"


# ---------------------------------------------------------------------------
# Invalid project name retried until valid
# ---------------------------------------------------------------------------


@patch("spawn.cli.prompts.typer.confirm", return_value=False)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "--",          # invalid: no alphanumeric
        "good-name",   # valid
        "1",           # template choice
    ],
)
def test_invalid_name_retried_until_valid(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.name == "good-name"


@patch("spawn.cli.prompts.typer.confirm", return_value=False)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "my project",  # invalid: space
        "my-project",  # valid
        "3",           # template choice
    ],
)
def test_name_with_space_retried(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.name == "my-project"
    assert config.template == "data-science"


# ---------------------------------------------------------------------------
# Invalid template choice retried until valid
# ---------------------------------------------------------------------------


@patch("spawn.cli.prompts.typer.confirm", return_value=True)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "demo",   # valid name
        "9",      # invalid template choice
        "0",      # invalid template choice
        "4",      # valid: ml
    ],
)
def test_invalid_template_choice_retried(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.template == "ml"


@patch("spawn.cli.prompts.typer.confirm", return_value=True)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "demo",
        "abc",   # invalid (non-numeric)
        "2",     # valid: fastapi
    ],
)
def test_non_numeric_template_choice_retried(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.template == "fastapi"


# ---------------------------------------------------------------------------
# All four template choices map correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "choice,expected_template",
    [
        ("1", "python"),
        ("2", "fastapi"),
        ("3", "data-science"),
        ("4", "ml"),
    ],
)
@patch("spawn.cli.prompts.typer.confirm", return_value=False)
def test_all_template_choices(mock_confirm, choice, expected_template):
    with patch(
        "spawn.cli.prompts.typer.prompt", side_effect=["project", choice]
    ):
        config = get_project_config()
    assert config.template == expected_template


# ---------------------------------------------------------------------------
# Backend API — framework and extras prompt flow
# ---------------------------------------------------------------------------


@patch("spawn.cli.prompts.typer.confirm", return_value=False)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "my-api",   # project name
        "5",        # template: backend-api
        "1",        # framework: fastapi
        "1,2",      # extras: ruff + pytest
    ],
)
def test_backend_api_with_framework_and_extras(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.name == "my-api"
    assert config.template == "backend-api"
    assert config.framework == "fastapi"
    assert "ruff" in config.extras
    assert "pytest" in config.extras


@patch("spawn.cli.prompts.typer.confirm", return_value=True)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "my-api",   # project name
        "5",        # template: backend-api
        "1",        # framework: fastapi
        "",         # extras: skipped
    ],
)
def test_backend_api_with_no_extras(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.template == "backend-api"
    assert config.framework == "fastapi"
    assert config.extras == []


@patch("spawn.cli.prompts.typer.confirm", return_value=False)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "my-api",
        "5",
        "1",
        "1,9,2",    # 9 is out of range — should be ignored, ruff+pytest kept
    ],
)
def test_backend_api_extras_invalid_entry_ignored(mock_prompt, mock_confirm):
    config = get_project_config()
    assert "ruff" in config.extras
    assert "pytest" in config.extras
    assert len(config.extras) == 2


@patch("spawn.cli.prompts.typer.confirm", return_value=False)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "my-api",
        "5",    # backend-api
        "2",    # flask
        "",     # no extras
    ],
)
def test_backend_api_flask_framework_selected(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.template == "backend-api"
    assert config.framework == "flask"
    assert config.extras == []


@patch("spawn.cli.prompts.typer.confirm", return_value=False)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "my-api",
        "5",    # backend-api
        "3",    # django
        "",     # no extras
    ],
)
def test_backend_api_django_framework_selected(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.template == "backend-api"
    assert config.framework == "django"


@patch("spawn.cli.prompts.typer.confirm", return_value=False)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "my-api",
        "5",        # backend-api
        "1",        # fastapi
        "3,4",      # docker + github-actions
    ],
)
def test_backend_api_docker_and_github_actions_extras(mock_prompt, mock_confirm):
    config = get_project_config()
    assert "docker" in config.extras
    assert "github-actions" in config.extras
