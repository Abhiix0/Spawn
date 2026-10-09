import compileall
import difflib
import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fixtures.archetypes import ARCHETYPES
from spawn.cli.app import app
from spawn.core.exceptions import (
    FilesystemError,
    InvalidInputError,
    StructureParseError,
)
from spawn.core.models import ProjectConfig
from spawn.core.planning import plan_project
from spawn.generators.custom_structure import parse_structure
from spawn.generators.pipeline import generate_project

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures"
STATIC = FIXTURES / "static"
TREES = FIXTURES / "trees"

IDS = list(ARCHETYPES)


def file_list(root: Path) -> list[str]:
    return sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    )


def snapshot(root: Path) -> dict[str, bytes]:
    snap = {}
    for rel in file_list(root):
        data = (root / rel).read_bytes()
        if rel == ".spawn/meta.json":
            meta = json.loads(data)
            meta.pop("created_at")
            data = json.dumps(meta, sort_keys=True).encode()
        snap[rel] = data
    return snap


@pytest.fixture(params=IDS)
def archetype(request, spawn_project):
    template, options = ARCHETYPES[request.param]
    return request.param, spawn_project(template, **options)


def test_archetype_ids_are_the_nine_expected():
    assert len(ARCHETYPES) == 9


def test_golden_tree(archetype):
    cid, root = archetype
    actual = "\n".join(file_list(root)) + "\n"
    golden = TREES / f"{cid}.txt"
    if os.environ.get("SPAWN_UPDATE_TREES") == "1":
        golden.write_text(actual, encoding="utf-8", newline="\n")
    expected = golden.read_text(encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(True), actual.splitlines(True), "golden", "actual"
        )
    )
    assert actual == expected, f"tree for {cid} differs:\n{diff}"


def test_meta_json(archetype):
    cid, root = archetype
    meta = json.loads((root / ".spawn" / "meta.json").read_text(encoding="utf-8"))
    assert meta["intent"] == ARCHETYPES[cid][0]
    assert meta["generator"] == ("custom" if cid == "custom" else "blueprint")
    assert meta["uv"] is False
    assert meta["git"] is False


def test_generated_python_compiles(archetype):
    _, root = archetype
    assert compileall.compile_dir(str(root), quiet=1, force=True)


@pytest.mark.parametrize("cid", IDS)
def test_generation_is_deterministic(cid, tmp_path_factory, no_toolchain):
    template, options = ARCHETYPES[cid]
    snaps = []
    for i in range(2):
        base = tmp_path_factory.mktemp(f"det{i}")
        config = _config(template, options)
        config.destination = base / "fx"
        snaps.append(snapshot(generate_project(config)))
    assert snaps[0] == snaps[1]


def _config(template, options):
    if template == "custom":
        return ProjectConfig(
            name="fx",
            template="custom",
            use_git=False,
            use_uv=False,
            custom_entries=parse_structure(
                "src/\n  app.py\ntests/\n  test_a.py\nREADME.md\n"
            ),
            custom_source_format="tree",
        )
    return plan_project("fx", template, use_git=False, use_uv=False, **options)


def _doctor(path):
    result = runner.invoke(app, ["doctor", str(path)])
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "Traceback" not in result.output
    return result.exit_code


def test_doctor_on_generated_project(archetype):
    _, root = archetype
    assert _doctor(root) == 0


def test_doctor_on_static_fixtures():
    for name in ("non_spawn_python_repo", "broken_meta", "meta_unknown_intent"):
        assert _doctor(STATIC / name) == 0


def test_doctor_on_empty_dir(tmp_path):
    assert _doctor(tmp_path) == 0


def test_doctor_on_nonexistent_path(tmp_path):
    assert _doctor(tmp_path / "missing") == 1


def test_doctor_on_file_path(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    assert _doctor(f) == 1


def test_pipeline_rejects_existing_destination(spawn_project, tmp_path):
    (tmp_path / "fx").mkdir()
    with pytest.raises(FilesystemError):
        spawn_project("mcp")


def test_pipeline_rejects_unsafe_custom_entry():
    with pytest.raises(StructureParseError):
        parse_structure("src/\n  ../evil.py\n")


def test_planning_rejects_invalid_option():
    with pytest.raises(InvalidInputError):
        plan_project("fx", "backend-api", framework="nope")
