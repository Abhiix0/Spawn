"""Tests for core/planning.py — plan_project."""

from unittest.mock import patch

import pytest

from spawn.cli.noninteractive import build_config_from_args
from spawn.cli.prompts import get_project_config
from spawn.core.exceptions import SpawnError
from spawn.core.planning import plan_project
from spawn.core.registry import TEMPLATES
from spawn.templates.agent import get_supported_providers as agent_providers
from spawn.templates.chatbot import get_supported_providers as chatbot_providers


def _both(name, template, **kw):
    claude = kw.pop("generate_claude_md", False)
    a = plan_project(name, template, generate_claude_md=claude, **kw)
    b = build_config_from_args(name, template, use_claude_md=claude, **kw)
    return a, b


@pytest.mark.parametrize("slug", list(TEMPLATES))
def test_matches_build_config_from_args_for_every_template(slug):
    a, b = _both("proj", slug)
    assert a == b
    assert a.template == slug


@pytest.mark.parametrize("slug", list(TEMPLATES))
def test_matches_with_all_options(slug):
    meta = TEMPLATES[slug]
    kw = {"extras": list(meta.available_extras), "use_git": False, "use_uv": False}
    if meta.available_frameworks:
        kw["framework"] = meta.available_frameworks[-1]
    if meta.available_cli_types:
        kw["cli_type"] = meta.available_cli_types[-1]
    if meta.available_data_types:
        kw["data_type"] = meta.available_data_types[-1]
    a, b = _both("proj", slug, license="none", generate_claude_md=True, **kw)
    assert a == b


@pytest.mark.parametrize(
    "template,kw,message",
    [
        (
            "cli",
            {"cli_type": "nope"},
            "Invalid cli_type: 'nope'. Valid options for 'cli': ",
        ),
        (
            "data",
            {"data_type": "x"},
            "Invalid data_type: 'x'. Valid options for 'data': ",
        ),
        (
            "backend-api",
            {"framework": "x"},
            "Invalid framework: 'x'. Valid options for 'backend-api': ",
        ),
        (
            "agent",
            {"framework": "pydantic-ai", "provider": "x"},
            "Invalid provider: 'x'. Valid options for 'agent' with framework 'pydantic-ai': ",
        ),
        (
            "backend-api",
            {"extras": ["ruff", "x"]},
            "Invalid extra: 'x'. Valid options for 'backend-api': ",
        ),
        ("cli", {"license": "gpl"}, "Invalid license: 'gpl'. Valid options: mit, none"),
        ("zzz", {}, "Unknown template: 'zzz'. Valid templates: "),
    ],
)
def test_error_messages(template, kw, message):
    with pytest.raises(SpawnError) as exc:
        plan_project("proj", template, **kw)
    assert str(exc.value).startswith(message)


def test_extras_dedupe_preserves_order():
    cfg = plan_project("proj", "backend-api", extras=["pytest", "ruff", "pytest"])
    assert cfg.extras == ["pytest", "ruff"]


def test_existing_directory_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "taken").mkdir()
    with pytest.raises(SpawnError, match="A directory named 'taken' already exists."):
        plan_project("taken", "cli")


@pytest.mark.parametrize("fw", TEMPLATES["agent"].available_frameworks)
def test_agent_provider_by_framework(fw):
    assert (
        plan_project("proj", "agent", framework=fw).provider == agent_providers(fw)[0]
    )


@pytest.mark.parametrize("fw", TEMPLATES["chatbot"].available_frameworks)
def test_chatbot_provider_by_framework(fw):
    cfg = plan_project("proj", "chatbot", framework=fw)
    assert cfg.provider == chatbot_providers(fw)[0]


# --- interactive parity ---------------------------------------------------

_PARITY = [
    (
        "Backend API",
        "backend-api",
        ["fastapi"],
        ["ruff", "pytest"],
        {"framework": "fastapi", "extras": ["ruff", "pytest"]},
    ),
    (
        "CLI Application",
        "cli",
        ["interactive", "click"],
        [],
        {"cli_type": "interactive", "framework": "click"},
    ),
    ("Data Project", "data", ["Dashboard"], [], {"data_type": "Dashboard"}),
    ("MCP Server", "mcp", [], [], {}),
]


@pytest.mark.parametrize("display,slug,picks,extras,kw", _PARITY)
def test_interactive_matches_plan_project(display, slug, picks, extras, kw):
    assert TEMPLATES[slug].display_name == display
    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="parity-proj"),
        patch("spawn.cli.prompts.typer.confirm", return_value=True),
        patch("spawn.cli.prompts.Confirm.ask", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as sel,
        patch("spawn.cli.prompts.questionary.checkbox") as chk,
    ):
        sel.return_value.ask.side_effect = [display, *picks, "MIT"]
        chk.return_value.ask.return_value = extras
        interactive = get_project_config()
    assert interactive == plan_project("parity-proj", slug, **kw)


@pytest.mark.parametrize("slug", ["chatbot", "agent"])
def test_interactive_provider_matches_plan_project(slug):
    meta = TEMPLATES[slug]
    fw = meta.available_frameworks[-1]
    prov = (agent_providers if slug == "agent" else chatbot_providers)(fw)[-1]
    with (
        patch("spawn.cli.prompts.typer.prompt", return_value="parity-proj"),
        patch("spawn.cli.prompts.typer.confirm", return_value=True),
        patch("spawn.cli.prompts.Confirm.ask", return_value=False),
        patch("spawn.cli.prompts.questionary.select") as sel,
        patch("spawn.cli.prompts.questionary.checkbox") as chk,
    ):
        sel.return_value.ask.side_effect = [meta.display_name, fw, prov, "MIT"]
        chk.return_value.ask.return_value = []
        interactive = get_project_config()
    assert interactive == plan_project("parity-proj", slug, framework=fw, provider=prov)
