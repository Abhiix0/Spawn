import inspect
from dataclasses import dataclass, field

from spawn.core.models import ProjectConfig
from spawn.templates.backend_api import BackendAPITemplate
from spawn.templates.cli_application import CLITemplate
from spawn.templates.automation import AutomationTemplate
from spawn.templates.chatbot import ChatbotTemplate
from spawn.templates.agent import AgentTemplate
from spawn.templates.rag import RAGTemplate
from spawn.templates.data_project import DataProjectTemplate
from spawn.templates.base import BaseTemplate


@dataclass
class TemplateMetadata:
    slug: str
    display_name: str
    description: str
    template_class: type
    available_frameworks: list[str] = field(default_factory=list)
    available_extras: list[str] = field(default_factory=list)
    available_cli_types: list[str] = field(default_factory=list)
    available_providers: list[str] = field(default_factory=list)
    available_data_types: list[str] = field(default_factory=list)


# Slugs that existed in previous versions but have been superseded.
# get_template() returns None for these, which surfaces as a clear
# SpawnError("Unknown template: fastapi") in the generator.
_REMOVED_SLUGS = {"fastapi", "python"}

TEMPLATES: dict[str, TemplateMetadata] = {
    "backend-api": TemplateMetadata(
        slug="backend-api",
        display_name="Backend API",
        description="Production-ready backend with FastAPI, Flask, or Django",
        template_class=BackendAPITemplate,
        available_frameworks=["fastapi", "flask", "django"],
        available_extras=["ruff", "pytest", "docker", "github-actions"],
    ),
    "cli": TemplateMetadata(
        slug="cli",
        display_name="CLI Application",
        description="Command-line application with Typer, Click, or Argparse",
        template_class=CLITemplate,
        available_frameworks=["typer", "click", "argparse"],
        available_extras=["ruff", "pytest", "github-actions"],
        available_cli_types=["utility", "interactive"],
    ),
    "automation": TemplateMetadata(
        slug="automation",
        display_name="Automation Tool",
        description="Workflow-based automation with logging, tasks, and integrations",
        template_class=AutomationTemplate,
        available_extras=["ruff", "pytest", "github-actions"],
    ),
    "chatbot": TemplateMetadata(
        slug="chatbot",
        display_name="AI Chatbot",
        description="Conversational AI with PydanticAI, OpenAI SDK, or LiteLLM",
        template_class=ChatbotTemplate,
        available_frameworks=["pydantic-ai", "openai-sdk", "litellm"],
        available_providers=["openai", "anthropic", "gemini", "openrouter", "ollama", "groq"],
        available_extras=["ruff", "pytest", "rich", "github-actions"],
    ),
    "agent": TemplateMetadata(
        slug="agent",
        display_name="AI Agent",
        description="Tool-calling agent with PydanticAI or OpenAI Agents SDK",
        template_class=AgentTemplate,
        available_frameworks=["pydantic-ai", "openai-agents"],
        available_providers=["openai", "anthropic", "gemini", "openrouter", "ollama", "groq"],
        available_extras=["ruff", "pytest", "github-actions"],
    ),
    "rag": TemplateMetadata(
        slug="rag",
        display_name="RAG System",
        description="Retrieval-Augmented Generation with LlamaIndex and ChromaDB",
        template_class=RAGTemplate,
        available_extras=["ruff", "pytest", "github-actions"],
    ),
    "data": TemplateMetadata(
        slug="data",
        display_name="Data Project",
        description="Data Analysis, Dashboard, ETL Pipeline, or Machine Learning project",
        template_class=DataProjectTemplate,
        available_extras=["ruff", "pytest", "github-actions"],
        available_data_types=["Data Analysis", "Dashboard", "ETL Pipeline", "Machine Learning"],
    ),
}


def get_template(template_name: str) -> BaseTemplate | None:
    """Return a no-argument template instance. Used by tests and CLI helpers."""
    metadata = TEMPLATES.get(template_name)

    if metadata is None:
        return None

    return metadata.template_class()


def instantiate_template(config: ProjectConfig) -> BaseTemplate | None:
    """
    Instantiate a template from a fully-populated ProjectConfig.

    For templates that accept framework/extras (e.g. BackendAPITemplate),
    those values are forwarded from config. For all other templates the
    no-argument constructor is used, so existing behaviour is unchanged.
    """
    metadata = TEMPLATES.get(config.template)

    if metadata is None:
        return None

    cls = metadata.template_class

    # Forward framework and extras only when the constructor accepts them.
    # Introspecting the signature avoids coupling the registry to each
    # template class individually.
    params = set(inspect.signature(cls.__init__).parameters)

    kwargs: dict = {}
    if "framework" in params:
        kwargs["framework"] = config.framework
    if "extras" in params:
        kwargs["extras"] = config.extras
    if "cli_type" in params:
        kwargs["cli_type"] = config.cli_type
    if "provider" in params:
        kwargs["provider"] = config.provider
    if "data_type" in params:
        kwargs["data_type"] = config.data_type

    return cls(**kwargs)


def get_metadata(template_name: str) -> TemplateMetadata | None:
    return TEMPLATES.get(template_name)


def list_templates() -> list[TemplateMetadata]:
    return list(TEMPLATES.values())
