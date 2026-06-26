import inspect
from dataclasses import dataclass, field

from spawn.core.models import ProjectConfig
# Kept for future re-registration
# from spawn.templates.python_script import PythonScriptTemplate
# from spawn.templates.data_science import DataScienceTemplate
# from spawn.templates.ml_project import MLProjectTemplate
from spawn.templates.backend_api import BackendAPITemplate
from spawn.templates.cli_application import CLITemplate
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


# Slugs that existed in previous versions but have been superseded.
# get_template() returns None for these, which surfaces as a clear
# SpawnError("Unknown template: fastapi") in the generator.
_REMOVED_SLUGS = {"fastapi", "python", "data-science", "ml"}

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

    return cls(**kwargs)


def get_metadata(template_name: str) -> TemplateMetadata | None:
    return TEMPLATES.get(template_name)


def list_templates() -> list[TemplateMetadata]:
    return list(TEMPLATES.values())
