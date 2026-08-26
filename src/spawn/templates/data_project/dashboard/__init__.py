from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.data_project.dashboard.content import (
    DASHBOARD_SAMPLE_CSV,
    DASHBOARD_APP_CONTENT,
    DASHBOARD_TEST_CONTENT,
    make_readme,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
)

FOLDERS = ["data", "dashboard", "src", "tests"]

FILES = [
    ("data/sample.csv", DASHBOARD_SAMPLE_CSV),
    ("dashboard/__init__.py", ""),
    ("dashboard/app.py", DASHBOARD_APP_CONTENT),
    ("tests/test_dashboard.py", DASHBOARD_TEST_CONTENT),
    ("tests/__init__.py", ""),
    ("src/__init__.py", ""),
]

DEPENDENCIES = ["streamlit", "pandas", "plotly"]

NEXT_STEPS = [
    "cd {project_name}",
    "uv run streamlit run dashboard/app.py",
]


class DashboardTemplate(BaseTemplate):
    data_type = "Dashboard"
    _CI_BASE = GITHUB_ACTIONS_CI_BASE
    _CI_RUFF_STEP = GITHUB_ACTIONS_CI_RUFF_STEP
    _CI_PYTEST_STEP = GITHUB_ACTIONS_CI_PYTEST_STEP

    def __init__(self, extras: list[str] | None = None) -> None:
        self.extras = extras or []
        super().__init__(
            name="Data Project",
            folders=list(FOLDERS),
            starter_files=list(FILES),
            next_steps=list(NEXT_STEPS),
        )

    def get_readme_content(self, context: dict) -> str | None:
        return make_readme().format_map(context)

    def get_dependencies(self) -> list[str]:
        base = list(DEPENDENCIES)
        if "pytest" in self.extras:
            base.append("pytest")
        if "ruff" in self.extras:
            base.append("ruff")
        return base

    def post_install(self, project_path: Path) -> None:
        from spawn.templates.data_project import _DataProjectPostInstallMixin

        _DataProjectPostInstallMixin.post_install(self, project_path)  # type: ignore[arg-type]
