import json
from contextlib import contextmanager
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.data_project import DataProjectTemplate
from spawn.templates.data_project.dashboard import DashboardTemplate


def _cfg(name: str = "my-dashboard", extras: list[str] | None = None) -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="data",
        use_git=False,
        data_type="Dashboard",
        extras=extras or [],
    )


@contextmanager
def _mock_uv_and_install():
    with patch("spawn.generators.project_generator.install_packages"), \
         patch("spawn.generators.project_generator.initialize_uv"), \
         patch.object(DashboardTemplate, "post_install"):
        yield


# ─── Dispatcher ───────────────────────────────────────────────────────────


def test_dispatcher_returns_dashboard_template():
    t = DataProjectTemplate(data_type="Dashboard")
    assert isinstance(t, DashboardTemplate)


# ─── Template-level ───────────────────────────────────────────────────────


def test_dashboard_name():
    t = DashboardTemplate()
    assert t.name == "Data Project"


def test_dashboard_folders():
    t = DashboardTemplate()
    for required in ["data", "dashboard", "tests"]:
        assert required in t.folders, f"Missing folder: {required}"


def test_dashboard_required_files():
    t = DashboardTemplate()
    paths = [p for p, _ in t.starter_files]
    assert "data/sample.csv" in paths
    assert "dashboard/app.py" in paths
    assert "tests/test_dashboard.py" in paths


def test_dashboard_app_contains_streamlit():
    t = DashboardTemplate()
    files = dict(t.starter_files)
    app = files["dashboard/app.py"]
    assert "import streamlit as st" in app
    assert "st.title" in app
    assert "st.sidebar" in app
    assert "plotly" in app


def test_dashboard_app_has_project_name_placeholder():
    t = DashboardTemplate()
    files = dict(t.starter_files)
    app = files["dashboard/app.py"]
    assert "{project_name}" in app


def test_dashboard_sample_csv_has_correct_columns():
    t = DashboardTemplate()
    files = dict(t.starter_files)
    lines = [ln for ln in files["data/sample.csv"].strip().splitlines() if ln]
    assert len(lines) > 1
    assert "date" in lines[0]
    assert "category" in lines[0]
    assert "value" in lines[0]


def test_dashboard_dependencies():
    t = DashboardTemplate()
    deps = t.get_dependencies()
    assert "streamlit" in deps
    assert "pandas" in deps
    assert "plotly" in deps


def test_dashboard_extras():
    t = DashboardTemplate(extras=["pytest", "ruff"])
    deps = t.get_dependencies()
    assert "pytest" in deps
    assert "ruff" in deps


def test_dashboard_readme():
    t = DashboardTemplate()
    readme = t.get_readme_content({"project_name": "my-dashboard"})
    assert readme is not None
    assert "my-dashboard" in readme
    assert "streamlit run" in readme


def test_dashboard_next_steps():
    t = DashboardTemplate()
    assert any("streamlit" in s for s in t.next_steps)


# ─── Generator integration ────────────────────────────────────────────────


def test_generator_creates_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-dashboard").is_dir()


def test_generator_creates_dashboard_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-dashboard" / "dashboard").is_dir()


def test_generator_creates_app_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    app = tmp_path / "my-dashboard" / "dashboard" / "app.py"
    assert app.exists()
    content = app.read_text(encoding="utf-8")
    assert "streamlit" in content
    assert "my-dashboard" in content


def test_generator_creates_data_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    csv = tmp_path / "my-dashboard" / "data" / "sample.csv"
    assert csv.exists()
    assert csv.stat().st_size > 0


def test_generator_creates_test_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-dashboard" / "tests" / "test_dashboard.py").exists()


def test_generator_readme(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="sales-dash"))
    readme = (tmp_path / "sales-dash" / "README.md").read_text(encoding="utf-8")
    assert "sales-dash" in readme
    assert "streamlit run" in readme


def test_generator_meta_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    meta = json.loads(
        (tmp_path / "my-dashboard" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "data"
    assert meta["framework"] is None
    assert meta["provider"] is None
