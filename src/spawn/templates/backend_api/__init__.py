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
        return BACKEND_API_README_CONTENT.format_map(context)

    def get_dependencies(self) -> list[str]:
        if self.framework == "flask":
            base_deps = list(FLASK_DEPS)
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
