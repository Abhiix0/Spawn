from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.backend_api.content import (
    # FastAPI
    MAIN_CONTENT,
    HEALTH_ROUTER_CONTENT,
    CONFIG_CONTENT,
    TEST_HEALTH_CONTENT,
    ENV_EXAMPLE_CONTENT,
    BACKEND_API_README_CONTENT,
    INIT_CONTENT,
    # Flask
    FLASK_APP_INIT_CONTENT,
    FLASK_CONFIG_CONTENT,
    FLASK_HEALTH_CONTENT,
    FLASK_RUN_CONTENT,
    FLASK_TEST_HEALTH_CONTENT,
    FLASK_ENV_EXAMPLE_CONTENT,
    FLASK_README_CONTENT,
    # Django
    DJANGO_MANAGE_CONTENT,
    DJANGO_SETTINGS_CONTENT,
    DJANGO_URLS_CONTENT,
    DJANGO_ASGI_CONTENT,
    DJANGO_WSGI_CONTENT,
    DJANGO_HEALTH_VIEWS_CONTENT,
    DJANGO_HEALTH_URLS_CONTENT,
    DJANGO_HEALTH_TESTS_CONTENT,
    DJANGO_README_CONTENT,
    # Docker
    DOCKERFILE_FASTAPI_CONTENT,
    DOCKERFILE_FLASK_CONTENT,
    DOCKERFILE_DJANGO_CONTENT,
    DOCKERIGNORE_CONTENT,
    # GitHub Actions
    GITHUB_ACTIONS_CI_CONTENT,
)

# ---------------------------------------------------------------------------
# Framework definitions
# ---------------------------------------------------------------------------

FASTAPI_FOLDERS = [
    "app/api/routes",
    "app/core",
    "app/models",
    "app/schemas",
    "app/services",
    "tests",
]

FASTAPI_FILES = [
    ("app/__init__.py", INIT_CONTENT),
    ("app/api/__init__.py", INIT_CONTENT),
    ("app/api/routes/__init__.py", INIT_CONTENT),
    ("app/api/routes/health.py", HEALTH_ROUTER_CONTENT),
    ("app/main.py", MAIN_CONTENT),
    ("app/core/__init__.py", INIT_CONTENT),
    ("app/core/config.py", CONFIG_CONTENT),
    ("tests/__init__.py", INIT_CONTENT),
    ("tests/test_health.py", TEST_HEALTH_CONTENT),
    (".env.example", ENV_EXAMPLE_CONTENT),
]

FASTAPI_DEPS = [
    "fastapi",
    "uvicorn[standard]",
    "pydantic-settings",
]

FLASK_FOLDERS = [
    "app/routes",
    "app/models",
    "app/services",
    "tests",
]

FLASK_FILES = [
    ("app/__init__.py", FLASK_APP_INIT_CONTENT),
    ("app/routes/__init__.py", INIT_CONTENT),
    ("app/routes/health.py", FLASK_HEALTH_CONTENT),
    ("app/models/__init__.py", INIT_CONTENT),
    ("app/services/__init__.py", INIT_CONTENT),
    ("app/config.py", FLASK_CONFIG_CONTENT),
    ("run.py", FLASK_RUN_CONTENT),
    ("tests/__init__.py", INIT_CONTENT),
    ("tests/test_health.py", FLASK_TEST_HEALTH_CONTENT),
    (".env.example", FLASK_ENV_EXAMPLE_CONTENT),
]

FLASK_DEPS = [
    "flask",
    "python-dotenv",
]

DJANGO_FOLDERS = [
    "config",
    "apps/health",
]

DJANGO_FILES = [
    ("manage.py", DJANGO_MANAGE_CONTENT),
    ("config/__init__.py", INIT_CONTENT),
    ("config/settings.py", DJANGO_SETTINGS_CONTENT),
    ("config/urls.py", DJANGO_URLS_CONTENT),
    ("config/asgi.py", DJANGO_ASGI_CONTENT),
    ("config/wsgi.py", DJANGO_WSGI_CONTENT),
    ("apps/__init__.py", INIT_CONTENT),
    ("apps/health/__init__.py", INIT_CONTENT),
    ("apps/health/views.py", DJANGO_HEALTH_VIEWS_CONTENT),
    ("apps/health/urls.py", DJANGO_HEALTH_URLS_CONTENT),
    ("apps/health/tests.py", DJANGO_HEALTH_TESTS_CONTENT),
]

DJANGO_DEPS = [
    "django",
]


class BackendAPITemplate(BaseTemplate):
    def __init__(
        self,
        framework: str | None = None,
        extras: list[str] | None = None,
    ):
        self.framework = framework
        self.extras = extras or []

        if framework == "flask":
            folders = FLASK_FOLDERS
            files = FLASK_FILES
        elif framework == "django":
            folders = DJANGO_FOLDERS
            files = DJANGO_FILES
        else:
            # Default to fastapi for None or "fastapi"
            folders = FASTAPI_FOLDERS
            files = FASTAPI_FILES

        super().__init__(
            name="Backend API",
            folders=folders,
            starter_files=files,
        )

    def get_readme_content(self, context: dict) -> str | None:
        if self.framework == "flask":
            return FLASK_README_CONTENT.format_map(context)
        if self.framework == "django":
            return DJANGO_README_CONTENT.format_map(context)
        return BACKEND_API_README_CONTENT.format_map(context)

    def get_dependencies(self) -> list[str]:
        if self.framework == "flask":
            base_deps = list(FLASK_DEPS)
        elif self.framework == "django":
            base_deps = list(DJANGO_DEPS)
        else:
            base_deps = list(FASTAPI_DEPS)

        if "pytest" in self.extras:
            base_deps += ["pytest", "httpx"]

        if "ruff" in self.extras:
            base_deps += ["ruff"]

        return base_deps

    def post_install(self, project_path: Path) -> None:
        pyproject = project_path / "pyproject.toml"
        current = pyproject.read_text(encoding="utf-8")
        additions = ""

        if "pytest" in self.extras:
            additions += (
                "\n[tool.pytest.ini_options]\n"
                'filterwarnings = [\n'
                '    "ignore::DeprecationWarning:starlette",\n'
                '    "ignore::DeprecationWarning:httpx",\n'
                "]\n"
            )

        if "ruff" in self.extras:
            additions += "\n[tool.ruff]\nline-length = 88\n"

        if additions:
            pyproject.write_text(current + additions, encoding="utf-8")

        if "docker" in self.extras:
            if self.framework == "flask":
                dockerfile_content = DOCKERFILE_FLASK_CONTENT
            elif self.framework == "django":
                dockerfile_content = DOCKERFILE_DJANGO_CONTENT
            else:
                dockerfile_content = DOCKERFILE_FASTAPI_CONTENT

            (project_path / "Dockerfile").write_text(
                dockerfile_content, encoding="utf-8"
            )
            (project_path / ".dockerignore").write_text(
                DOCKERIGNORE_CONTENT, encoding="utf-8"
            )

        if "github-actions" in self.extras:
            workflows_path = project_path / ".github" / "workflows"
            workflows_path.mkdir(parents=True, exist_ok=True)
            (workflows_path / "ci.yml").write_text(
                GITHUB_ACTIONS_CI_CONTENT, encoding="utf-8"
            )
