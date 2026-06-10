from spawn.templates.fastapi import FastAPITemplate
from spawn.templates.python_script import PythonScriptTemplate
from spawn.templates.data_science import DataScienceTemplate
from spawn.templates.ml_project import MLProjectTemplate


def test_fastapi_template():
    template = FastAPITemplate()

    assert "app" in template.folders
    assert "tests" in template.folders


def test_python_template_has_starter_files():
    template = PythonScriptTemplate()

    assert len(template.starter_files) > 0
    paths = [path for path, _ in template.starter_files]
    assert "main.py" in paths


def test_fastapi_template_has_starter_files():
    template = FastAPITemplate()

    assert len(template.starter_files) > 0
    paths = [path for path, _ in template.starter_files]
    assert "app/main.py" in paths


def test_data_science_template_has_starter_files():
    template = DataScienceTemplate()

    assert len(template.starter_files) > 0
    paths = [path for path, _ in template.starter_files]
    assert "main.py" in paths


def test_ml_template_has_starter_files():
    template = MLProjectTemplate()

    assert len(template.starter_files) > 0
    paths = [path for path, _ in template.starter_files]
    assert "main.py" in paths


def test_starter_file_paths_are_strings():
    for template in [
        PythonScriptTemplate(),
        FastAPITemplate(),
        DataScienceTemplate(),
        MLProjectTemplate(),
    ]:
        for path, content in template.starter_files:
            assert isinstance(path, str)
            assert isinstance(content, str)
