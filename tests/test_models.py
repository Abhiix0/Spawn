from spawn.core.models import ProjectConfig


def test_project_config_values():
    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=True,
    )

    assert config.name == "demo"
    assert config.template == "python"
    assert config.use_git is True