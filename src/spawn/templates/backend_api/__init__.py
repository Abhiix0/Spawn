from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.backend_api.content import (
    MAIN_CONTENT,
    HEALTH_ROUTER_CONTENT,
    CONFIG_CONTENT,
    TEST_HEALTH_CONTENT,
    ENV_EXAMPLE_CONTENT,
    BACKEND_API_README_CONTENT,
    INIT_CONTENT,
)


class BackendAPITemplate(BaseTemplate):
    def __init__(
        self,
        framework: str | None = None,
        extras: list[str] | None = None,
    ):
        self.framework = framework
        self.extras = extras or []
        super().__init__(
            name="Backend API",
            folders=[
                "app/api/routes",
                "app/core",
                "app/models",
                "app/schemas",
                "app/services",
                "tests",
            ],
            starter_files=[
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
            ],
        )

    def get_readme_content(self, context: dict) -> str | None:
        return BACKEND_API_README_CONTENT.format_map(context)

    def get_dependencies(self) -> list[str]:
        deps = [
            "fastapi",
            "uvicorn[standard]",
            "pydantic-settings",
        ]

        if "pytest" in self.extras:
            deps += ["pytest", "httpx"]

        if "ruff" in self.extras:
            deps += ["ruff"]

        return deps

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
