"""
Tests that each data_type appends the correct gitignore rules via post_install,
and that the negation rules (keeping the sample data file) are present.
"""
from contextlib import contextmanager
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.data_project.analysis import DataAnalysisTemplate
from spawn.templates.data_project.dashboard import DashboardTemplate
from spawn.templates.data_project.etl import ETLPipelineTemplate
from spawn.templates.data_project.ml import MLProjectTemplate


def _cfg(data_type: str, name: str = "test-proj") -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="data",
        use_git=False,
        data_type=data_type,
        extras=[],
    )


@contextmanager
def _mock_uv(template_cls):
    """Mock initialize_uv to create pyproject.toml; let post_install run real."""
    def fake_uv(p):
        (p / "pyproject.toml").write_text(
            '[project]\nname="x"\nversion="0.1.0"\n', encoding="utf-8"
        )

    with patch("spawn.generators.project_generator.install_packages"), \
         patch("spawn.generators.project_generator.initialize_uv", side_effect=fake_uv):
        yield


# ─── Data Analysis ────────────────────────────────────────────────────────


def test_data_analysis_gitignore_excludes_csvs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(DataAnalysisTemplate):
        ProjectGenerator().generate(_cfg("Data Analysis"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "data/*.csv" in gitignore


def test_data_analysis_gitignore_keeps_sample_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(DataAnalysisTemplate):
        ProjectGenerator().generate(_cfg("Data Analysis"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "!data/sample.csv" in gitignore


def test_data_analysis_gitignore_excludes_report_pngs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(DataAnalysisTemplate):
        ProjectGenerator().generate(_cfg("Data Analysis"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "reports/*.png" in gitignore


def test_data_analysis_gitignore_excludes_ipynb_checkpoints(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(DataAnalysisTemplate):
        ProjectGenerator().generate(_cfg("Data Analysis"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "notebooks/.ipynb_checkpoints/" in gitignore


# ─── Dashboard ────────────────────────────────────────────────────────────


def test_dashboard_gitignore_excludes_csvs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(DashboardTemplate):
        ProjectGenerator().generate(_cfg("Dashboard"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "data/*.csv" in gitignore


def test_dashboard_gitignore_keeps_sample_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(DashboardTemplate):
        ProjectGenerator().generate(_cfg("Dashboard"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "!data/sample.csv" in gitignore


# ─── ETL Pipeline ─────────────────────────────────────────────────────────


def test_etl_gitignore_excludes_cleaned_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(ETLPipelineTemplate):
        ProjectGenerator().generate(_cfg("ETL Pipeline"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "data/cleaned.csv" in gitignore


def test_etl_gitignore_does_not_exclude_raw_csv(tmp_path, monkeypatch):
    """Raw input data must NOT be gitignored — it's the source of truth."""
    monkeypatch.chdir(tmp_path)
    with _mock_uv(ETLPipelineTemplate):
        ProjectGenerator().generate(_cfg("ETL Pipeline"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "data/raw.csv" not in gitignore


# ─── Machine Learning ─────────────────────────────────────────────────────


def test_ml_gitignore_excludes_joblib(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(MLProjectTemplate):
        ProjectGenerator().generate(_cfg("Machine Learning"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "models/*.joblib" in gitignore


def test_ml_gitignore_excludes_experiment_jsons(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(MLProjectTemplate):
        ProjectGenerator().generate(_cfg("Machine Learning"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "experiments/*.json" in gitignore


def test_ml_gitignore_excludes_csvs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(MLProjectTemplate):
        ProjectGenerator().generate(_cfg("Machine Learning"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "data/*.csv" in gitignore


def test_ml_gitignore_keeps_dataset_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv(MLProjectTemplate):
        ProjectGenerator().generate(_cfg("Machine Learning"))
    gitignore = (tmp_path / "test-proj" / ".gitignore").read_text(encoding="utf-8")
    assert "!data/dataset.csv" in gitignore


# ─── GitHub Actions extra ─────────────────────────────────────────────────


def test_github_actions_creates_ci_yml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="test-proj",
        template="data",
        use_git=False,
        data_type="Machine Learning",
        extras=["github-actions", "pytest", "ruff"],
    )
    with patch("spawn.generators.project_generator.install_packages"), \
         patch("spawn.generators.project_generator.initialize_uv",
               side_effect=lambda p: (p / "pyproject.toml").write_text(
                   '[project]\nname="x"\nversion="0.1.0"\n', encoding="utf-8"
               )):
        ProjectGenerator().generate(config)
    ci = (tmp_path / "test-proj" / ".github" / "workflows" / "ci.yml")
    assert ci.exists()
    content = ci.read_text(encoding="utf-8")
    assert "uv sync" in content
    assert "uv run pytest" in content
    assert "uv run ruff check ." in content
