"""Tests for spawn.cli.noninteractive — build_config_from_args and build_config_from_file."""

import json

import pytest

from spawn.cli.noninteractive import build_config_from_args, build_config_from_file
from spawn.core.exceptions import SpawnError


# ---------------------------------------------------------------------------
# build_config_from_args — valid paths
# ---------------------------------------------------------------------------


def test_automation_minimal_returns_correct_config():
    """automation has no frameworks/providers/cli_types/data_types — all None."""
    config = build_config_from_args(name="my-tool", template="automation")
    assert config.template == "automation"
    assert config.framework is None
    assert config.provider is None
    assert config.cli_type is None
    assert config.data_type is None
    assert config.extras == []


def test_cli_defaults_cli_type_to_first_option():
    """cli with no cli_type passed defaults to 'utility' (first in available_cli_types)."""
    config = build_config_from_args(name="my-cli", template="cli")
    assert config.cli_type == "utility"


def test_cli_explicit_cli_type_passes_through():
    config = build_config_from_args(name="my-cli", template="cli", cli_type="interactive")
    assert config.cli_type == "interactive"


def test_backend_api_explicit_framework_passes_through():
    config = build_config_from_args(name="my-api", template="backend-api", framework="flask")
    assert config.framework == "flask"


def test_agent_defaults_provider_to_first_of_get_agent_providers():
    """Default provider must equal get_agent_providers('pydantic-ai')[0], not a hardcoded name."""
    from spawn.templates.agent import get_supported_providers as get_agent_providers

    config = build_config_from_args(
        name="my-agent", template="agent", framework="pydantic-ai"
    )
    expected = get_agent_providers("pydantic-ai")[0]
    assert config.provider == expected


def test_backend_api_valid_extras_pass_through_in_order():
    config = build_config_from_args(
        name="my-api", template="backend-api", extras=["ruff", "pytest"]
    )
    assert config.extras == ["ruff", "pytest"]


def test_backend_api_duplicate_extras_deduplicated():
    config = build_config_from_args(
        name="my-api", template="backend-api", extras=["ruff", "ruff"]
    )
    assert config.extras == ["ruff"]


def test_use_git_and_use_uv_forwarded():
    config = build_config_from_args(
        name="my-tool", template="automation", use_git=False, use_uv=False
    )
    assert config.use_git is False
    assert config.use_uv is False


# ---------------------------------------------------------------------------
# build_config_from_args — validation errors
# ---------------------------------------------------------------------------


def test_invalid_cli_type_raises():
    with pytest.raises(SpawnError, match="Invalid cli_type"):
        build_config_from_args(name="my-cli", template="cli", cli_type="bogus")


def test_invalid_framework_raises():
    with pytest.raises(SpawnError, match="Invalid framework"):
        build_config_from_args(name="my-api", template="backend-api", framework="rails")


def test_invalid_provider_raises():
    with pytest.raises(SpawnError, match="Invalid provider"):
        build_config_from_args(
            name="my-bot",
            template="chatbot",
            framework="openai-sdk",
            provider="made-up",
        )


def test_invalid_extras_raises():
    with pytest.raises(SpawnError, match="Invalid extra"):
        build_config_from_args(
            name="my-api",
            template="backend-api",
            extras=["ruff", "nonsense"],
        )


def test_unknown_template_raises():
    with pytest.raises(SpawnError, match="Unknown template"):
        build_config_from_args(name="my-proj", template="nope")


def test_custom_template_raises():
    """'custom' is not in the registry — must raise SpawnError."""
    with pytest.raises(SpawnError, match="Unknown template"):
        build_config_from_args(name="my-proj", template="custom")


def test_existing_directory_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "exists").mkdir()
    with pytest.raises(SpawnError, match="already exists"):
        build_config_from_args(name="exists", template="automation")


def test_invalid_project_name_raises():
    with pytest.raises(SpawnError):
        build_config_from_args(name="has spaces", template="automation")


# ---------------------------------------------------------------------------
# build_config_from_file — valid paths
# ---------------------------------------------------------------------------


def test_valid_minimal_json_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg_file = tmp_path / "spawn.json"
    cfg_file.write_text(json.dumps({"name": "demo", "template": "automation"}))
    config = build_config_from_file(cfg_file)
    assert config.name == "demo"
    assert config.template == "automation"
    assert config.framework is None
    assert config.extras == []


def test_json_file_all_optional_fields(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg_file = tmp_path / "full.json"
    cfg_file.write_text(
        json.dumps({
            "name": "full-proj",
            "template": "backend-api",
            "framework": "flask",
            "extras": ["ruff"],
            "git": False,
            "uv": False,
        })
    )
    config = build_config_from_file(cfg_file)
    assert config.framework == "flask"
    assert config.extras == ["ruff"]
    assert config.use_git is False
    assert config.use_uv is False


# ---------------------------------------------------------------------------
# build_config_from_file — error paths
# ---------------------------------------------------------------------------


def test_missing_file_raises(tmp_path):
    with pytest.raises(SpawnError, match="Config file not found"):
        build_config_from_file(tmp_path / "nonexistent.json")


def test_malformed_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    with pytest.raises(SpawnError, match="Invalid JSON"):
        build_config_from_file(bad)


def test_json_array_raises(tmp_path):
    f = tmp_path / "array.json"
    f.write_text(json.dumps(["a", "b"]))
    with pytest.raises(SpawnError, match="JSON object"):
        build_config_from_file(f)


def test_missing_name_raises(tmp_path):
    f = tmp_path / "no_name.json"
    f.write_text(json.dumps({"template": "automation"}))
    with pytest.raises(SpawnError, match="'name'"):
        build_config_from_file(f)


def test_missing_template_raises(tmp_path):
    f = tmp_path / "no_template.json"
    f.write_text(json.dumps({"name": "demo"}))
    with pytest.raises(SpawnError, match="'template'"):
        build_config_from_file(f)


def test_extras_not_a_list_raises(tmp_path):
    f = tmp_path / "bad_extras.json"
    f.write_text(json.dumps({"name": "demo", "template": "automation", "extras": "ruff"}))
    with pytest.raises(SpawnError, match="list of strings"):
        build_config_from_file(f)
