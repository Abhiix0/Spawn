from spawn.core.registry import get_template, get_metadata, list_templates


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
    assert len(slugs) == 7


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
    from spawn.templates.agent import AgentTemplate
    from spawn.core.registry import get_template
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
