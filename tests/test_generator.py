import pytest

from unittest.mock import patch

from spawn.core.exceptions import SpawnError
from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator


@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_project(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()
    generator.generate(config)

    assert (tmp_path / "demo").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_folders(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()
    generator.generate(config)

    assert (tmp_path / "demo" / "src").exists()
    assert (tmp_path / "demo" / "tests").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_readme(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()
    generator.generate(config)

    assert (tmp_path / "demo" / "README.md").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_gitignore(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()
    generator.generate(config)

    assert (tmp_path / "demo" / ".gitignore").exists()


def test_invalid_template_raises_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="banana",
        use_git=False,
    )

    generator = ProjectGenerator()

    with pytest.raises(SpawnError):
        generator.generate(config)


@patch("spawn.generators.project_generator.initialize_uv")
def test_existing_directory_raises_error(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "demo").mkdir()

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()

    with pytest.raises(SpawnError):
        generator.generate(config)


@patch("spawn.generators.project_generator.initialize_uv")
def test_uv_failure_cleans_up_directory(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    mock_uv.side_effect = SpawnError("uv not found")

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()

    with pytest.raises(SpawnError):
        generator.generate(config)

    assert not (tmp_path / "demo").exists()


@patch("spawn.generators.project_generator.initialize_uv")
@patch("spawn.generators.project_generator.initialize_git")
def test_git_failure_cleans_up_directory(
    mock_git,
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    mock_git.side_effect = SpawnError("Git is not installed or not available in PATH.")

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=True,
    )

    generator = ProjectGenerator()

    with pytest.raises(SpawnError):
        generator.generate(config)

    assert not (tmp_path / "demo").exists()

@patch("spawn.generators.project_generator.initialize_uv")
def test_python_template_creates_main(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=False,
    )

    ProjectGenerator().generate(config)

    assert (tmp_path / "demo" / "main.py").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_backend_api_fastapi_creates_main(
    mock_uv,
    mock_install,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="backend-api",
        use_git=False,
        framework="fastapi",
    )

    from spawn.templates.backend_api import BackendAPITemplate
    with patch.object(BackendAPITemplate, "post_install"):
        ProjectGenerator().generate(config)

    assert (tmp_path / "demo" / "app" / "main.py").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_data_science_template_creates_main(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="data-science",
        use_git=False,
    )

    ProjectGenerator().generate(config)

    assert (tmp_path / "demo" / "main.py").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_ml_template_creates_main(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="ml",
        use_git=False,
    )

    ProjectGenerator().generate(config)

    assert (tmp_path / "demo" / "main.py").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_starter_file_contains_project_name(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="my-app",
        template="python",
        use_git=False,
    )

    ProjectGenerator().generate(config)

    content = (tmp_path / "my-app" / "main.py").read_text(encoding="utf-8")
    assert "my-app" in content


# ---------------------------------------------------------------------------
# Phase 2 additions
# ---------------------------------------------------------------------------


@patch("spawn.generators.project_generator.initialize_uv")
def test_mkdir_failure_raises_spawn_error_not_raw_exception(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    """project_path.mkdir() raising PermissionError must surface as SpawnError."""
    from pathlib import Path

    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=False,
    )

    original_mkdir = Path.mkdir

    def _failing_mkdir(self, *args, **kwargs):
        # Only fail on the top-level project directory creation
        if self.name == "demo" and not kwargs.get("exist_ok", False):
            raise PermissionError("Permission denied: 'demo'")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", _failing_mkdir)

    generator = ProjectGenerator()

    with pytest.raises(SpawnError):
        generator.generate(config)

    # Partial directory must not be left behind
    assert not (tmp_path / "demo").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_write_text_failure_raises_spawn_error_and_cleans_up(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    """A write_text OSError mid-generation must wrap as SpawnError and remove the dir."""
    from pathlib import Path

    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=False,
    )

    original_write_text = Path.write_text

    call_count = 0

    def _failing_write_text(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        # Fail on the second write_text call (after README succeeds)
        if call_count == 2:
            raise OSError("No space left on device")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", _failing_write_text)

    generator = ProjectGenerator()

    with pytest.raises(SpawnError, match="No space left on device"):
        generator.generate(config)

    assert not (tmp_path / "demo").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_nested_folder_path_is_created(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    """A template that declares a nested folder like 'src/api' must create it."""
    monkeypatch.chdir(tmp_path)

    from spawn.templates.base import BaseTemplate

    nested_template = BaseTemplate(
        name="Nested Test",
        folders=["src/api"],
        starter_files=[],
    )

    with patch("spawn.generators.project_generator.instantiate_template", return_value=nested_template):
        config = ProjectConfig(
            name="demo",
            template="nested",
            use_git=False,
        )
        ProjectGenerator().generate(config)

    assert (tmp_path / "demo" / "src" / "api").is_dir()


# ---------------------------------------------------------------------------
# Phase 5D extras flow tests
# ---------------------------------------------------------------------------


def test_backend_api_extras_reach_template():
    """extras from ProjectConfig must be forwarded to BackendAPITemplate."""
    from spawn.core.registry import instantiate_template
    from spawn.templates.backend_api import BackendAPITemplate

    config = ProjectConfig(
        name="demo",
        template="backend-api",
        use_git=False,
        framework="fastapi",
        extras=["ruff", "pytest"],
    )

    template = instantiate_template(config)

    assert isinstance(template, BackendAPITemplate)
    assert template.extras == ["ruff", "pytest"]
    assert template.framework == "fastapi"


def test_backend_api_extras_in_dependencies():
    """ruff, pytest, and httpx must appear in get_dependencies() when selected."""
    from spawn.core.registry import instantiate_template

    config = ProjectConfig(
        name="demo",
        template="backend-api",
        use_git=False,
        framework="fastapi",
        extras=["ruff", "pytest"],
    )

    template = instantiate_template(config)
    deps = template.get_dependencies()

    assert "ruff" in deps
    assert "pytest" in deps
    assert "httpx" in deps


def test_backend_api_no_extras_excludes_optional_deps():
    """Without extras, ruff/pytest/httpx must NOT appear in dependencies."""
    from spawn.core.registry import instantiate_template

    config = ProjectConfig(
        name="demo",
        template="backend-api",
        use_git=False,
        framework="fastapi",
        extras=[],
    )

    template = instantiate_template(config)
    deps = template.get_dependencies()

    assert "ruff" not in deps
    assert "pytest" not in deps
    assert "httpx" not in deps
    assert "fastapi" in deps
    assert "uvicorn[standard]" in deps


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_generator_passes_extras_to_install_packages(
    mock_uv,
    mock_install,
    tmp_path,
    monkeypatch,
):
    """ProjectGenerator must call install_packages with the full dependency list."""
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="backend-api",
        use_git=False,
        framework="fastapi",
        extras=["ruff", "pytest"],
    )

    from spawn.templates.backend_api import BackendAPITemplate
    with patch.object(BackendAPITemplate, "post_install"):
        ProjectGenerator().generate(config)

    assert mock_install.called
    installed = mock_install.call_args[0][1]  # second positional arg: packages list
    assert "ruff" in installed
    assert "pytest" in installed
    assert "httpx" in installed


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_python_template_never_calls_install_packages(
    mock_uv,
    mock_install,
    tmp_path,
    monkeypatch,
):
    """Python template has no dependencies — install_packages must not be called."""
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=False,
    )

    ProjectGenerator().generate(config)

    mock_install.assert_not_called()


@patch("spawn.generators.project_generator.initialize_uv")
def test_generator_creates_spawn_meta_json(mock_uv, tmp_path, monkeypatch):
    """Every generated project must have .spawn/meta.json."""
    import json

    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(name="demo", template="python", use_git=False)
    ProjectGenerator().generate(config)

    meta_path = tmp_path / "demo" / ".spawn" / "meta.json"
    assert meta_path.exists(), ".spawn/meta.json was not created"

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert data["intent"] == "python"
    assert data["framework"] is None
    assert "spawn_version" in data


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_backend_api_meta_json_has_framework(
    mock_uv, mock_install, tmp_path, monkeypatch
):
    """Backend API meta.json must record the selected framework."""
    import json

    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="demo",
        template="backend-api",
        use_git=False,
        framework="fastapi",
        extras=[],
    )

    from spawn.templates.backend_api import BackendAPITemplate
    with patch.object(BackendAPITemplate, "post_install"):
        ProjectGenerator().generate(config)

    data = json.loads(
        (tmp_path / "demo" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert data["intent"] == "backend-api"
    assert data["framework"] == "fastapi"


@patch("spawn.generators.project_generator.initialize_uv")
def test_gitignore_contains_spawn_dir(mock_uv, tmp_path, monkeypatch):
    """.gitignore in generated projects must exclude .spawn/."""
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(name="demo", template="python", use_git=False)
    ProjectGenerator().generate(config)

    gitignore = (tmp_path / "demo" / ".gitignore").read_text(encoding="utf-8")
    assert ".spawn/" in gitignore


@patch("spawn.generators.project_generator.initialize_uv")
def test_meta_json_rollback_on_failure(mock_uv, tmp_path, monkeypatch):
    """If meta.json write fails, rollback must remove the project dir."""
    from pathlib import Path

    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(name="demo", template="python", use_git=False)

    original_mkdir = Path.mkdir
    call_count = 0

    def failing_mkdir(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if self.name == ".spawn":
            raise OSError("Simulated .spawn mkdir failure")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", failing_mkdir)

    with pytest.raises(SpawnError):
        ProjectGenerator().generate(config)

    assert not (tmp_path / "demo").exists()
