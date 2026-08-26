import json
from contextlib import contextmanager
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.data_project import DataProjectTemplate
from spawn.templates.data_project.etl import ETLPipelineTemplate


def _cfg(name: str = "my-etl", extras: list[str] | None = None) -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="data",
        use_git=False,
        data_type="ETL Pipeline",
        extras=extras or [],
    )


@contextmanager
def _mock_uv_and_install():
    with (
        patch("spawn.generators.project_generator.install_packages"),
        patch("spawn.generators.project_generator.initialize_uv"),
        patch.object(ETLPipelineTemplate, "post_install"),
    ):
        yield


# ─── Dispatcher ───────────────────────────────────────────────────────────


def test_dispatcher_returns_etl_template():
    t = DataProjectTemplate(data_type="ETL Pipeline")
    assert isinstance(t, ETLPipelineTemplate)


# ─── Template-level ───────────────────────────────────────────────────────


def test_etl_name():
    t = ETLPipelineTemplate()
    assert t.name == "Data Project"


def test_etl_folders():
    t = ETLPipelineTemplate()
    for required in ["data", "pipelines", "tests"]:
        assert required in t.folders, f"Missing folder: {required}"


def test_etl_required_files():
    t = ETLPipelineTemplate()
    paths = [p for p, _ in t.starter_files]
    assert "data/raw.csv" in paths
    assert "pipelines/clean_data.py" in paths
    assert "pipelines/run.py" in paths
    assert "tests/test_etl.py" in paths
    assert ".env.example" in paths


def test_etl_env_has_input_and_output_path():
    t = ETLPipelineTemplate()
    files = dict(t.starter_files)
    env = files[".env.example"].format_map({"project_name": "test"})
    assert "INPUT_PATH" in env
    assert "OUTPUT_PATH" in env


def test_etl_raw_csv_has_messy_data():
    t = ETLPipelineTemplate()
    files = dict(t.starter_files)
    raw = files["data/raw.csv"]
    # Should have mixed casing in category column
    assert "SALES" in raw or "Sales" in raw
    assert "sales" in raw
    # Should have at least one empty field (missing value)
    lines = raw.strip().splitlines()
    assert any(ln.endswith(",") or ",," in ln for ln in lines[1:])


def test_etl_clean_data_has_safe_error_handling():
    t = ETLPipelineTemplate()
    files = dict(t.starter_files)
    clean = files["pipelines/clean_data.py"]
    assert "FileNotFoundError" in clean
    assert "sys.exit(1)" in clean


def test_etl_clean_data_normalises_category():
    t = ETLPipelineTemplate()
    files = dict(t.starter_files)
    clean = files["pipelines/clean_data.py"]
    assert "str.lower()" in clean or ".lower()" in clean
    assert "str.strip()" in clean or ".strip()" in clean


def test_etl_run_imports_clean():
    t = ETLPipelineTemplate()
    files = dict(t.starter_files)
    run = files["pipelines/run.py"]
    assert "clean_data" in run
    assert "Pipeline complete" in run


def test_etl_dependencies():
    t = ETLPipelineTemplate()
    deps = t.get_dependencies()
    assert "pandas" in deps
    assert "python-dotenv" in deps


def test_etl_extras():
    t = ETLPipelineTemplate(extras=["pytest", "ruff"])
    deps = t.get_dependencies()
    assert "pytest" in deps
    assert "ruff" in deps


def test_etl_readme():
    t = ETLPipelineTemplate()
    readme = t.get_readme_content({"project_name": "my-etl"})
    assert readme is not None
    assert "my-etl" in readme
    assert "pipelines.run" in readme
    assert "INPUT_PATH" in readme
    assert "OUTPUT_PATH" in readme


def test_etl_next_steps():
    t = ETLPipelineTemplate()
    combined = " ".join(t.next_steps)
    assert "pipelines.run" in combined
    assert "python pipelines/run.py" not in combined
    assert "python -m pipelines.run" in combined


def test_etl_readme_uses_module_invocation():
    t = ETLPipelineTemplate()
    readme = t.get_readme_content({"project_name": "my-etl"})
    assert "python -m pipelines.run" in readme
    assert "python pipelines/run.py" not in readme


# ─── Generator integration ────────────────────────────────────────────────


def test_generator_creates_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-etl").is_dir()


def test_generator_creates_pipelines_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-etl" / "pipelines").is_dir()


def test_generator_creates_clean_data_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    clean = tmp_path / "my-etl" / "pipelines" / "clean_data.py"
    assert clean.exists()
    content = clean.read_text(encoding="utf-8")
    assert "FileNotFoundError" in content
    assert "sys.exit(1)" in content


def test_generator_creates_run_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    run = tmp_path / "my-etl" / "pipelines" / "run.py"
    assert run.exists()
    assert "Pipeline complete" in run.read_text(encoding="utf-8")


def test_generator_creates_raw_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    raw = tmp_path / "my-etl" / "data" / "raw.csv"
    assert raw.exists()
    assert raw.stat().st_size > 0


def test_generator_creates_env_example(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    env = (tmp_path / "my-etl" / ".env.example").read_text(encoding="utf-8")
    assert "INPUT_PATH" in env
    assert "OUTPUT_PATH" in env


def test_generator_creates_test_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-etl" / "tests" / "test_etl.py").exists()


def test_generator_readme(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="my-pipeline"))
    readme = (tmp_path / "my-pipeline" / "README.md").read_text(encoding="utf-8")
    assert "my-pipeline" in readme
    assert "pipelines.run" in readme


def test_generator_meta_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    meta = json.loads(
        (tmp_path / "my-etl" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "data"
    assert meta["framework"] is None
    assert meta["provider"] is None
