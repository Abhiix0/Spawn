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


def test_project_config_defaults():
    config = ProjectConfig(
        name="demo",
        template="python",
        use_git=True,
    )

    assert config.framework is None


def test_project_config_with_framework():
    config = ProjectConfig(
        name="demo",
        template="backend-api",
        use_git=True,
        framework="fastapi",
    )

    assert config.framework == "fastapi"


def test_project_config_cli_type_defaults_none():
    from spawn.core.models import ProjectConfig

    c = ProjectConfig(name="x", template="cli", use_git=False)
    assert c.cli_type is None


def test_project_config_cli_type_set():
    from spawn.core.models import ProjectConfig

    c = ProjectConfig(
        name="x", template="cli", use_git=False, cli_type="interactive"
    )
    assert c.cli_type == "interactive"
