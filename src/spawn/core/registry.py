from spawn.templates.python_script import PythonScriptTemplate
from spawn.templates.fastapi_template import FastAPITemplate
from spawn.templates.data_science import DataScienceTemplate
from spawn.templates.ml_project import MLProjectTemplate
from spawn.templates.base import BaseTemplate


TEMPLATES = {
    "python": PythonScriptTemplate,
    "fastapi": FastAPITemplate,
    "data-science": DataScienceTemplate,
    "ml": MLProjectTemplate,
}


def get_template(template_name: str) -> BaseTemplate | None:
    template_class = TEMPLATES.get(template_name)

    if template_class is None:
        return None

    return template_class()