import sys
from pathlib import Path

import pytest

import spawn.cli.app  # noqa: F401  (load every module that holds toolchain hooks)
from spawn.core.models import ProjectConfig
from spawn.core.planning import plan_project
from spawn.generators.custom_structure import parse_structure
from spawn.generators.pipeline import generate_project

CUSTOM_TREE = "src/\n  app.py\ntests/\n  test_a.py\nREADME.md\n"


@pytest.fixture
def no_toolchain(monkeypatch):
    """Make generation offline: no git, no uv, no package installs."""
    for mod in list(sys.modules.values()):
        if mod and getattr(mod, "__name__", "").startswith("spawn"):
            for attr in ("initialize_uv", "install_packages", "initialize_git"):
                if hasattr(mod, attr):
                    monkeypatch.setattr(mod, attr, lambda *a, **k: None)


@pytest.fixture
def spawn_project(tmp_path, no_toolchain):
    """Factory: make(template, name="fx", **options) -> generated project Path."""

    def make(template: str, name: str = "fx", **options) -> Path:
        if template == "custom":
            config = ProjectConfig(
                name=name,
                template="custom",
                use_git=False,
                use_uv=False,
                custom_entries=parse_structure(CUSTOM_TREE),
                custom_source_format="tree",
            )
        else:
            config = plan_project(
                name, template, use_git=False, use_uv=False, **options
            )
        config.destination = tmp_path / name
        return generate_project(config)

    return make
