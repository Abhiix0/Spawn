from spawn.templates.fastapi_template import FastAPITemplate
from spawn.templates.python_script import PythonScriptTemplate
from spawn.templates.data_science import DataScienceTemplate
from spawn.templates.ml_project import MLProjectTemplate
from spawn.templates.backend_api import BackendAPITemplate


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


def test_backend_api_template_default():
    template = BackendAPITemplate()
    assert template.name == "Backend API"
    assert template.framework is None
    assert template.extras == []


def test_backend_api_template_folders():
    template = BackendAPITemplate()
    assert "app/api/routes" in template.folders
    assert "app/core" in template.folders
    assert "app/models" in template.folders
    assert "app/schemas" in template.folders
    assert "app/services" in template.folders
    assert "tests" in template.folders


def test_backend_api_template_has_starter_files():
    template = BackendAPITemplate()
    assert len(template.starter_files) > 0
    paths = [path for path, _ in template.starter_files]
    assert "app/main.py" in paths
    assert "app/api/routes/health.py" in paths
    assert "app/core/config.py" in paths
    assert "tests/test_health.py" in paths
    assert ".env.example" in paths


def test_backend_api_starter_file_paths_are_strings():
    template = BackendAPITemplate()
    for path, content in template.starter_files:
        assert isinstance(path, str)
        assert isinstance(content, str)


def test_backend_api_base_dependencies():
    template = BackendAPITemplate()
    deps = template.get_dependencies()
    assert "fastapi" in deps
    assert "uvicorn[standard]" in deps
    assert "pydantic-settings" in deps


def test_backend_api_extras_add_deps():
    template = BackendAPITemplate(extras=["ruff", "pytest"])
    deps = template.get_dependencies()
    assert "ruff" in deps
    assert "pytest" in deps
    assert "httpx" in deps


def test_backend_api_no_extras_excludes_optional_deps():
    template = BackendAPITemplate(extras=[])
    deps = template.get_dependencies()
    assert "ruff" not in deps
    assert "pytest" not in deps
    assert "httpx" not in deps


def test_backend_api_readme_content_contains_project_name():
    template = BackendAPITemplate()
    readme = template.get_readme_content({"project_name": "my-api"})
    assert readme is not None
    assert "my-api" in readme
    assert "uv run uvicorn" in readme
