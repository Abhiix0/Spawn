import pytest

from unittest.mock import patch

from spawn.core.exceptions import SpawnError
from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator


@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_project(
    mock_uv,
    tmp_path,
):
    project_dir = tmp_path / "demo"

    config = ProjectConfig(
        name=str(project_dir),
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()
    generator.generate(config)

    assert project_dir.exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_folders(
    mock_uv,
    tmp_path,
):
    project_dir = tmp_path / "demo"

    config = ProjectConfig(
        name=str(project_dir),
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()
    generator.generate(config)

    assert (project_dir / "src").exists()
    assert (project_dir / "tests").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_readme(
    mock_uv,
    tmp_path,
):
    project_dir = tmp_path / "demo"

    config = ProjectConfig(
        name=str(project_dir),
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()
    generator.generate(config)

    assert (project_dir / "README.md").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_gitignore(
    mock_uv,
    tmp_path,
):
    project_dir = tmp_path / "demo"

    config = ProjectConfig(
        name=str(project_dir),
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()
    generator.generate(config)

    assert (project_dir / ".gitignore").exists()


def test_invalid_template_raises_error(tmp_path):
    project_dir = tmp_path / "demo"

    config = ProjectConfig(
        name=str(project_dir),
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
):
    project_dir = tmp_path / "demo"
    project_dir.mkdir()

    config = ProjectConfig(
        name=str(project_dir),
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()

    with pytest.raises(SpawnError):
        generator.generate(config)