from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.data_project.etl.content import (
    ETL_RAW_CSV,
    ETL_CLEAN_CONTENT,
    ETL_RUN_CONTENT,
    ETL_ENV_CONTENT,
    ETL_TEST_CONTENT,
    make_readme,
)

FOLDERS = ["data", "pipelines", "src", "tests"]

FILES = [
    ("data/raw.csv",               ETL_RAW_CSV),
    ("pipelines/__init__.py",      ""),
    ("pipelines/clean_data.py",    ETL_CLEAN_CONTENT),
    ("pipelines/run.py",           ETL_RUN_CONTENT),
    ("tests/test_etl.py",          ETL_TEST_CONTENT),
    ("tests/__init__.py",          ""),
    ("src/__init__.py",            ""),
    (".env.example",               ETL_ENV_CONTENT),
]

DEPENDENCIES = ["pandas", "python-dotenv"]

NEXT_STEPS = [
    "cd {project_name}",
    "Rename .env.example to .env if you want custom paths",
    "uv run python pipelines/run.py",
]


class ETLPipelineTemplate(BaseTemplate):
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
        if not any(e in self.extras for e in ("pytest", "ruff")):
            return
        pyproject = project_path / "pyproject.toml"
        current = pyproject.read_text(encoding="utf-8")
        additions = ""
        if "pytest" in self.extras:
            additions += '\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
        if "ruff" in self.extras:
            additions += "\n[tool.ruff]\nline-length = 88\n"
        if additions:
            pyproject.write_text(current + additions, encoding="utf-8")
