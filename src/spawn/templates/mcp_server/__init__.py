from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.mcp_server.content import (
    INIT_CONTENT,
    SERVER_CONTENT,
    TEST_CONTENT,
    ENV_CONTENT,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
    make_readme,
    make_agents_md,
)

MCP_SERVER_FOLDERS = [
    "src",
    "tests",
]


def _build_files() -> list:
    return [
        ("src/__init__.py", INIT_CONTENT),
        ("src/server.py", SERVER_CONTENT),
        ("tests/__init__.py", INIT_CONTENT),
        ("tests/test_server.py", TEST_CONTENT),
        (".env.example", ENV_CONTENT),
    ]


class MCPServerTemplate(BaseTemplate):
    def __init__(self, extras: list[str] | None = None) -> None:
        self.extras = extras or []

        super().__init__(
            name="MCP Server",
            folders=list(MCP_SERVER_FOLDERS),
            starter_files=_build_files(),
            next_steps=[
                "cd {project_name}",
                "uv run python -m src.server",
                "Add this server to Claude Desktop's config (see README.md)",
            ],
        )

    def get_readme_content(self, context: dict) -> str | None:
        return make_readme().format_map(context)

    def get_agents_md_content(self, context: dict) -> str | None:
        return make_agents_md().format_map(context)

    def get_dependencies(self) -> list[str]:
        base = ["mcp"]
        if "pytest" in self.extras:
            base.append("pytest")
        if "ruff" in self.extras:
            base.append("ruff")
        return base

    def post_install(self, project_path: Path) -> None:
        pyproject = project_path / "pyproject.toml"
        current = pyproject.read_text(encoding="utf-8")
        additions = ""

        if "pytest" in self.extras:
            additions += '\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'

        if "ruff" in self.extras:
            additions += "\n[tool.ruff]\nline-length = 88\n"

        if additions:
            pyproject.write_text(current + additions, encoding="utf-8")

        if "github-actions" in self.extras:
            workflows_path = project_path / ".github" / "workflows"
            workflows_path.mkdir(parents=True, exist_ok=True)
            ci = GITHUB_ACTIONS_CI_BASE
            if "ruff" in self.extras:
                ci += GITHUB_ACTIONS_CI_RUFF_STEP
            if "pytest" in self.extras:
                ci += GITHUB_ACTIONS_CI_PYTEST_STEP
            (workflows_path / "ci.yml").write_text(ci, encoding="utf-8")
