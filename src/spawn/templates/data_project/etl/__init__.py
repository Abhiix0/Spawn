from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.data_project.etl.content import (
    ETL_RAW_CSV,
    ETL_CLEAN_CONTENT,
    ETL_RUN_CONTENT,
    ETL_ENV_CONTENT,
    ETL_TEST_CONTENT,
    make_readme,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
)

FOLDERS = ["data", "pipelines", "src", "tests"]

FILES = [
    ("data/raw.csv", ETL_RAW_CSV),
    ("pipelines/__init__.py", ""),
    ("pipelines/clean_data.py", ETL_CLEAN_CONTENT),
    ("pipelines/run.py", ETL_RUN_CONTENT),
    ("tests/test_etl.py", ETL_TEST_CONTENT),
    ("tests/__init__.py", ""),
    ("src/__init__.py", ""),
    (".env.example", ETL_ENV_CONTENT),
]

DEPENDENCIES = ["pandas", "python-dotenv"]

NEXT_STEPS = [
    "cd {project_name}",
    "Rename .env.example to .env if you want custom paths",
    "uv run python -m pipelines.run",
]


class ETLPipelineTemplate(BaseTemplate):
    data_type = "ETL Pipeline"
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
