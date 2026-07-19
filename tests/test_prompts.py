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
@patch("spawn.cli.prompts.typer.prompt", side_effect=["my-project", "2", "1", "1", ""])
def test_valid_name_and_template_returns_config(mock_prompt, mock_confirm):
    config = get_project_config()

    assert isinstance(config, ProjectConfig)
    assert config.name == "my-project"
    assert config.template == "cli"
    assert config.use_git is True


@patch("spawn.cli.prompts.typer.confirm", return_value=False)
@patch("spawn.cli.prompts.typer.prompt", side_effect=["my-project", "1", "1", ""])
def test_git_false_reflected_in_config(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.use_git is False
    assert config.template == "backend-api"


# ---------------------------------------------------------------------------
# Invalid project name retried until valid
# ---------------------------------------------------------------------------


@patch("spawn.cli.prompts.typer.confirm", return_value=False)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "--",          # invalid: no alphanumeric
        "good-name",   # valid
        "2",           # template choice: cli
        "1",           # framework: typer
        "1",           # cli_type: utility
        "",            # extras: skip
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
        "2",           # template choice: cli
        "1",           # framework: typer
        "1",           # cli_type: utility
        "",            # extras: skip
    ],
)
def test_name_with_space_retried(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.name == "my-project"
    assert config.template == "cli"


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
        "2",      # valid: cli
        "1",      # framework: typer
        "1",      # cli_type: utility
        "",       # extras: skip
    ],
)
def test_invalid_template_choice_retried(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.template == "cli"


@patch("spawn.cli.prompts.typer.confirm", return_value=True)
@patch(
    "spawn.cli.prompts.typer.prompt",
    side_effect=[
        "demo",
        "abc",   # invalid (non-numeric)
        "2",     # valid: cli
        "1",     # framework: typer
        "1",     # cli_type: utility
        "",      # extras: skip
    ],
)
def test_non_numeric_template_choice_retried(mock_prompt, mock_confirm):
    config = get_project_config()
    assert config.template == "cli"


# ---------------------------------------------------------------------------
# All template choices map correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "choice,expected_template",
    [
        ("1", "backend-api"),
        ("2", "cli"),
        ("3", "automation"),
        ("4", "chatbot"),
    ],
)
@patch("spawn.cli.prompts.typer.confirm", return_value=False)
def test_all_template_choices(mock_confirm, choice, expected_template):
    if expected_template == "backend-api":
        side_effects = ["project", choice, "1", ""]       # name, choice, framework, extras
    elif expected_template == "automation":
        side_effects = ["project", choice, ""]            # name, choice, extras (skip)
    elif expected_template == "chatbot":
        side_effects = ["project", choice, "1", "1", ""]  # name, choice, framework, provider, extras
    else:
        side_effects = ["project", choice, "1", "1", ""]  # name, choice, framework, cli_type, extras
    with patch(
        "spawn.cli.prompts.typer.prompt", side_effect=side_effects
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
        "1",        # template: backend-api
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
        "1",        # template: backend-api
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
        "1",
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
        "1",    # backend-api
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
        "1",    # backend-api
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
        "1",        # backend-api
        "1",        # fastapi
        "3,4",      # docker + github-actions
    ],
)
def test_backend_api_docker_and_github_actions_extras(mock_prompt, mock_confirm):
    config = get_project_config()
    assert "docker" in config.extras
    assert "github-actions" in config.extras


def test_existing_directory_name_retried(tmp_path, monkeypatch):
    """If the project directory already exists, prompt loops and retries."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "taken").mkdir()

    with patch("spawn.cli.prompts.typer.prompt") as mock_prompt, \
         patch("spawn.cli.prompts.typer.confirm", return_value=False):
        mock_prompt.side_effect = ["taken", "free", "2", "1", "1", ""]
        config = get_project_config()

    assert config.name == "free"


def test_existing_directory_shows_error_message(tmp_path, monkeypatch):
    """Error message is shown when entered name already exists as a directory."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "taken").mkdir()

    with patch("spawn.cli.prompts.typer.prompt") as mock_prompt, \
         patch("spawn.cli.prompts.typer.confirm", return_value=False), \
         patch("spawn.cli.prompts.typer.secho") as mock_secho:
        mock_prompt.side_effect = ["taken", "free", "2", "1", "1", ""]
        get_project_config()

    error_calls = [str(call) for call in mock_secho.call_args_list]
    assert any("already exists" in c for c in error_calls)


# ---------------------------------------------------------------------------
# Custom Structure — dependency prompt
# ---------------------------------------------------------------------------


def _custom_stdin(text: str):
    """Return a StringIO that mimics sys.stdin.read() returning *text*."""
    import io
    return io.StringIO(text)


_SIMPLE_STRUCTURE = "src/\n    main.py\n"


@patch("spawn.cli.prompts.typer.confirm")
@patch("spawn.cli.prompts.typer.prompt")
def test_custom_structure_dependency_prompt_shown_when_uv_true(mock_prompt, mock_confirm, monkeypatch):
    """When use_uv=True the Dependencies prompt fires and its value is captured."""
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(_SIMPLE_STRUCTURE))
    # confirm sequence: Git? → uv? → Proceed?
    mock_confirm.side_effect = [True, True, True]
    # prompt sequence: project-name (from get_project_config) → template choice
    # → then _get_custom_structure_config only calls prompt for deps
    # We drive via get_project_config: name, template-choice (custom = last index)
    # But _get_custom_structure_config is called internally; its only prompt is deps.
    mock_prompt.side_effect = ["my-proj", "8", "requests, rich"]  # 8 = custom (adjust if registry changes)

    from spawn.cli.prompts import get_project_config
    from spawn.core.registry import list_templates
    custom_index = str(len(list_templates()) + 1)
    mock_prompt.side_effect = ["my-proj", custom_index, "requests, rich"]

    config = get_project_config()

    assert config.custom_dependencies == ["requests", "rich"]


@patch("spawn.cli.prompts.typer.confirm")
@patch("spawn.cli.prompts.typer.prompt")
def test_custom_structure_dependency_prompt_skipped_when_uv_false(mock_prompt, mock_confirm, monkeypatch):
    """When use_uv=False the Dependencies prompt must never be invoked."""
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(_SIMPLE_STRUCTURE))
    # confirm sequence: Git? → uv? (False) → Proceed?
    mock_confirm.side_effect = [True, False, True]

    from spawn.core.registry import list_templates
    custom_index = str(len(list_templates()) + 1)
    # Only name + template-choice prompts; NO deps prompt
    mock_prompt.side_effect = ["my-proj", custom_index]

    from spawn.cli.prompts import get_project_config
    config = get_project_config()

    assert config.custom_dependencies == []
    # Ensure no extra prompt calls were consumed (StopIteration would have fired)


@patch("spawn.cli.prompts.typer.confirm")
@patch("spawn.cli.prompts.typer.prompt")
def test_custom_structure_parses_comma_separated_deps(mock_prompt, mock_confirm, monkeypatch):
    """'fastapi, pydantic ,  sqlalchemy' parses to three trimmed package names."""
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(_SIMPLE_STRUCTURE))
    mock_confirm.side_effect = [True, True, True]  # Git, uv, Proceed

    from spawn.core.registry import list_templates
    custom_index = str(len(list_templates()) + 1)
    mock_prompt.side_effect = ["my-proj", custom_index, "fastapi, pydantic ,  sqlalchemy"]

    from spawn.cli.prompts import get_project_config
    config = get_project_config()

    assert config.custom_dependencies == ["fastapi", "pydantic", "sqlalchemy"]


@patch("spawn.cli.prompts.typer.confirm")
@patch("spawn.cli.prompts.typer.prompt")
def test_custom_structure_empty_deps_input_yields_empty_list(mock_prompt, mock_confirm, monkeypatch):
    """Pressing Enter (empty string) at the Dependencies prompt yields []."""
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(_SIMPLE_STRUCTURE))
    mock_confirm.side_effect = [True, True, True]  # Git, uv, Proceed

    from spawn.core.registry import list_templates
    custom_index = str(len(list_templates()) + 1)
    mock_prompt.side_effect = ["my-proj", custom_index, ""]  # empty deps input

    from spawn.cli.prompts import get_project_config
    config = get_project_config()

    assert config.custom_dependencies == []
