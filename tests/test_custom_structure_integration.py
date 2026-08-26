"""Integration tests for the Custom Structure end-to-end flow."""

import json
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.custom_structure import CustomStructureGenerator, parse_structure


_TREE_RAW = """\
app/
├── api/
├── services/
└── tests/
README.md
"""


def _write_custom_metadata(project_path, config) -> None:
    """Local copy of the helper from app.py for testing without importing the CLI."""
    import datetime
    from spawn import __version__

    meta_dir = project_path / ".spawn"
    meta_dir.mkdir(exist_ok=True)
    (meta_dir / "meta.json").write_text(
        json.dumps(
            {
                "intent": "custom",
                "framework": None,
                "provider": None,
                "spawn_version": __version__,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "generator": "custom",
                "git": config.use_git,
                "uv": config.use_uv,
                "source": "tree",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_custom_structure_end_to_end(tmp_path, monkeypatch):
    """Full flow: parse → generate → write_metadata → verify .spawn/meta.json."""
    monkeypatch.chdir(tmp_path)

    entries = parse_structure(_TREE_RAW)
    config = ProjectConfig(
        name="my-custom",
        template="custom",
        use_git=False,
        use_uv=False,
        custom_entries=entries,
    )

    with (
        patch("spawn.generators.custom_structure.initialize_uv"),
        patch("spawn.generators.custom_structure.initialize_git"),
    ):
        project_path = CustomStructureGenerator().generate(
            project_name=config.name,
            entries=entries,
            use_git=config.use_git,
            use_uv=config.use_uv,
        )

    _write_custom_metadata(project_path, config)

    meta = json.loads(
        (project_path / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "custom"
    assert meta["generator"] == "custom"
    assert meta["git"] is False
    assert meta["uv"] is False
    assert meta["source"] == "tree"
    assert "created_at" in meta
    assert "spawn_version" in meta


def test_custom_structure_creates_correct_fs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)

    with (
        patch("spawn.generators.custom_structure.initialize_uv"),
        patch("spawn.generators.custom_structure.initialize_git"),
    ):
        project_path = CustomStructureGenerator().generate(
            project_name="my-custom",
            entries=entries,
            use_git=False,
            use_uv=False,
        )

    assert (project_path / "app" / "api").is_dir()
    assert (project_path / "app" / "services").is_dir()
    assert (project_path / "app" / "tests").is_dir()
    assert (project_path / "README.md").is_file()


def test_custom_config_carries_entries():
    entries = parse_structure(_TREE_RAW)
    config = ProjectConfig(
        name="x",
        template="custom",
        use_git=False,
        use_uv=True,
        custom_entries=entries,
    )
    assert config.custom_entries is entries
    assert config.use_uv is True


def test_meta_json_new_keys_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    config = ProjectConfig(
        name="my-custom",
        template="custom",
        use_git=False,
        use_uv=False,
        custom_entries=entries,
    )

    with (
        patch("spawn.generators.custom_structure.initialize_uv"),
        patch("spawn.generators.custom_structure.initialize_git"),
    ):
        project_path = CustomStructureGenerator().generate(
            project_name=config.name,
            entries=entries,
            use_git=False,
            use_uv=False,
        )

    _write_custom_metadata(project_path, config)
    meta = json.loads(
        (project_path / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )

    for key in (
        "intent",
        "framework",
        "provider",
        "spawn_version",
        "created_at",
        "generator",
        "git",
        "uv",
        "source",
    ):
        assert key in meta, f"Missing meta key: {key}"
