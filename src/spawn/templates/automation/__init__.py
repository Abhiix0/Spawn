from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.automation.content import (
    INIT_CONTENT,
    MAIN_CONTENT,
    LOGGER_CONTENT,
    REPORT_WORKFLOW_CONTENT,
    DATA_TASK_CONTENT,
    REPORT_TASK_CONTENT,
    TEST_CONTENT,
    ENV_EXAMPLE_CONTENT,
    README_CONTENT,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
)

AUTOMATION_FOLDERS = [
    "src/workflows",
    "src/tasks",
    "src/integrations",
    "src/utils",
    "logs",
    "tests",
]

AUTOMATION_FILES = [
    ("src/__init__.py", INIT_CONTENT),
    ("src/workflows/__init__.py", INIT_CONTENT),
    ("src/workflows/report_workflow.py", REPORT_WORKFLOW_CONTENT),
    ("src/tasks/__init__.py", INIT_CONTENT),
    ("src/tasks/data_task.py", DATA_TASK_CONTENT),
    ("src/tasks/report_task.py", REPORT_TASK_CONTENT),
    ("src/integrations/__init__.py", INIT_CONTENT),
    ("src/utils/__init__.py", INIT_CONTENT),
    ("src/utils/logger.py", LOGGER_CONTENT),
    ("src/main.py", MAIN_CONTENT),
    ("logs/.gitkeep", INIT_CONTENT),
    ("tests/__init__.py", INIT_CONTENT),
    ("tests/test_automation.py", TEST_CONTENT),
    (".env.example", ENV_EXAMPLE_CONTENT),
]


class AutomationTemplate(BaseTemplate):
    def __init__(
        self,
        extras: list[str] | None = None,
    ) -> None:
        self.extras = extras or []
        super().__init__(
            name="Automation Tool",
            folders=AUTOMATION_FOLDERS,
            starter_files=AUTOMATION_FILES,
            next_steps=[
                "cd {project_name}",
                "uv run python -m src.main",
            ],
        )

    def get_readme_content(self, context: dict) -> str | None:
        return README_CONTENT.format_map(context)

    def get_dependencies(self) -> list[str]:
        base = ["requests", "python-dotenv"]
        if "pytest" in self.extras:
            base += ["pytest"]
        if "ruff" in self.extras:
            base += ["ruff"]
        return base

    def post_install(self, project_path: Path) -> None:
        pyproject = project_path / "pyproject.toml"
        current = pyproject.read_text(encoding="utf-8")
        additions = ""

        if "pytest" in self.extras:
            additions += (
                "\n[tool.pytest.ini_options]\n"
                'testpaths = ["tests"]\n'
            )

        if "ruff" in self.extras:
            additions += "\n[tool.ruff]\nline-length = 88\n"

        if additions:
            pyproject.write_text(current + additions, encoding="utf-8")

        if "github-actions" in self.extras:
            workflows_path = project_path / ".github" / "workflows"
            workflows_path.mkdir(parents=True, exist_ok=True)
            ci_content = GITHUB_ACTIONS_CI_BASE
            if "ruff" in self.extras:
                ci_content += GITHUB_ACTIONS_CI_RUFF_STEP
            if "pytest" in self.extras:
                ci_content += GITHUB_ACTIONS_CI_PYTEST_STEP
            (workflows_path / "ci.yml").write_text(
                ci_content, encoding="utf-8"
            )
