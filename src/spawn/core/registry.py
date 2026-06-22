from dataclasses import dataclass, field

from spawn.templates.python_script import PythonScriptTemplate
from spawn.templates.fastapi_template import FastAPITemplate
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


TEMPLATES: dict[str, TemplateMetadata] = {
    "python": TemplateMetadata(
        slug="python",
        display_name="Python Script",
        description="Simple Python script with src/ and tests/",
        template_class=PythonScriptTemplate,
    ),
    "fastapi": TemplateMetadata(
        slug="fastapi",
        display_name="FastAPI",
        description="FastAPI web application",
        template_class=FastAPITemplate,
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
    "backend-api": TemplateMetadata(
        slug="backend-api",
        display_name="Backend API",
        description="Production-ready FastAPI backend with routes and config",
        template_class=BackendAPITemplate,
        available_frameworks=["fastapi"],
        available_extras=["ruff", "pytest"],
    ),
}


def get_template(template_name: str) -> BaseTemplate | None:
    metadata = TEMPLATES.get(template_name)

    if metadata is None:
        return None

    return metadata.template_class()


def get_metadata(template_name: str) -> TemplateMetadata | None:
    return TEMPLATES.get(template_name)


def list_templates() -> list[TemplateMetadata]:
    return list(TEMPLATES.values())
