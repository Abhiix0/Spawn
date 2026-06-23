import inspect
from dataclasses import dataclass, field

from spawn.core.models import ProjectConfig
from spawn.templates.python_script import PythonScriptTemplate
from spawn.templates.data_science import DataScienceTemplate
from spawn.templates.ml_project import MLProjectTemplate
from spawn.templates.backend_api import BackendAPITemplate
from spawn.templates.base import BaseTemplate


@dataclass
class TemplateMetadata:
    slug: str
    display_name: str
    description: str
    template_class: type
    available_frameworks: list[str] = field(default_factory=list)
    available_extras: list[str] = field(default_factory=list)


# Slugs that existed in v0.2.0 but have been superseded.
# get_template() returns None for these, which surfaces as a clear
# SpawnError("Unknown template: fastapi") in the generator.
_REMOVED_SLUGS = {"fastapi"}

TEMPLATES: dict[str, TemplateMetadata] = {
    "backend-api": TemplateMetadata(
        slug="backend-api",
        display_name="Backend API",
        description="Production-ready backend with FastAPI, Flask, or Django",
        template_class=BackendAPITemplate,
        available_frameworks=["fastapi", "flask", "django"],
        available_extras=["ruff", "pytest", "docker", "github-actions"],
    ),
    "python": TemplateMetadata(
        slug="python",
        display_name="Python Script",
        description="Simple Python script with src/ and tests/",
        template_class=PythonScriptTemplate,
    ),
    "data-science": TemplateMetadata(
        slug="data-science",
        display_name="Data Science",
        description="Data science project with notebooks and data directories",
        template_class=DataScienceTemplate,
    ),
    "ml": TemplateMetadata(
        slug="ml",
        display_name="ML Project",
        description="Machine learning project with models and data directories",
        template_class=MLProjectTemplate,
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

    return cls(**kwargs)


def get_metadata(template_name: str) -> TemplateMetadata | None:
    return TEMPLATES.get(template_name)


def list_templates() -> list[TemplateMetadata]:
    return list(TEMPLATES.values())
