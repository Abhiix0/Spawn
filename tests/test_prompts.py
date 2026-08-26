"""Tests for cli/prompts.py — get_project_config()."""

from unittest.mock import patch, MagicMock
import io

import pytest

from spawn.cli.prompts import get_project_config, _select, _multiselect
from spawn.core.models import ProjectConfig
from spawn.core.registry import get_metadata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_select(return_value: str) -> MagicMock:
    """Return a mock for questionary.select that yields return_value from .ask()."""
    m = MagicMock()
    m.return_value.ask.return_value = return_value
    return m


def _mock_checkbox(return_value: list) -> MagicMock:
    """Return a mock for questionary.checkbox that yields return_value from .ask()."""
    m = MagicMock()
    m.return_value.ask.return_value = return_value
    return m


@pytest.fixture(autouse=True)
def _mock_confirm_ask(monkeypatch):
    monkeypatch.setattr("spawn.cli.prompts.Confirm.ask", lambda *args, **kwargs: False)


# ---------------------------------------------------------------------------
# _select / _multiselect unit tests
# ---------------------------------------------------------------------------


def test_select_raises_keyboard_interrupt_on_none():
    with patch("spawn.cli.prompts.questionary.select") as mock_qs:
        mock_qs.return_value.ask.return_value = None
        with pytest.raises(KeyboardInterrupt):
            _select("Pick one", ["a", "b"])


def test_multiselect_raises_keyboard_interrupt_on_none():
    with patch("spawn.cli.prompts.questionary.checkbox") as mock_qc:
        mock_qc.return_value.ask.return_value = None
        with pytest.raises(KeyboardInterrupt):
            _multiselect("Pick many", ["a", "b"])


def test_select_returns_chosen_value():
    with patch("spawn.cli.prompts.questionary.select") as mock_qs:
        mock_qs.return_value.ask.return_value = "b"
        result = _select("Pick one", ["a", "b"])
    assert result == "b"


def test_multiselect_returns_chosen_list():
    with patch("spawn.cli.prompts.questionary.checkbox") as mock_qc:
        mock_qc.return_value.ask.return_value = ["a", "c"]
        result = _multiselect("Pick many", ["a", "b", "c"])
    assert result == ["a", "c"]


def test_multiselect_empty_selection_is_valid():
    with patch("spawn.cli.prompts.questionary.checkbox") as mock_qc:
        mock_qc.return_value.ask.return_value = []
        result = _multiselect("Pick many", ["a", "b"])
    assert result == []


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_name_and_template_returns_config():
    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="my-project"),
        patch("spawn.cli.prompts.typer.confirm", return_value=True),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        # Template → CLI Application; CLI type → utility; Framework → typer
        mock_sel.return_value.ask.side_effect = ["CLI Application", "utility", "typer"]
        mock_chk.return_value.ask.return_value = []  # no extras
        config = get_project_config()

    assert isinstance(config, ProjectConfig)
    assert config.name == "my-project"
    assert config.template == "cli"
    assert config.use_git is True


def test_git_false_reflected_in_config():
    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="my-project"),
        patch("spawn.cli.prompts.typer.confirm", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        # Template → Backend API; Framework → fastapi
        mock_sel.return_value.ask.side_effect = ["Backend API", "fastapi"]
        mock_chk.return_value.ask.return_value = []
        config = get_project_config()

    assert config.use_git is False
    assert config.template == "backend-api"


def test_generate_claude_md_true_reflected_in_config(monkeypatch):
    monkeypatch.setattr("spawn.cli.prompts.Confirm.ask", lambda *args, **kwargs: True)
    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="my-project"),
        patch("spawn.cli.prompts.typer.confirm", return_value=True),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = ["CLI Application", "utility", "typer"]
        mock_chk.return_value.ask.return_value = []
        config = get_project_config()

    assert config.generate_claude_md is True


# ---------------------------------------------------------------------------
# Invalid project name retried until valid
# ---------------------------------------------------------------------------


def test_invalid_name_retried_until_valid():
    prompt_calls = ["--", "good-name"]  # first invalid, then valid
    with (
        patch("spawn.cli.prompts.typer.prompt", side_effect=prompt_calls),
        patch("spawn.cli.prompts.typer.confirm", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = ["CLI Application", "utility", "typer"]
        mock_chk.return_value.ask.return_value = []
        config = get_project_config()

    assert config.name == "good-name"


def test_name_with_space_retried():
    with (
        patch(
            "spawn.cli.prompts.typer.prompt", side_effect=["my project", "my-project"]
        ),
        patch("spawn.cli.prompts.typer.confirm", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = ["CLI Application", "utility", "typer"]
        mock_chk.return_value.ask.return_value = []
        config = get_project_config()

    assert config.name == "my-project"
    assert config.template == "cli"


# ---------------------------------------------------------------------------
# Template choices map correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "display_name,expected_template",
    [
        ("Backend API", "backend-api"),
        ("CLI Application", "cli"),
        ("Automation Tool", "automation"),
        ("AI Chatbot", "chatbot"),
    ],
)
def test_all_template_choices(display_name, expected_template):
    meta = get_metadata(expected_template)

    # Build side_effect list for select calls: template + sub-selects
    select_side_effects = [display_name]
    if meta and meta.available_cli_types:
        select_side_effects.append(meta.available_cli_types[0])
    if meta and meta.available_data_types:
        select_side_effects.append(meta.available_data_types[0])
    if meta and meta.available_frameworks:
        select_side_effects.append(meta.available_frameworks[0])
    if meta and meta.available_providers:
        if meta.slug == "agent":
            from spawn.templates.agent import get_supported_providers

            select_side_effects.append(
                get_supported_providers(meta.available_frameworks[0])[0]
            )
        elif meta.slug == "chatbot":
            from spawn.templates.chatbot import get_supported_providers

            select_side_effects.append(
                get_supported_providers(meta.available_frameworks[0])[0]
            )

    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="project"),
        patch("spawn.cli.prompts.typer.confirm", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = select_side_effects
        mock_chk.return_value.ask.return_value = []
        config = get_project_config()

    assert config.template == expected_template


# ---------------------------------------------------------------------------
# Backend API — framework and extras
# ---------------------------------------------------------------------------


def test_backend_api_with_framework_and_extras():
    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="my-api"),
        patch("spawn.cli.prompts.typer.confirm", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = ["Backend API", "fastapi"]
        mock_chk.return_value.ask.return_value = ["ruff", "pytest"]
        config = get_project_config()

    assert config.name == "my-api"
    assert config.template == "backend-api"
    assert config.framework == "fastapi"
    assert "ruff" in config.extras
    assert "pytest" in config.extras


def test_backend_api_with_no_extras():
    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="my-api"),
        patch("spawn.cli.prompts.typer.confirm", return_value=True),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = ["Backend API", "fastapi"]
        mock_chk.return_value.ask.return_value = []
        config = get_project_config()

    assert config.template == "backend-api"
    assert config.framework == "fastapi"
    assert config.extras == []


def test_backend_api_flask_framework_selected():
    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="my-api"),
        patch("spawn.cli.prompts.typer.confirm", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = ["Backend API", "flask"]
        mock_chk.return_value.ask.return_value = []
        config = get_project_config()

    assert config.template == "backend-api"
    assert config.framework == "flask"
    assert config.extras == []


def test_backend_api_django_framework_selected():
    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="my-api"),
        patch("spawn.cli.prompts.typer.confirm", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = ["Backend API", "django"]
        mock_chk.return_value.ask.return_value = []
        config = get_project_config()

    assert config.template == "backend-api"
    assert config.framework == "django"


def test_backend_api_docker_and_github_actions_extras():
    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="my-api"),
        patch("spawn.cli.prompts.typer.confirm", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = ["Backend API", "fastapi"]
        mock_chk.return_value.ask.return_value = ["docker", "github-actions"]
        config = get_project_config()

    assert "docker" in config.extras
    assert "github-actions" in config.extras


# ---------------------------------------------------------------------------
# Existing directory handling
# ---------------------------------------------------------------------------


def test_existing_directory_name_retried(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "taken").mkdir()

    with (
        patch("spawn.cli.prompts.typer.prompt", side_effect=["taken", "free"]),
        patch("spawn.cli.prompts.typer.confirm", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = ["CLI Application", "utility", "typer"]
        mock_chk.return_value.ask.return_value = []
        config = get_project_config()

    assert config.name == "free"


def test_existing_directory_shows_error_message(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "taken").mkdir()

    with (
        patch("spawn.cli.prompts.typer.prompt", side_effect=["taken", "free"]),
        patch("spawn.cli.prompts.typer.confirm", return_value=False),
        patch("spawn.cli.prompts.typer.secho") as mock_secho,
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.side_effect = ["CLI Application", "utility", "typer"]
        mock_chk.return_value.ask.return_value = []
        get_project_config()

    error_calls = [str(c) for c in mock_secho.call_args_list]
    assert any("already exists" in c for c in error_calls)


# ---------------------------------------------------------------------------
# Custom Structure — dependency prompt
# ---------------------------------------------------------------------------

_SIMPLE_STRUCTURE = "src/\n    main.py\n"


def _custom_select_for_custom_structure():
    """Mock select that returns 'Custom Structure' for the template choice."""
    m = MagicMock()
    m.return_value.ask.return_value = "Custom Structure"
    return m


@patch("spawn.cli.prompts.typer.confirm")
@patch("spawn.cli.prompts.typer.prompt")
def test_custom_structure_dependency_prompt_shown_when_uv_true(
    mock_prompt, mock_confirm, monkeypatch
):
    """When use_uv=True the Dependencies prompt fires and its value is captured."""
    monkeypatch.setattr("sys.stdin", io.StringIO(_SIMPLE_STRUCTURE))
    # confirm: Git? → CLAUDE.md (via Confirm.ask fixture → False) → uv? → Proceed?
    mock_confirm.side_effect = [True, True, True]
    # typer.prompt: project_name, deps_raw, extra_ignores_raw
    mock_prompt.side_effect = ["my-proj", "requests, rich", ""]

    with (
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.return_value = "Custom Structure"
        mock_chk.return_value.ask.return_value = []  # optional setup: skip

        config = get_project_config()

    assert config.custom_dependencies == ["requests", "rich"]


@patch("spawn.cli.prompts.typer.confirm")
@patch("spawn.cli.prompts.typer.prompt")
def test_custom_structure_dependency_prompt_skipped_when_uv_false(
    mock_prompt, mock_confirm, monkeypatch
):
    """When use_uv=False the Dependencies prompt must never be invoked."""
    monkeypatch.setattr("sys.stdin", io.StringIO(_SIMPLE_STRUCTURE))
    # confirm: Git? → uv? (False) → Proceed?
    mock_confirm.side_effect = [True, False, True]
    # typer.prompt: project_name, extra_ignores_raw (no deps prompt)
    mock_prompt.side_effect = ["my-proj", ""]

    with (
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.return_value = "Custom Structure"
        mock_chk.return_value.ask.return_value = []

        config = get_project_config()

    assert config.custom_dependencies == []


@patch("spawn.cli.prompts.typer.confirm")
@patch("spawn.cli.prompts.typer.prompt")
def test_custom_structure_parses_comma_separated_deps(
    mock_prompt, mock_confirm, monkeypatch
):
    """'fastapi, pydantic ,  sqlalchemy' parses to three trimmed package names."""
    monkeypatch.setattr("sys.stdin", io.StringIO(_SIMPLE_STRUCTURE))
    mock_confirm.side_effect = [True, True, True]  # Git, uv, Proceed
    mock_prompt.side_effect = ["my-proj", "fastapi, pydantic ,  sqlalchemy", ""]

    with (
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.return_value = "Custom Structure"
        mock_chk.return_value.ask.return_value = []

        config = get_project_config()

    assert config.custom_dependencies == ["fastapi", "pydantic", "sqlalchemy"]


@patch("spawn.cli.prompts.typer.confirm")
@patch("spawn.cli.prompts.typer.prompt")
def test_custom_structure_empty_deps_input_yields_empty_list(
    mock_prompt, mock_confirm, monkeypatch
):
    """Pressing Enter (empty string) at the Dependencies prompt yields []."""
    monkeypatch.setattr("sys.stdin", io.StringIO(_SIMPLE_STRUCTURE))
    mock_confirm.side_effect = [True, True, True]  # Git, uv, Proceed
    mock_prompt.side_effect = ["my-proj", "", ""]  # empty deps, skip extra ignores

    with (
        patch("spawn.cli.prompts.questionary.select") as mock_sel,
        patch("spawn.cli.prompts.questionary.checkbox") as mock_chk,
    ):
        mock_sel.return_value.ask.return_value = "Custom Structure"
        mock_chk.return_value.ask.return_value = []

        config = get_project_config()

    assert config.custom_dependencies == []
