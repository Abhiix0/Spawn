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


@patch("spawn.generators.project_generator.initialize_uv")
def test_fastapi_template_creates_main(
    mock_uv,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="fastapi",
        use_git=False,
    )

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
