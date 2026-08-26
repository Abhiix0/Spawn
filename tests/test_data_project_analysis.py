import json
from contextlib import contextmanager
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.data_project import DataProjectTemplate
from spawn.templates.data_project.analysis import DataAnalysisTemplate


def _cfg(name: str = "my-analysis", extras: list[str] | None = None) -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="data",
        use_git=False,
        data_type="Data Analysis",
        extras=extras or [],
    )


@contextmanager
def _mock_uv_and_install():
    with (
        patch("spawn.generators.project_generator.install_packages"),
        patch("spawn.generators.project_generator.initialize_uv"),
        patch.object(DataAnalysisTemplate, "post_install"),
    ):
        yield


# ─── Dispatcher ───────────────────────────────────────────────────────────


def test_dispatcher_returns_analysis_template():
    t = DataProjectTemplate(data_type="Data Analysis")
    assert isinstance(t, DataAnalysisTemplate)


def test_dispatcher_default_is_analysis():
    t = DataProjectTemplate()
    assert isinstance(t, DataAnalysisTemplate)


# ─── Template-level ───────────────────────────────────────────────────────


def test_data_analysis_name():
    t = DataAnalysisTemplate()
    assert t.name == "Data Project"


def test_data_analysis_folders():
    t = DataAnalysisTemplate()
    for required in ["data", "notebooks", "reports", "tests"]:
        assert required in t.folders, f"Missing folder: {required}"


def test_data_analysis_required_files():
    t = DataAnalysisTemplate()
    paths = [p for p, _ in t.starter_files]
    assert "data/sample.csv" in paths
    assert "notebooks/analysis.ipynb" in paths
    assert "tests/test_analysis.py" in paths


def test_data_analysis_sample_csv_nonempty():
    t = DataAnalysisTemplate()
    files = dict(t.starter_files)
    csv = files["data/sample.csv"]
    lines = [ln for ln in csv.strip().splitlines() if ln]
    assert len(lines) > 1
    assert "category" in lines[0]
    assert "value" in lines[0]


def test_data_analysis_notebook_is_valid_json():
    t = DataAnalysisTemplate()
    files = dict(t.starter_files)
    nb = json.loads(files["notebooks/analysis.ipynb"])
    assert nb["nbformat"] == 4
    assert len(nb["cells"]) == 4


def test_data_analysis_notebook_cells():
    t = DataAnalysisTemplate()
    files = dict(t.starter_files)
    nb = json.loads(files["notebooks/analysis.ipynb"])
    cells = nb["cells"]
    assert "import pandas" in "".join(cells[0]["source"])
    assert "sample.csv" in "".join(cells[0]["source"])
    assert "describe" in "".join(cells[1]["source"])
    assert "groupby" in "".join(cells[1]["source"])
    assert "savefig" in "".join(cells[2]["source"])
    assert "reports/summary.png" in "".join(cells[2]["source"])
    assert cells[3]["cell_type"] == "markdown"
    assert "Insights" in "".join(cells[3]["source"])


def test_data_analysis_dependencies():
    t = DataAnalysisTemplate()
    deps = t.get_dependencies()
    for pkg in ["pandas", "numpy", "jupyter", "matplotlib"]:
        assert pkg in deps


def test_data_analysis_extras():
    t = DataAnalysisTemplate(extras=["pytest", "ruff"])
    deps = t.get_dependencies()
    assert "pytest" in deps
    assert "ruff" in deps


def test_data_analysis_readme():
    t = DataAnalysisTemplate()
    readme = t.get_readme_content({"project_name": "my-analysis"})
    assert readme is not None
    assert "my-analysis" in readme
    assert "jupyter notebook" in readme
    assert "Data Analysis" in readme


def test_data_analysis_next_steps():
    t = DataAnalysisTemplate()
    assert any("jupyter" in s for s in t.next_steps)


# ─── Generator integration ────────────────────────────────────────────────


def test_generator_creates_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-analysis").is_dir()


def test_generator_creates_data_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    csv = tmp_path / "my-analysis" / "data" / "sample.csv"
    assert csv.exists()
    assert csv.stat().st_size > 0


def test_generator_creates_notebook(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    nb_path = tmp_path / "my-analysis" / "notebooks" / "analysis.ipynb"
    assert nb_path.exists()
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4
    assert len(nb["cells"]) == 4


def test_generator_creates_reports_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-analysis" / "reports").is_dir()


def test_generator_creates_test_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-analysis" / "tests" / "test_analysis.py").exists()


def test_generator_readme(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="sales-analysis"))
    readme = (tmp_path / "sales-analysis" / "README.md").read_text(encoding="utf-8")
    assert "sales-analysis" in readme
    assert "jupyter notebook" in readme


def test_generator_meta_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    meta = json.loads(
        (tmp_path / "my-analysis" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "data"
    assert meta["framework"] is None
    assert meta["provider"] is None
