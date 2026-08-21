from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.data_project.analysis import DataAnalysisTemplate
from spawn.templates.data_project.dashboard import DashboardTemplate
from spawn.templates.data_project.etl import ETLPipelineTemplate
from spawn.templates.data_project.ml import MLProjectTemplate

_SUBTEMPLATE_MAP = {
    "Data Analysis":    DataAnalysisTemplate,
    "Dashboard":        DashboardTemplate,
    "ETL Pipeline":     ETLPipelineTemplate,
    "Machine Learning": MLProjectTemplate,
}

_GITIGNORE_RULES: dict[str, str] = {
    "Data Analysis": (
        "\n# Data Analysis artifacts\n"
        "data/*.csv\n"
        "!data/sample.csv\n"
        "reports/*.png\n"
        "notebooks/.ipynb_checkpoints/\n"
    ),
    "Dashboard": (
        "\n# Dashboard artifacts\n"
        "data/*.csv\n"
        "!data/sample.csv\n"
    ),
    "ETL Pipeline": (
        "\n# ETL artifacts\n"
        "data/cleaned.csv\n"
    ),
    "Machine Learning": (
        "\n# ML artifacts\n"
        "models/*.joblib\n"
        "experiments/*.json\n"
        "data/*.csv\n"
        "!data/dataset.csv\n"
    ),
}


class _DataProjectPostInstallMixin:
    """
    Shared post_install logic for all Data Project subtemplates.

    Subtemplates must set:
      - self.extras (list[str])
      - self.data_type (str)
    and import their own CI constants from their content module.
    """

    # Subtemplates override these with their own imported constants.
    _CI_BASE: str = ""
    _CI_RUFF_STEP: str = ""
    _CI_PYTEST_STEP: str = ""

    def post_install(self, project_path: Path) -> None:
        # ── pyproject.toml extras ─────────────────────────────────────────
        needs_pyproject = any(e in self.extras for e in ("pytest", "ruff"))
        if needs_pyproject:
            pyproject = project_path / "pyproject.toml"
            current = pyproject.read_text(encoding="utf-8")
            additions = ""
            if "pytest" in self.extras:
                additions += '\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
            if "ruff" in self.extras:
                additions += "\n[tool.ruff]\nline-length = 88\n"
            if additions:
                pyproject.write_text(current + additions, encoding="utf-8")

        # ── GitHub Actions ────────────────────────────────────────────────
        if "github-actions" in self.extras and self._CI_BASE:
            workflows_path = project_path / ".github" / "workflows"
            workflows_path.mkdir(parents=True, exist_ok=True)
            ci = self._CI_BASE
            if "ruff" in self.extras:
                ci += self._CI_RUFF_STEP
            if "pytest" in self.extras:
                ci += self._CI_PYTEST_STEP
            (workflows_path / "ci.yml").write_text(ci, encoding="utf-8")

        # ── Data-artifact gitignore rules ─────────────────────────────────
        gitignore_path = project_path / ".gitignore"
        current_gitignore = gitignore_path.read_text(encoding="utf-8")
        rule = _GITIGNORE_RULES.get(self.data_type, "")
        if rule and rule.strip() not in current_gitignore:
            gitignore_path.write_text(current_gitignore + rule, encoding="utf-8")


class DataProjectTemplate(BaseTemplate):
    """
    Dispatcher that returns the appropriate per-data_type subtemplate.
    Uses __new__ so the returned object IS the subtemplate.
    """

    def __new__(
        cls,
        data_type: str = "Data Analysis",
        extras: list[str] | None = None,
    ) -> BaseTemplate:  # type: ignore[misc]
        klass = _SUBTEMPLATE_MAP.get(data_type)
        if klass is not None:
            return klass(extras=extras)
        instance = super().__new__(cls)
        return instance

    def __init__(
        self,
        data_type: str = "Data Analysis",
        extras: list[str] | None = None,
    ) -> None:
        if isinstance(self, tuple(_SUBTEMPLATE_MAP.values())):
            return
        self.data_type = data_type
        self.extras = extras or []
        super().__init__(
            name="Data Project",
            folders=[],
            starter_files=[],
            next_steps=["cd {project_name}"],
        )

    def get_dependencies(self) -> list[str]:
        return []
