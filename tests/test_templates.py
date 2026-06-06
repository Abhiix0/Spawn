import pytest

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.core.exceptions import SpawnError

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