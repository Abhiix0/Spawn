import json
from contextlib import contextmanager
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.data_project import DataProjectTemplate
from spawn.templates.data_project.ml import MLProjectTemplate


def _cfg(name: str = "my-ml", extras: list[str] | None = None) -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="data",
        use_git=False,
        data_type="Machine Learning",
        extras=extras or [],
    )


@contextmanager
def _mock_uv_and_install():
    with (
        patch("spawn.generators.project_generator.install_packages"),
        patch("spawn.generators.project_generator.initialize_uv"),
        patch.object(MLProjectTemplate, "post_install"),
    ):
        yield


# ─── Dispatcher ───────────────────────────────────────────────────────────


def test_dispatcher_returns_ml_template():
    t = DataProjectTemplate(data_type="Machine Learning")
    assert isinstance(t, MLProjectTemplate)


# ─── Template-level ───────────────────────────────────────────────────────


def test_ml_name():
    t = MLProjectTemplate()
    assert t.name == "Data Project"


def test_ml_folders():
    t = MLProjectTemplate()
    for required in ["data", "models", "experiments", "src", "tests"]:
        assert required in t.folders, f"Missing folder: {required}"


def test_ml_required_files():
    t = MLProjectTemplate()
    paths = [p for p, _ in t.starter_files]
    assert "data/dataset.csv" in paths
    assert "src/train.py" in paths
    assert "tests/test_ml.py" in paths


def test_ml_dataset_has_target_column():
    t = MLProjectTemplate()
    files = dict(t.starter_files)
    lines = files["data/dataset.csv"].strip().splitlines()
    assert len(lines) > 10
    header = lines[0]
    assert "target" in header
    assert "feature" in header or any(
        c.isalpha() for c in header.replace("target", "").replace(",", "")
    )


def test_ml_train_uses_random_forest():
    t = MLProjectTemplate()
    files = dict(t.starter_files)
    train = files["src/train.py"]
    assert "RandomForestClassifier" in train


def test_ml_train_saves_model():
    t = MLProjectTemplate()
    files = dict(t.starter_files)
    train = files["src/train.py"]
    assert "joblib.dump" in train
    assert "model.joblib" in train


def test_ml_train_logs_experiment():
    t = MLProjectTemplate()
    files = dict(t.starter_files)
    train = files["src/train.py"]
    assert "experiments" in train
    assert "accuracy" in train
    assert "timestamp" in train


def test_ml_train_uses_train_test_split():
    t = MLProjectTemplate()
    files = dict(t.starter_files)
    train = files["src/train.py"]
    assert "train_test_split" in train
    assert "test_size=0.2" in train


def test_ml_dependencies():
    t = MLProjectTemplate()
    deps = t.get_dependencies()
    for pkg in ["pandas", "numpy", "scikit-learn", "joblib"]:
        assert pkg in deps, f"Missing dep: {pkg}"


def test_ml_extras():
    t = MLProjectTemplate(extras=["pytest", "ruff"])
    deps = t.get_dependencies()
    assert "pytest" in deps
    assert "ruff" in deps


def test_ml_readme():
    t = MLProjectTemplate()
    readme = t.get_readme_content({"project_name": "my-ml"})
    assert readme is not None
    assert "my-ml" in readme
    assert "src/train.py" in readme
    assert "experiments" in readme


def test_ml_next_steps():
    t = MLProjectTemplate()
    combined = " ".join(t.next_steps)
    assert "train.py" in combined


# ─── Generator integration ────────────────────────────────────────────────


def test_generator_creates_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-ml").is_dir()


def test_generator_creates_src_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-ml" / "src").is_dir()


def test_generator_creates_models_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-ml" / "models").is_dir()


def test_generator_creates_experiments_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-ml" / "experiments").is_dir()


def test_generator_creates_train_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    train = tmp_path / "my-ml" / "src" / "train.py"
    assert train.exists()
    content = train.read_text(encoding="utf-8")
    assert "RandomForestClassifier" in content


def test_generator_creates_dataset_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    csv = tmp_path / "my-ml" / "data" / "dataset.csv"
    assert csv.exists()
    assert csv.stat().st_size > 0


def test_generator_creates_test_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-ml" / "tests" / "test_ml.py").exists()


def test_generator_readme(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="forest-model"))
    readme = (tmp_path / "forest-model" / "README.md").read_text(encoding="utf-8")
    assert "forest-model" in readme
    assert "train.py" in readme
    assert "experiments" in readme


def test_generator_meta_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    meta = json.loads(
        (tmp_path / "my-ml" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "data"
    assert meta["framework"] is None
    assert meta["provider"] is None
