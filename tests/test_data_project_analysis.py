import json
from contextlib import contextmanager
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.data_project import DataProjectTemplate


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
    with patch("spawn.generators.project_generator.install_packages"), \
         patch("spawn.generators.project_generator.initialize_uv"), \
         patch.object(DataProjectTemplate, "post_install"):
        yield


# ─── Template-level ───────────────────────────────────────────────────────


def test_data_analysis_name():
    t = DataProjectTemplate(data_type="Data Analysis")
    assert t.name == "Data Project"
    assert t.data_type == "Data Analysis"


def test_data_analysis_folders():
    t = DataProjectTemplate(data_type="Data Analysis")
    for required in ["data", "notebooks", "reports", "tests"]:
        assert required in t.folders, f"Missing folder: {required}"


def test_data_analysis_required_files():
    t = DataProjectTemplate(data_type="Data Analysis")
    paths = [p for p, _ in t.starter_files]
    assert "data/sample.csv" in paths
    assert "notebooks/analysis.ipynb" in paths
    assert "tests/test_analysis.py" in paths


def test_data_analysis_sample_csv_nonempty():
    t = DataProjectTemplate(data_type="Data Analysis")
    files = dict(t.starter_files)
    csv = files["data/sample.csv"]
    lines = [ln for ln in csv.strip().splitlines() if ln]
    assert len(lines) > 1, "sample.csv has no data rows"
    assert "category" in lines[0]
    assert "value" in lines[0]


def test_data_analysis_notebook_is_valid_json():
    t = DataProjectTemplate(data_type="Data Analysis")
    files = dict(t.starter_files)
    nb = json.loads(files["notebooks/analysis.ipynb"])
    assert nb["nbformat"] == 4
    assert len(nb["cells"]) == 4


def test_data_analysis_notebook_cells():
    t = DataProjectTemplate(data_type="Data Analysis")
    files = dict(t.starter_files)
    nb = json.loads(files["notebooks/analysis.ipynb"])
    cells = nb["cells"]
    # Cell 1: imports + load CSV
    src1 = "".join(cells[0]["source"])
    assert "import pandas" in src1
    assert "sample.csv" in src1
    # Cell 2: describe + groupby
    src2 = "".join(cells[1]["source"])
    assert "describe" in src2
    assert "groupby" in src2
    # Cell 3: bar chart + savefig
    src3 = "".join(cells[2]["source"])
    assert "savefig" in src3
    assert "reports/summary.png" in src3
    # Cell 4: markdown Insights
    assert cells[3]["cell_type"] == "markdown"
    assert "Insights" in "".join(cells[3]["source"])


def test_data_analysis_dependencies():
    t = DataProjectTemplate(data_type="Data Analysis")
    deps = t.get_dependencies()
    for pkg in ["pandas", "numpy", "jupyter", "matplotlib"]:
        assert pkg in deps, f"Missing dep: {pkg}"


def test_data_analysis_extras_add_pytest_and_ruff():
    t = DataProjectTemplate(data_type="Data Analysis", extras=["pytest", "ruff"])
    deps = t.get_dependencies()
    assert "pytest" in deps
    assert "ruff" in deps


def test_data_analysis_readme_contains_project_name():
    t = DataProjectTemplate(data_type="Data Analysis")
    readme = t.get_readme_content({"project_name": "my-analysis"})
    assert readme is not None
    assert "my-analysis" in readme


def test_data_analysis_readme_has_jupyter_instruction():
    t = DataProjectTemplate(data_type="Data Analysis")
    readme = t.get_readme_content({"project_name": "x"})
    assert "jupyter notebook" in readme
    assert "Data Analysis" in readme


def test_data_analysis_next_steps_has_jupyter():
    t = DataProjectTemplate(data_type="Data Analysis")
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
    csv_path = tmp_path / "my-analysis" / "data" / "sample.csv"
    assert csv_path.exists()
    assert csv_path.stat().st_size > 0


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


def test_generator_readme_has_project_name(tmp_path, monkeypatch):
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
