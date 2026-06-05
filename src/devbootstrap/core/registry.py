from devbootstrap.templates.python_script import PythonScriptTemplate
from devbootstrap.templates.fastapi import FastAPITemplate
from devbootstrap.templates.data_science import DataScienceTemplate
from devbootstrap.templates.ml_project import MLProjectTemplate


TEMPLATES = {
    "python": PythonScriptTemplate(),
    "fastapi": FastAPITemplate(),
    "data-science": DataScienceTemplate(),
    "ml": MLProjectTemplate(),
}


def get_template(template_name: str):
    return TEMPLATES.get(template_name)