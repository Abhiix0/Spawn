import os
from unittest.mock import patch

import pytest

from spawn.core.exceptions import SpawnError, StructureParseError
from spawn.core.models import ProjectConfig
from spawn.generators import custom_structure, destination, project_generator
from spawn.generators.custom_structure import (
    CustomStructureGenerator,
    ParsedEntry,
    parse_structure,
)
from spawn.generators.destination import (
    assert_available,
    cleanup_created,
    resolve_destination,
    safe_join,
)
from spawn.generators.pipeline import generate_project
from spawn.generators.project_generator import ProjectGenerator


@pytest.fixture
def offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for mod in (project_generator, custom_structure):
        for fn in ("initialize_uv", "initialize_git", "install_packages"):
            monkeypatch.setattr(mod, fn, lambda *a, **k: None)
    return tmp_path


def _cfg(**kw):
    base = dict(name="proj", template="cli", use_git=False, use_uv=False)
    base.update(kw)
    return ProjectConfig(**base)


# ── resolve_destination ──
def test_resolve_default_is_cwd_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert resolve_destination("x") == (tmp_path / "x").resolve()


@pytest.mark.parametrize("bad", ["", ".", "..", "a/b", "../x", "a\\b", "x\0y"])
def test_resolve_rejects_bad_names(bad):
    with pytest.raises(SpawnError):
        resolve_destination(bad)


def test_resolve_explicit_destination(tmp_path):
    assert resolve_destination("x", tmp_path / "y") == (tmp_path / "y").resolve()


# ── assert_available ──
def test_available_existing_dir_and_file(tmp_path):
    (tmp_path / "d").mkdir()
    (tmp_path / "f").write_text("x")
    for n in ("d", "f"):
        with pytest.raises(SpawnError, match="boom"):
            assert_available(tmp_path / n, "boom")
    assert_available(tmp_path / "free", "boom")


def test_available_dangling_symlink(tmp_path):
    link = tmp_path / "l"
    try:
        os.symlink(tmp_path / "nope", link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(SpawnError):
        assert_available(link, "boom")


# ── safe_join ──
@pytest.mark.parametrize(
    "bad",
    [
        "",
        "..",
        "a/../../b",
        "../x",
        "/abs",
        "C:\\x",
        "C:/x",
        "\\\\srv\\x",
        "a\\b",
        "a\0b",
    ],
)
def test_safe_join_rejects(tmp_path, bad):
    with pytest.raises(SpawnError):
        safe_join(tmp_path, bad)


def test_safe_join_valid(tmp_path):
    assert safe_join(tmp_path, "a/b/c.py") == tmp_path / "a/b/c.py"


def test_safe_join_symlink_escape(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "out"
    root.mkdir()
    outside.mkdir()
    try:
        os.symlink(outside, root / "link", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(SpawnError):
        safe_join(root, "link/file.txt")


# ── cleanup_created ──
def test_cleanup_refuses_cwd_and_ancestors(tmp_path, monkeypatch):
    child = tmp_path / "c"
    child.mkdir()
    monkeypatch.chdir(child)
    cleanup_created(child)
    cleanup_created(tmp_path)
    assert child.is_dir()


def test_cleanup_removes_real_dir(tmp_path):
    d = tmp_path / "d"
    (d / "sub").mkdir(parents=True)
    cleanup_created(d)
    assert not d.exists()


# ── custom parse / generate ──
@pytest.mark.parametrize(
    "raw",
    [
        "root/\n    ../../evil.txt\n",
        "root/../../evil.txt\n",
        "../x/\n    /abs/file.txt\n",
    ],
)
def test_parse_rejects_traversal(raw):
    with pytest.raises(StructureParseError):
        parse_structure(raw)


def test_generate_rejects_traversal_entry_and_creates_nothing(offline):
    work = offline / "work"
    work.mkdir()
    sentinel = offline / "evil.txt"
    sentinel.write_text("keep")
    entries = [ParsedEntry("a/../../evil.txt", True)]
    with pytest.raises(SpawnError):
        CustomStructureGenerator().generate(
            "p", entries, use_uv=False, destination=work / "p"
        )
    assert sentinel.read_text() == "keep"
    assert not (work / "p").exists()
    assert sorted(p.name for p in offline.iterdir()) == ["evil.txt", "work"]


# ── unsafe cleanup regressions ──
def _preexisting(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    (d / "sentinel.txt").write_text("keep")
    return d


def test_project_generator_does_not_delete_preexisting_dir(offline):
    d = _preexisting(offline)
    with patch.object(project_generator, "assert_available", lambda *a: None):
        with pytest.raises(SpawnError):
            ProjectGenerator().generate(_cfg())
    assert (d / "sentinel.txt").read_text() == "keep"


def test_custom_generator_does_not_delete_preexisting_dir(offline):
    d = _preexisting(offline)
    with patch.object(custom_structure, "assert_available", lambda *a: None):
        with pytest.raises(SpawnError):
            CustomStructureGenerator().generate("proj", [], use_uv=False)
    assert (d / "sentinel.txt").read_text() == "keep"


def test_existing_message_wording_preserved(offline):
    _preexisting(offline)
    with pytest.raises(SpawnError, match="Directory 'proj' already exists."):
        ProjectGenerator().generate(_cfg())
    with pytest.raises(SpawnError, match="Directory 'proj' already exists."):
        CustomStructureGenerator().generate("proj", [], use_uv=False)


# ── mid-generation failure cleanup ──
def test_failure_removes_only_created_dir(offline):
    other = offline / "other"
    other.mkdir()
    with patch.object(project_generator, "write_changelog", side_effect=RuntimeError):
        with pytest.raises(RuntimeError):
            ProjectGenerator().generate(_cfg())
    assert not (offline / "proj").exists()
    assert other.is_dir()


def test_custom_failure_removes_only_created_dir(offline):
    other = offline / "other"
    other.mkdir()
    with patch.object(custom_structure, "initialize_git", side_effect=RuntimeError):
        with pytest.raises(RuntimeError):
            CustomStructureGenerator().generate(
                "proj", [ParsedEntry("a.txt", True)], use_git=True, use_uv=False
            )
    assert not (offline / "proj").exists()
    assert other.is_dir()


def test_pipeline_meta_failure_removes_custom_dir(offline):
    cfg = _cfg(
        template="custom", custom_entries=[ParsedEntry("a.txt", True)], use_uv=False
    )
    from spawn.generators import pipeline

    with patch.object(pipeline, "write_project_meta", side_effect=OSError("disk")):
        with pytest.raises(SpawnError, match="disk"):
            generate_project(cfg)
    assert not (offline / "proj").exists()


# ── explicit destination ──
def test_destination_honored_by_both_generators(offline, tmp_path_factory):
    base = tmp_path_factory.mktemp("elsewhere")
    p1 = ProjectGenerator().generate(_cfg(destination=base / "one"))
    assert p1 == (base / "one").resolve() and (p1 / "README.md").is_file()
    p2 = CustomStructureGenerator().generate(
        "two", [ParsedEntry("a.txt", True)], use_uv=False, destination=base / "two"
    )
    assert p2 == (base / "two").resolve() and (p2 / "a.txt").is_file()
    assert not (offline / "one").exists() and not (offline / "two").exists()


def test_module_exports():
    assert destination.safe_join is safe_join
