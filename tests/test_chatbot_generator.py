"""Generator integration tests for the AI Chatbot template."""

import json

from contextlib import contextmanager
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.chatbot import ChatbotTemplate


def _cfg(
    name: str = "my-bot",
    framework: str = "pydantic-ai",
    extras: list[str] | None = None,
) -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="chatbot",
        use_git=False,
        framework=framework,
        extras=extras or [],
    )


@contextmanager
def _mock_uv_and_install():
    with (
        patch("spawn.generators.project_generator.install_packages"),
        patch("spawn.generators.project_generator.initialize_uv"),
        patch.object(ChatbotTemplate, "post_install"),
    ):
        yield


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------


def test_chatbot_creates_root_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot").is_dir()


def test_chatbot_creates_chatbot_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "src" / "chatbot").is_dir()


def test_chatbot_creates_providers_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "src" / "providers").is_dir()


def test_chatbot_creates_prompts_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "src" / "prompts").is_dir()


def test_chatbot_creates_tests_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "tests").is_dir()


# ---------------------------------------------------------------------------
# File tests
# ---------------------------------------------------------------------------


def test_chatbot_creates_main(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "src" / "main.py").exists()


def test_chatbot_creates_chat_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "src" / "chatbot" / "chat.py").exists()


def test_chatbot_creates_llm_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "src" / "providers" / "llm.py").exists()


def test_chatbot_creates_system_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "src" / "prompts" / "system.txt").exists()


def test_chatbot_creates_test_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "tests" / "test_chatbot.py").exists()


def test_chatbot_creates_conftest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "tests" / "conftest.py").exists()


def test_chatbot_creates_env_example(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / ".env.example").exists()


# ---------------------------------------------------------------------------
# Content tests
# ---------------------------------------------------------------------------


def test_chatbot_pydantic_ai_env_has_correct_model_format(tmp_path, monkeypatch):
    """pydantic-ai .env.example must use openai:gpt-4o-mini prefix."""
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(framework="pydantic-ai"))
    env = (tmp_path / "my-bot" / ".env.example").read_text(encoding="utf-8")
    assert "MODEL=openai:gpt-4o-mini" in env
    assert "BASE_URL" not in env


def test_chatbot_openai_sdk_env_has_plain_model(tmp_path, monkeypatch):
    """openai-sdk .env.example must use plain model name."""
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(framework="openai-sdk"))
    env = (tmp_path / "my-bot" / ".env.example").read_text(encoding="utf-8")
    assert "MODEL=gpt-4o-mini" in env


def test_chatbot_readme_contains_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="my-assistant"))
    readme = (tmp_path / "my-assistant" / "README.md").read_text(encoding="utf-8")
    assert "my-assistant" in readme


def test_chatbot_pydantic_ai_llm_uses_agent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(framework="pydantic-ai"))
    llm = (tmp_path / "my-bot" / "src" / "providers" / "llm.py").read_text(
        encoding="utf-8"
    )
    assert "pydantic_ai" in llm
    assert "Agent" in llm


def test_chatbot_openai_sdk_llm_uses_openai_client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(framework="openai-sdk"))
    llm = (tmp_path / "my-bot" / "src" / "providers" / "llm.py").read_text(
        encoding="utf-8"
    )
    assert "OpenAI" in llm
    assert "pydantic_ai" not in llm


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


def test_chatbot_creates_spawn_meta_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-bot",
        template="chatbot",
        use_git=False,
        framework="pydantic-ai",
        provider="openai",
        extras=[],
    )
    with _mock_uv_and_install():
        ProjectGenerator().generate(config)
    meta = json.loads(
        (tmp_path / "my-bot" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "chatbot"
    assert meta["framework"] == "pydantic-ai"
    assert "provider" in meta
    assert meta["provider"] == "openai"


def test_chatbot_openai_sdk_meta_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(framework="openai-sdk"))
    meta = json.loads(
        (tmp_path / "my-bot" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "chatbot"
    assert meta["framework"] == "openai-sdk"
    assert "provider" in meta


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def test_chatbot_pydantic_ai_install_packages_called(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with (
        patch("spawn.generators.project_generator.install_packages") as mock_install,
        patch("spawn.generators.project_generator.initialize_uv"),
        patch.object(ChatbotTemplate, "post_install"),
    ):
        ProjectGenerator().generate(_cfg(framework="pydantic-ai"))
    args = mock_install.call_args[0][1]
    assert "pydantic-ai" in args
    assert "python-dotenv" in args


def test_chatbot_openai_sdk_install_packages_called(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with (
        patch("spawn.generators.project_generator.install_packages") as mock_install,
        patch("spawn.generators.project_generator.initialize_uv"),
        patch.object(ChatbotTemplate, "post_install"),
    ):
        ProjectGenerator().generate(_cfg(framework="openai-sdk"))
    args = mock_install.call_args[0][1]
    assert "openai" in args
    assert "python-dotenv" in args
    assert "pydantic-ai[openai]" not in args


def test_chatbot_extras_reach_install_packages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with (
        patch("spawn.generators.project_generator.install_packages") as mock_install,
        patch("spawn.generators.project_generator.initialize_uv"),
        patch.object(ChatbotTemplate, "post_install"),
    ):
        ProjectGenerator().generate(_cfg(extras=["ruff", "pytest"]))
    args = mock_install.call_args[0][1]
    assert "ruff" in args
    assert "pytest" in args


def test_chatbot_meta_json_has_provider(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with (
        patch("spawn.generators.project_generator.install_packages"),
        patch("spawn.generators.project_generator.initialize_uv"),
        patch.object(ChatbotTemplate, "post_install"),
    ):
        config = ProjectConfig(
            name="my-bot",
            template="chatbot",
            use_git=False,
            framework="pydantic-ai",
            provider="gemini",
            extras=[],
        )
        ProjectGenerator().generate(config)
    meta = json.loads(
        (tmp_path / "my-bot" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["provider"] == "gemini"


def test_chatbot_pydantic_ai_only_pydantic_dep(tmp_path, monkeypatch):
    """pydantic-ai projects should not install openai/anthropic separately."""
    monkeypatch.chdir(tmp_path)
    with (
        patch("spawn.generators.project_generator.install_packages") as mock_install,
        patch("spawn.generators.project_generator.initialize_uv"),
        patch.object(ChatbotTemplate, "post_install"),
    ):
        ProjectGenerator().generate(_cfg(framework="pydantic-ai"))
    args = mock_install.call_args[0][1]
    assert "pydantic-ai" in args
    assert "openai" not in args
    assert "anthropic" not in args
    assert "google-genai" not in args


def test_chatbot_memory_history_has_pai_functions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    mem = (tmp_path / "my-bot" / "src" / "memory" / "history.py").read_text(
        encoding="utf-8"
    )
    assert "get_pai_history" in mem
    assert "append_pai_messages" in mem
    assert "_pai_history" in mem


# ─── AGENTS.md ───────────────────────────────────────────────────────────


def test_chatbot_creates_agents_md(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-bot" / "AGENTS.md").is_file()


def test_chatbot_agents_md_contains_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="test-chatbot-x"))
    content = (tmp_path / "test-chatbot-x" / "AGENTS.md").read_text(encoding="utf-8")
    assert "test-chatbot-x" in content
