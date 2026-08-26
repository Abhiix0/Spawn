from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.data_project.ml.content import (
    ML_SAMPLE_CSV,
    ML_TRAIN_CONTENT,
    ML_TEST_CONTENT,
    make_readme,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
)

FOLDERS = ["data", "models", "experiments", "src", "tests"]

FILES = [
    ("data/dataset.csv", ML_SAMPLE_CSV),
    ("src/__init__.py", ""),
    ("src/train.py", ML_TRAIN_CONTENT),
    ("tests/test_ml.py", ML_TEST_CONTENT),
    ("tests/__init__.py", ""),
    ("models/.gitkeep", ""),
    ("experiments/.gitkeep", ""),
]

DEPENDENCIES = ["pandas", "numpy", "scikit-learn", "joblib"]

NEXT_STEPS = [
    "cd {project_name}",
    "uv run python src/train.py",
]


class MLProjectTemplate(BaseTemplate):
    data_type = "Machine Learning"
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
