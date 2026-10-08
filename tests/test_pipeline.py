import datetime
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.core.models import ProjectConfig
from spawn.generators import project_generator
from spawn.generators.metadata import write_project_meta
from spawn.generators.pipeline import generate_project

runner = CliRunner()

META_KEYS = [
    "intent",
    "framework",
    "provider",
    "spawn_version",
    "created_at",
    "generator",
    "git",
    "uv",
    "source",
]


def _fake_uv_init(project_path):
    (Path(project_path) / "pyproject.toml").write_text("[project]\n", encoding="utf-8")


@pytest.fixture
def offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spies = {
        "initialize_uv": MagicMock(side_effect=_fake_uv_init),
        "install_packages": MagicMock(),
        "initialize_git": MagicMock(),
    }
    for name, spy in spies.items():
        monkeypatch.setattr(project_generator, name, spy)
    return spies


def _meta(path: Path) -> dict:
    return json.loads((path / ".spawn" / "meta.json").read_text(encoding="utf-8"))


def test_generate_project_dispatches_custom():
    config = ProjectConfig(name="c", template="custom", use_git=False)
    with (
        patch("spawn.generators.pipeline.CustomStructureGenerator") as custom,
        patch("spawn.generators.pipeline.ProjectGenerator") as blueprint,
        patch("spawn.generators.pipeline.write_project_meta") as meta,
    ):
        custom.return_value.generate.return_value = Path("c")
        assert generate_project(config) == Path("c")
    custom.return_value.generate.assert_called_once()
    blueprint.assert_not_called()
    meta.assert_called_once_with(Path("c"), config, generator="custom")


def test_generate_project_dispatches_template():
    config = ProjectConfig(name="t", template="mcp", use_git=False)
    with (
        patch("spawn.generators.pipeline.CustomStructureGenerator") as custom,
        patch("spawn.generators.pipeline.ProjectGenerator") as blueprint,
    ):
        blueprint.return_value.generate.return_value = Path("t")
        assert generate_project(config) == Path("t")
    blueprint.return_value.generate.assert_called_once_with(config)
    custom.assert_not_called()


def test_write_project_meta_blueprint(tmp_path):
    config = ProjectConfig(name="x", template="cli", use_git=False, use_uv=False)
    write_project_meta(tmp_path, config, generator="blueprint")
    meta = _meta(tmp_path)
    assert list(meta) == META_KEYS
    datetime.datetime.fromisoformat(meta["created_at"])
    assert meta["intent"] == "cli"
    assert meta["generator"] == "blueprint"
    assert meta["git"] is False and meta["uv"] is False
    assert meta["source"] is None


def test_write_project_meta_custom(tmp_path):
    config = ProjectConfig(name="x", template="custom", use_git=True)
    write_project_meta(tmp_path, config, generator="custom")
    meta = _meta(tmp_path)
    assert list(meta) == META_KEYS
    assert meta["intent"] == "custom"
    assert meta["framework"] is None and meta["provider"] is None
    assert meta["generator"] == "custom"
    assert meta["source"] == "tree"


def test_default_flow_runs_uv_and_meta_uv_true(offline):
    result = runner.invoke(app, ["create", "--name", "p", "--template", "cli"])
    assert result.exit_code == 0, result.output
    offline["initialize_uv"].assert_called_once()
    assert _meta(Path("p"))["uv"] is True


def test_no_uv_skips_uv_and_meta_uv_false(offline):
    result = runner.invoke(
        app, ["create", "--name", "p", "--template", "cli", "--no-uv"]
    )
    assert result.exit_code == 0, result.output
    offline["initialize_uv"].assert_not_called()
    offline["install_packages"].assert_not_called()
    assert _meta(Path("p"))["uv"] is False
    assert "Initialized" not in result.output


@pytest.mark.parametrize("extra", ["mypy", "pre-commit"])
def test_no_uv_with_extras_does_not_raise(offline, extra):
    result = runner.invoke(
        app,
        ["create", "--name", "p", "--template", "cli", "--no-uv", "--extras", extra],
    )
    assert result.exit_code == 0, result.output
    offline["install_packages"].assert_not_called()
    assert Path("p").is_dir()


def test_single_meta_writer():
    import spawn.cli.app as app_mod

    assert not hasattr(app_mod, "_write_custom_metadata")
    src = Path(project_generator.__file__).read_text(encoding="utf-8")
    assert "meta.json" not in src
    assert "meta.json" not in Path(app_mod.__file__).read_text(encoding="utf-8")
