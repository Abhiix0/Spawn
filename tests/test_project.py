import json

import pytest

from fixtures.archetypes import ARCHETYPES
from spawn.core.exceptions import ConfigError
from spawn.core.models import ProjectConfig
from spawn.core.project import ProjectMetadata, read_project_metadata

from test_fixtures import STATIC, file_list


def _write_meta(root, data):
    (root / ".spawn").mkdir(exist_ok=True)
    (root / ".spawn" / "meta.json").write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize("cid", list(ARCHETYPES))
def test_read_generated_archetype(cid, spawn_project):
    template, options = ARCHETYPES[cid]
    root = spawn_project(template, **options)
    meta = read_project_metadata(root)
    assert isinstance(meta, ProjectMetadata)
    assert meta.intent == cid
    assert meta.generator == ("custom" if cid == "custom" else "blueprint")
    assert meta.uv is False
    assert meta.git is False
    assert meta.framework == options.get("framework")
    assert meta.source == ("tree" if cid == "custom" else None)


def test_none_for_non_spawn_repo():
    assert read_project_metadata(STATIC / "non_spawn_python_repo") is None


def test_none_for_empty_dir(tmp_path):
    assert read_project_metadata(tmp_path) is None


def test_broken_meta_raises_config_error():
    with pytest.raises(ConfigError) as exc:
        read_project_metadata(STATIC / "broken_meta")
    assert "meta.json" in str(exc.value)


def test_non_object_meta_raises(tmp_path):
    (tmp_path / ".spawn").mkdir()
    (tmp_path / ".spawn" / "meta.json").write_text("[1]", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        read_project_metadata(tmp_path)
    assert "meta.json" in str(exc.value)


def test_unknown_intent_still_loads():
    assert read_project_metadata(STATIC / "meta_unknown_intent").intent == "nope"


def test_missing_optional_keys_are_none(tmp_path):
    _write_meta(tmp_path, {"intent": "mcp"})
    meta = read_project_metadata(tmp_path)
    assert meta == ProjectMetadata(intent="mcp")
    assert meta.framework is None and meta.uv is None and meta.created_at is None


def test_unknown_keys_ignored(tmp_path):
    _write_meta(tmp_path, {"intent": "mcp", "future_key": 1})
    meta = read_project_metadata(tmp_path)
    assert meta.intent == "mcp"
    assert not hasattr(meta, "future_key")


def test_read_does_not_write(spawn_project):
    root = spawn_project("mcp")
    before = file_list(root)
    read_project_metadata(root)
    assert file_list(root) == before


def test_result_is_not_project_config(spawn_project):
    meta = read_project_metadata(spawn_project("mcp"))
    assert type(meta) is ProjectMetadata
    assert not isinstance(meta, ProjectConfig)


def test_license_none_is_not_exposed(spawn_project):
    meta = read_project_metadata(spawn_project("mcp", license="none"))
    for attr in ("license", "name", "extras", "cli_type", "data_type", "claude_md"):
        assert not hasattr(meta, attr)
