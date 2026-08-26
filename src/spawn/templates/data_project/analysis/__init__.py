from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.data_project.analysis.content import (
    SAMPLE_CSV,
    NOTEBOOK_CONTENT,
    TEST_CONTENT,
    make_readme,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
)

FOLDERS = ["data", "notebooks", "reports", "src", "tests"]

FILES = [
    ("data/sample.csv", SAMPLE_CSV),
    ("notebooks/analysis.ipynb", NOTEBOOK_CONTENT),
    ("tests/test_analysis.py", TEST_CONTENT),
    ("tests/__init__.py", ""),
    ("reports/.gitkeep", ""),
    ("src/__init__.py", ""),
]

DEPENDENCIES = ["pandas", "numpy", "jupyter", "matplotlib"]

NEXT_STEPS = [
    "cd {project_name}",
    "uv run jupyter notebook",
]


class DataAnalysisTemplate(BaseTemplate):
    data_type = "Data Analysis"
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

    def generate(self, project_path: Path, context: dict) -> None:
        """Write files, skipping format_map for .ipynb (raw JSON)."""
        for folder in self.folders:
            (project_path / folder).mkdir(parents=True, exist_ok=True)

        for relative_path, content in self.starter_files:
            file_path = project_path / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if relative_path.endswith(".ipynb"):
                file_path.write_text(content, encoding="utf-8")
            else:
                file_path.write_text(content.format_map(context), encoding="utf-8")

    def post_install(self, project_path: Path) -> None:
        from spawn.templates.data_project import _DataProjectPostInstallMixin

        _DataProjectPostInstallMixin.post_install(self, project_path)  # type: ignore[arg-type]
