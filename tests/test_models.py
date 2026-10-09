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

    c = ProjectConfig(name="x", template="cli", use_git=False, cli_type="interactive")
    assert c.cli_type == "interactive"


def test_project_config_has_use_uv_default_true():
    config = ProjectConfig(name="x", template="cli", use_git=False)
    assert config.use_uv is True


def test_project_config_use_uv_can_be_set_false():
    config = ProjectConfig(name="x", template="cli", use_git=False, use_uv=False)
    assert config.use_uv is False


def test_project_config_custom_entries_default_none():
    config = ProjectConfig(name="x", template="cli", use_git=False)
    assert config.custom_entries is None


def test_project_config_custom_entries_can_be_set():
    config = ProjectConfig(
        name="x", template="custom", use_git=False, custom_entries=[1, 2]
    )
    assert config.custom_entries == [1, 2]


# --- v1.0.9: destination + to_dict ---------------------------------------


def test_to_dict_is_json_serializable_with_custom_entries(tmp_path):
    import json

    from spawn.core.models import ProjectConfig
    from spawn.generators.custom_structure import ParsedEntry

    cfg = ProjectConfig(
        name="p",
        template="custom",
        use_git=False,
        custom_entries=[ParsedEntry("src", False), ParsedEntry("src/a.py", True)],
        destination=tmp_path / "p",
    )
    d = cfg.to_dict()
    json.dumps(d)
    assert d["custom_entries"] == [
        {"path": "src", "is_file": False},
        {"path": "src/a.py", "is_file": True},
    ]
    assert d["destination"] == str(tmp_path / "p")
    assert ProjectConfig("p", "cli", True).to_dict()["destination"] is None


def test_destination_excluded_from_equality(tmp_path):
    from spawn.core.models import ProjectConfig

    a = ProjectConfig("p", "cli", True)
    b = ProjectConfig("p", "cli", True, destination=tmp_path)
    assert a == b


def test_positional_construction_still_works():
    from spawn.core.models import ProjectConfig

    cfg = ProjectConfig("p", "cli", True, "typer", ["ruff"], "utility")
    assert cfg.framework == "typer"
    assert cfg.extras == ["ruff"]
    assert cfg.cli_type == "utility"
    assert cfg.destination is None
