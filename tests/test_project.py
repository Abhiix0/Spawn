import pytest

from fixtures.archetypes import ARCHETYPES
from spawn.core.exceptions import ConfigError
from spawn.core.models import ProjectConfig
from spawn.core.project import load_project

from test_fixtures import STATIC, file_list


@pytest.mark.parametrize("cid", list(ARCHETYPES))
def test_load_generated_archetype(cid, spawn_project):
    template, options = ARCHETYPES[cid]
    root = spawn_project(template, **options)
    cfg = load_project(root)
    assert isinstance(cfg, ProjectConfig)
    assert cfg.template == cid
    assert cfg.name == root.name
    assert cfg.destination == root.resolve()
    assert cfg.use_git is False
    assert cfg.use_uv is False
    assert cfg.framework == options.get("framework")
    assert cfg.custom_source_format == ("tree" if cid == "custom" else None)


def test_none_for_non_spawn_repo():
    assert load_project(STATIC / "non_spawn_python_repo") is None


def test_none_for_empty_dir(tmp_path):
    assert load_project(tmp_path) is None


def test_broken_meta_raises_config_error():
    with pytest.raises(ConfigError) as exc:
        load_project(STATIC / "broken_meta")
    assert "meta.json" in str(exc.value)


def test_non_object_meta_raises(tmp_path):
    (tmp_path / ".spawn").mkdir()
    (tmp_path / ".spawn" / "meta.json").write_text("[1]", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_project(tmp_path)


def test_unknown_intent_still_loads():
    cfg = load_project(STATIC / "meta_unknown_intent")
    assert cfg.template == "nope"


def test_load_does_not_write(spawn_project):
    root = spawn_project("mcp")
    before = file_list(root)
    load_project(root)
    assert file_list(root) == before
