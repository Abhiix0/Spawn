from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.data_project.content import (
    DATA_ANALYSIS_SAMPLE_CSV,
    DATA_ANALYSIS_NOTEBOOK_CONTENT,
    DATA_ANALYSIS_TEST_CONTENT,
    make_data_analysis_readme,
)

DATA_ANALYSIS_FOLDERS = ["data", "notebooks", "reports", "src", "tests"]

DATA_ANALYSIS_FILES = [
    ("data/sample.csv",              DATA_ANALYSIS_SAMPLE_CSV),
    ("notebooks/analysis.ipynb",     DATA_ANALYSIS_NOTEBOOK_CONTENT),
    ("tests/test_analysis.py",       DATA_ANALYSIS_TEST_CONTENT),
    ("tests/__init__.py",            ""),
    ("reports/.gitkeep",             ""),
    ("src/__init__.py",              ""),
]


class DataProjectTemplate(BaseTemplate):
    def __init__(
        self,
        data_type: str = "Data Analysis",
        extras: list[str] | None = None,
    ) -> None:
        self.data_type = data_type
        self.extras = extras or []

        if self.data_type == "Data Analysis":
            folders = list(DATA_ANALYSIS_FOLDERS)
            starter_files = list(DATA_ANALYSIS_FILES)
            next_steps = [
                "cd {project_name}",
                "uv run jupyter notebook",
            ]
        else:
            folders = []
            starter_files = []
            next_steps = ["cd {project_name}"]

        super().__init__(
            name="Data Project",
            folders=folders,
            starter_files=starter_files,
            next_steps=next_steps,
        )

    def get_readme_content(self, context: dict) -> str | None:
        if self.data_type == "Data Analysis":
            return make_data_analysis_readme().format_map(context)
        return None

    def get_dependencies(self) -> list[str]:
        if self.data_type == "Data Analysis":
            base = ["pandas", "numpy", "jupyter", "matplotlib"]
        else:
            base = []

        if "pytest" in self.extras:
            base.append("pytest")
        if "ruff" in self.extras:
            base.append("ruff")

        return base

    def generate(self, project_path: "Path", context: dict) -> None:  # type: ignore[override]
        """Override to skip format_map for binary-like files (e.g. .ipynb)."""
        from pathlib import Path as _Path

        for folder in self.folders:
            (project_path / folder).mkdir(parents=True, exist_ok=True)

        # Extensions that must be written verbatim — no format_map substitution
        _VERBATIM_EXTS = {".ipynb"}

        for relative_path, content_template in self.starter_files:
            file_path = project_path / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if _Path(relative_path).suffix in _VERBATIM_EXTS:
                file_path.write_text(content_template, encoding="utf-8")
            else:
                file_path.write_text(
                    content_template.format_map(context), encoding="utf-8"
                )

    def post_install(self, project_path: Path) -> None:
        if not any(e in self.extras for e in ("pytest", "ruff")):
            return
        pyproject = project_path / "pyproject.toml"
        current = pyproject.read_text(encoding="utf-8")
        additions = ""

        if "pytest" in self.extras:
            additions += "\n[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n"
        if "ruff" in self.extras:
            additions += "\n[tool.ruff]\nline-length = 88\n"

        if additions:
            pyproject.write_text(current + additions, encoding="utf-8")
