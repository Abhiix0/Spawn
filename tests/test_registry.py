from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.core.registry import get_metadata, get_template, list_templates
from spawn.generators.project_generator import ProjectGenerator


def test_invalid_template_returns_none():

    assert get_template("banana") is None


def test_backend_api_template_is_registered():
    from spawn.templates.backend_api import BackendAPITemplate

    template = get_template("backend-api")
    assert template is not None
    assert isinstance(template, BackendAPITemplate)


def test_removed_slugs_return_none():
    assert get_template("python") is None
    assert get_template("fastapi") is None


def test_list_templates_returns_all():
    templates = list_templates()
    slugs = [t.slug for t in templates]
    assert "backend-api" in slugs
    assert "cli" in slugs
    assert "automation" in slugs
    assert "chatbot" in slugs
    assert "mcp" in slugs
    assert len(slugs) == 8


def test_get_metadata_returns_none_for_unknown():
    assert get_metadata("banana") is None


def test_backend_api_in_list_templates():
    templates = list_templates()
    slugs = [t.slug for t in templates]
    assert "backend-api" in slugs


def test_backend_api_metadata():
    from spawn.core.registry import get_metadata

    meta = get_metadata("backend-api")
    assert meta is not None
    assert meta.slug == "backend-api"
    assert meta.display_name == "Backend API"
    assert "fastapi" in meta.available_frameworks
    assert "ruff" in meta.available_extras
    assert "pytest" in meta.available_extras


def test_backend_api_template_exists():
    from spawn.templates.backend_api import BackendAPITemplate

    template = get_template("backend-api")
    assert template is not None
    assert isinstance(template, BackendAPITemplate)
    assert template.name == "Backend API"


def test_backend_api_frameworks_include_flask_and_django():
    from spawn.core.registry import get_metadata

    meta = get_metadata("backend-api")
    assert "flask" in meta.available_frameworks
    assert "django" in meta.available_frameworks


def test_backend_api_extras_include_docker_and_github_actions():
    from spawn.core.registry import get_metadata

    meta = get_metadata("backend-api")
    assert "docker" in meta.available_extras
    assert "github-actions" in meta.available_extras


def test_cli_template_is_registered():
    from spawn.templates.cli_application import CLITemplate

    template = get_template("cli")
    assert template is not None
    assert isinstance(template, CLITemplate)


def test_cli_metadata():
    meta = get_metadata("cli")
    assert meta is not None
    assert meta.slug == "cli"
    assert meta.display_name == "CLI Application"
    assert "typer" in meta.available_frameworks
    assert "click" in meta.available_frameworks
    assert "argparse" in meta.available_frameworks
    assert "ruff" in meta.available_extras
    assert "pytest" in meta.available_extras
    assert "utility" in meta.available_cli_types
    assert "interactive" in meta.available_cli_types


def test_cli_in_list_templates():
    slugs = [m.slug for m in list_templates()]
    assert "cli" in slugs


def test_automation_template_is_registered():
    from spawn.templates.automation import AutomationTemplate

    template = get_template("automation")
    assert template is not None
    assert isinstance(template, AutomationTemplate)


def test_automation_metadata():
    meta = get_metadata("automation")
    assert meta is not None
    assert meta.slug == "automation"
    assert meta.display_name == "Automation Tool"
    assert "ruff" in meta.available_extras
    assert "pytest" in meta.available_extras
    assert "github-actions" in meta.available_extras
    assert meta.available_frameworks == []
    assert meta.available_cli_types == []


def test_automation_in_list_templates():
    slugs = [m.slug for m in list_templates()]
    assert "automation" in slugs


def test_chatbot_template_is_registered():
    from spawn.templates.chatbot import ChatbotTemplate

    template = get_template("chatbot")
    assert template is not None
    assert isinstance(template, ChatbotTemplate)


def test_chatbot_metadata():
    meta = get_metadata("chatbot")
    assert meta is not None
    assert meta.slug == "chatbot"
    assert meta.display_name == "AI Chatbot"
    assert "pydantic-ai" in meta.available_frameworks
    assert "openai-sdk" in meta.available_frameworks
    assert "ruff" in meta.available_extras
    assert "pytest" in meta.available_extras
    assert "github-actions" in meta.available_extras
    assert "ollama" in meta.available_providers
    assert "groq" in meta.available_providers
    assert meta.available_cli_types == []


def test_chatbot_in_list_templates():
    slugs = [m.slug for m in list_templates()]
    assert "chatbot" in slugs


def test_agent_template_is_registered():
    from spawn.core.registry import get_template
    from spawn.templates.agent import AgentTemplate

    t = get_template("agent")
    assert t is not None
    assert isinstance(t, AgentTemplate)


def test_agent_metadata():
    meta = get_metadata("agent")
    assert meta is not None
    assert meta.slug == "agent"
    assert meta.display_name == "AI Agent"
    assert "pydantic-ai" in meta.available_frameworks
    assert "openai-agents" in meta.available_frameworks


def test_rag_is_registered():
    from spawn.templates.rag import RAGTemplate

    t = get_template("rag")
    assert t is not None
    assert isinstance(t, RAGTemplate)


def test_rag_metadata():
    meta = get_metadata("rag")
    assert meta is not None
    assert meta.slug == "rag"
    assert meta.display_name == "RAG System"
    assert not meta.available_frameworks
    assert not meta.available_providers
    assert "ruff" in meta.available_extras
    assert "pytest" in meta.available_extras


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_generate_all_templates_with_full_available_extras(
    mock_uv, mock_install, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    def _create_pyproject(path):
        (path / "pyproject.toml").write_text(
            "[project]\nname = 'test'\n", encoding="utf-8"
        )

    mock_uv.side_effect = _create_pyproject

    defaults = {
        "backend-api": {"framework": "fastapi"},
        "cli": {"framework": "typer", "cli_type": "utility"},
        "automation": {},
        "chatbot": {"framework": "pydantic-ai", "provider": "openai"},
        "agent": {"framework": "pydantic-ai", "provider": "openai"},
        "rag": {},
        "data": {"data_type": "Data Analysis"},
        "mcp": {},
    }

    for meta in list_templates():
        assert "pre-commit" in meta.available_extras
        assert "mypy" in meta.available_extras
        slug = meta.slug
        extra_kwargs = defaults.get(slug, {})
        config = ProjectConfig(
            name=f"proj-{slug}",
            template=slug,
            use_git=False,
            extras=list(meta.available_extras),
            **extra_kwargs,
        )
        gen = ProjectGenerator()
        path = gen.generate(config)
        assert path.exists()
        assert (path / "LICENSE").exists()
        assert (path / "CHANGELOG.md").exists()
        assert (path / ".pre-commit-config.yaml").exists()
        assert "[tool.mypy]" in (path / "pyproject.toml").read_text(encoding="utf-8")
