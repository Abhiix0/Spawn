from spawn.templates.python_script import PythonScriptTemplate
from spawn.templates.data_science import DataScienceTemplate
from spawn.templates.ml_project import MLProjectTemplate
from spawn.templates.backend_api import BackendAPITemplate


def test_python_template_has_starter_files():
    template = PythonScriptTemplate()

    assert len(template.starter_files) > 0
    paths = [path for path, _ in template.starter_files]
    assert "main.py" in paths


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


# ---------------------------------------------------------------------------
# Flask framework
# ---------------------------------------------------------------------------


def test_backend_api_flask_folders():
    template = BackendAPITemplate(framework="flask")
    assert "app/routes" in template.folders
    assert "tests" in template.folders


def test_backend_api_flask_starter_files():
    template = BackendAPITemplate(framework="flask")
    paths = [path for path, _ in template.starter_files]
    assert "run.py" in paths
    assert "app/__init__.py" in paths
    assert "app/routes/health.py" in paths
    assert "app/config.py" in paths
    assert "tests/test_health.py" in paths


def test_backend_api_flask_dependencies():
    template = BackendAPITemplate(framework="flask")
    deps = template.get_dependencies()
    assert "flask" in deps
    assert "python-dotenv" in deps
    assert "fastapi" not in deps


def test_backend_api_flask_readme():
    template = BackendAPITemplate(framework="flask")
    readme = template.get_readme_content({"project_name": "my-api"})
    assert readme is not None
    assert "my-api" in readme
    assert "uv run python run.py" in readme


# ---------------------------------------------------------------------------
# Django framework
# ---------------------------------------------------------------------------


def test_backend_api_django_folders():
    template = BackendAPITemplate(framework="django")
    assert "config" in template.folders
    assert "apps/health" in template.folders


def test_backend_api_django_starter_files():
    template = BackendAPITemplate(framework="django")
    paths = [path for path, _ in template.starter_files]
    assert "manage.py" in paths
    assert "config/settings.py" in paths
    assert "config/urls.py" in paths
    assert "apps/health/views.py" in paths
    assert "apps/health/tests.py" in paths


def test_backend_api_django_dependencies():
    template = BackendAPITemplate(framework="django")
    deps = template.get_dependencies()
    assert "django" in deps
    assert "fastapi" not in deps
    assert "flask" not in deps


def test_backend_api_django_readme():
    template = BackendAPITemplate(framework="django")
    readme = template.get_readme_content({"project_name": "my-api"})
    assert readme is not None
    assert "my-api" in readme
    assert "manage.py runserver" in readme


# ---------------------------------------------------------------------------
# Docker extra
# ---------------------------------------------------------------------------


def test_backend_api_docker_extra_fastapi(tmp_path):
    template = BackendAPITemplate(framework="fastapi", extras=["docker"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    template.post_install(tmp_path)
    assert (tmp_path / "Dockerfile").exists()
    assert (tmp_path / ".dockerignore").exists()
    content = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    assert "uvicorn" in content


def test_backend_api_docker_extra_flask(tmp_path):
    template = BackendAPITemplate(framework="flask", extras=["docker"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    template.post_install(tmp_path)
    dockerfile = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    assert "run.py" in dockerfile


def test_backend_api_docker_extra_django(tmp_path):
    template = BackendAPITemplate(framework="django", extras=["docker"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    template.post_install(tmp_path)
    dockerfile = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    assert "manage.py" in dockerfile


# ---------------------------------------------------------------------------
# GitHub Actions extra
# ---------------------------------------------------------------------------


def test_backend_api_github_actions_extra(tmp_path):
    template = BackendAPITemplate(framework="fastapi", extras=["github-actions", "ruff", "pytest"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    template.post_install(tmp_path)
    ci_path = tmp_path / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists()
    content = ci_path.read_text(encoding="utf-8")
    assert "uv sync" in content
    assert "uv run pytest" in content
    assert "uv run ruff check ." in content


def test_ci_without_ruff_does_not_include_ruff_step():
    from spawn.templates.backend_api.content import (
        GITHUB_ACTIONS_CI_BASE,
        GITHUB_ACTIONS_CI_RUFF_STEP,
        GITHUB_ACTIONS_CI_PYTEST_STEP,
    )

    t = BackendAPITemplate(framework="fastapi", extras=["github-actions"])
    ci = GITHUB_ACTIONS_CI_BASE
    if "ruff" in t.extras:
        ci += GITHUB_ACTIONS_CI_RUFF_STEP
    if "pytest" in t.extras:
        ci += GITHUB_ACTIONS_CI_PYTEST_STEP

    assert "ruff" not in ci
    assert "pytest" not in ci
    assert "uv sync" in ci


def test_ci_with_ruff_and_pytest_includes_both_steps():
    from spawn.templates.backend_api.content import (
        GITHUB_ACTIONS_CI_BASE,
        GITHUB_ACTIONS_CI_RUFF_STEP,
        GITHUB_ACTIONS_CI_PYTEST_STEP,
    )

    t = BackendAPITemplate(
        framework="fastapi", extras=["github-actions", "ruff", "pytest"]
    )
    ci = GITHUB_ACTIONS_CI_BASE
    if "ruff" in t.extras:
        ci += GITHUB_ACTIONS_CI_RUFF_STEP
    if "pytest" in t.extras:
        ci += GITHUB_ACTIONS_CI_PYTEST_STEP

    assert "uv run ruff check ." in ci
    assert "uv run pytest" in ci


def test_gitignore_does_not_ignore_uv_lock():
    from spawn.templates.shared_content import GITIGNORE_CONTENT

    lines = GITIGNORE_CONTENT.splitlines()
    assert "uv.lock" not in lines


def test_gitignore_excludes_log_files_not_logs_dir():
    from spawn.templates.shared_content import GITIGNORE_CONTENT

    lines = GITIGNORE_CONTENT.splitlines()
    assert "logs/*.log" in lines
    assert "logs/" not in lines
    assert "logs" not in lines


def test_flask_dockerfile_exposes_port_5000():
    from spawn.templates.backend_api.content import DOCKERFILE_FLASK_CONTENT

    assert "EXPOSE 5000" in DOCKERFILE_FLASK_CONTENT
    assert "EXPOSE 8000" not in DOCKERFILE_FLASK_CONTENT
