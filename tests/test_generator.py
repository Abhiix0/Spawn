import pytest
from pathlib import Path
from spawn.core.exceptions import SpawnError
from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator

def test_project_generator_creates_project(tmp_path):
    project_dir = tmp_path / "demo"

    config = ProjectConfig(
        name=str(project_dir),
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()
    generator.generate(config)

    assert project_dir.exists()

def test_project_generator_creates_folders(tmp_path):
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

def test_project_generator_creates_readme(tmp_path):
    project_dir = tmp_path / "demo"

    config = ProjectConfig(
        name=str(project_dir),
        template="python",
        use_git=False,
    )

    generator = ProjectGenerator()
    generator.generate(config)

    assert (project_dir / "README.md").exists()

def test_project_generator_creates_gitignore(tmp_path):
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