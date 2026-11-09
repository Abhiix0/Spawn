import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from spawn.cli.app import app

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


# ── FS-01 occupied destination regressions ──
def _make_junction(target: Path, link: Path) -> None:
    if sys.platform != "win32":
        pytest.skip("Windows junctions only available on Windows")
    import _winapi

    _winapi.CreateJunction(str(target), str(link))


def test_generators_reject_existing_regular_dir_and_file(offline):
    d = offline / "existing_dir"
    d.mkdir()
    (d / "keep.txt").write_text("keep")
    f = offline / "existing_file"
    f.write_text("file")

    for name in ("existing_dir", "existing_file"):
        with pytest.raises(SpawnError, match="already exists"):
            ProjectGenerator().generate(_cfg(name=name))
        with pytest.raises(SpawnError, match="already exists"):
            CustomStructureGenerator().generate(
                name, [ParsedEntry("a.txt", True)], use_uv=False
            )
    assert (d / "keep.txt").read_text() == "keep"
    assert f.read_text() == "file"


def test_generators_reject_live_symlink_leaves_canary_untouched(offline):
    canary = offline / "canary"
    canary.mkdir()
    (canary / "keep.txt").write_text("precious")
    link = offline / "proj"
    try:
        os.symlink(canary, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")

    with pytest.raises(SpawnError, match="already exists"):
        ProjectGenerator().generate(_cfg(name="proj"))
    assert (canary / "keep.txt").read_text() == "precious"
    assert not (canary / "README.md").exists()

    with pytest.raises(SpawnError, match="already exists"):
        CustomStructureGenerator().generate(
            "proj", [ParsedEntry("a.txt", True)], use_uv=False
        )
    assert (canary / "keep.txt").read_text() == "precious"
    assert not (canary / "a.txt").exists()


def test_generators_reject_dangling_symlink(offline):
    link = offline / "proj"
    target = offline / "target_dir"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")

    with pytest.raises(SpawnError, match="already exists"):
        ProjectGenerator().generate(_cfg(name="proj"))
    assert not target.exists()

    with pytest.raises(SpawnError, match="already exists"):
        CustomStructureGenerator().generate(
            "proj", [ParsedEntry("a.txt", True)], use_uv=False
        )
    assert not target.exists()


def test_generators_reject_live_junction_leaves_canary_untouched(offline):
    canary = offline / "canary"
    canary.mkdir()
    (canary / "keep.txt").write_text("precious")
    link = offline / "proj"
    _make_junction(canary, link)

    with pytest.raises(SpawnError, match="already exists"):
        ProjectGenerator().generate(_cfg(name="proj"))
    assert (canary / "keep.txt").read_text() == "precious"
    assert not (canary / "README.md").exists()

    with pytest.raises(SpawnError, match="already exists"):
        CustomStructureGenerator().generate(
            "proj", [ParsedEntry("a.txt", True)], use_uv=False
        )
    assert (canary / "keep.txt").read_text() == "precious"
    assert not (canary / "a.txt").exists()


def test_generators_reject_dangling_junction(offline):
    temp_target = offline / "temp_target"
    temp_target.mkdir()
    link = offline / "proj"
    _make_junction(temp_target, link)
    temp_target.rmdir()
    assert not temp_target.exists()

    with pytest.raises(SpawnError, match="already exists"):
        ProjectGenerator().generate(_cfg(name="proj"))
    assert not temp_target.exists()

    with pytest.raises(SpawnError, match="already exists"):
        CustomStructureGenerator().generate(
            "proj", [ParsedEntry("a.txt", True)], use_uv=False
        )
    assert not temp_target.exists()


def test_cli_refuses_occupied_destination_interactive_and_noninteractive(offline):
    canary = offline / "canary"
    canary.mkdir()
    (canary / "keep.txt").write_text("precious")
    link = offline / "link_proj"
    if sys.platform == "win32":
        _make_junction(canary, link)
    else:
        try:
            os.symlink(canary, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable")

    runner = CliRunner()
    # Non-interactive
    r_non = runner.invoke(
        app,
        ["create", "--name", "link_proj", "--template", "cli", "--no-git", "--no-uv"],
    )
    assert r_non.exit_code == 3
    assert "already exists" in r_non.output
    assert (canary / "keep.txt").read_text() == "precious"
    assert not (canary / "README.md").exists()

    # Interactive
    cfg = ProjectConfig(name="link_proj", template="cli", use_git=False, use_uv=False)
    with patch("spawn.cli.app.get_project_config", return_value=cfg):
        r_int = runner.invoke(app, ["create"])
    assert r_int.exit_code == 3
    assert "already exists" in r_int.output
    assert (canary / "keep.txt").read_text() == "precious"
    assert not (canary / "README.md").exists()


def test_cli_refuses_dangling_link_destination_interactive_and_noninteractive(offline):
    temp_target = offline / "temp_target"
    temp_target.mkdir()
    link = offline / "dangling_proj"
    if sys.platform == "win32":
        _make_junction(temp_target, link)
    else:
        try:
            os.symlink(temp_target, link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable")
    temp_target.rmdir()
    assert not temp_target.exists()

    runner = CliRunner()
    # Non-interactive
    r_non = runner.invoke(
        app,
        [
            "create",
            "--name",
            "dangling_proj",
            "--template",
            "cli",
            "--no-git",
            "--no-uv",
        ],
    )
    assert r_non.exit_code == 3
    assert "already exists" in r_non.output
    assert not temp_target.exists()

    # Interactive
    cfg = ProjectConfig(
        name="dangling_proj", template="cli", use_git=False, use_uv=False
    )
    with patch("spawn.cli.app.get_project_config", return_value=cfg):
        r_int = runner.invoke(app, ["create"])
    assert r_int.exit_code == 3
    assert "already exists" in r_int.output
    assert not temp_target.exists()


# ── FS-03 safe rollback regressions ──
def test_cleanup_leaf_is_link_or_junction_left_untouched(offline):
    victim = offline / "victim"
    victim.mkdir()
    (victim / "c1.txt").write_text("c1")
    (victim / "c2.txt").write_text("c2")

    # Junction test on Windows
    if sys.platform == "win32":
        junc = offline / "junc"
        _make_junction(victim, junc)
        cleanup_created(junc)
        assert (victim / "c1.txt").read_text() == "c1"
        assert (victim / "c2.txt").read_text() == "c2"
        assert junc.is_junction()

    # Symlink test where supported
    sym = offline / "sym"
    try:
        os.symlink(victim, sym, target_is_directory=True)
    except (OSError, NotImplementedError):
        pass
    else:
        cleanup_created(sym)
        assert (victim / "c1.txt").read_text() == "c1"
        assert (victim / "c2.txt").read_text() == "c2"


def test_template_rollback_junction_swap_leaves_victim_untouched(offline):
    if sys.platform != "win32":
        pytest.skip("Windows junctions only available on Windows")

    victim = offline / "victim"
    victim.mkdir()
    (victim / "canary1.txt").write_text("canary1")
    (victim / "canary2.txt").write_text("canary2")

    def hook(proj_path):
        shutil.rmtree(proj_path)
        _make_junction(victim, proj_path)
        raise RuntimeError("simulated failure after junction swap")

    cfg = _cfg(name="proj")
    with patch("spawn.generators.project_generator.write_changelog", side_effect=hook):
        with pytest.raises(RuntimeError):
            ProjectGenerator().generate(cfg)

    assert (victim / "canary1.txt").read_text() == "canary1"
    assert (victim / "canary2.txt").read_text() == "canary2"
    assert victim.is_dir()


def test_custom_rollback_junction_swap_leaves_victim_untouched(offline):
    if sys.platform != "win32":
        pytest.skip("Windows junctions only available on Windows")

    victim = offline / "victim_custom"
    victim.mkdir()
    (victim / "canary1.txt").write_text("canary1")
    (victim / "canary2.txt").write_text("canary2")

    def hook(proj_path, *args, **kwargs):
        shutil.rmtree(proj_path)
        _make_junction(victim, proj_path)
        raise RuntimeError("simulated failure after custom junction swap")

    entries = [ParsedEntry("a.txt", True)]
    with patch(
        "spawn.generators.custom_structure.CustomStructureGenerator._apply_dev_setup",
        side_effect=hook,
    ):
        with pytest.raises(RuntimeError):
            CustomStructureGenerator().generate(
                "proj", entries, use_uv=True, dev_setup=["ruff"]
            )

    assert (victim / "canary1.txt").read_text() == "canary1"
    assert (victim / "canary2.txt").read_text() == "canary2"
    assert victim.is_dir()


def test_pipeline_meta_failure_junction_swap_leaves_victim_untouched(offline):
    if sys.platform != "win32":
        pytest.skip("Windows junctions only available on Windows")

    victim = offline / "victim_meta"
    victim.mkdir()
    (victim / "canary1.txt").write_text("canary1")
    (victim / "canary2.txt").write_text("canary2")

    from spawn.generators import pipeline

    def hook(proj_path, *a, **kw):
        shutil.rmtree(proj_path)
        _make_junction(victim, proj_path)
        raise OSError("simulated meta write failure")

    cfg = _cfg(
        template="custom", custom_entries=[ParsedEntry("a.txt", True)], use_uv=False
    )
    with patch.object(pipeline, "write_project_meta", side_effect=hook):
        with pytest.raises(SpawnError, match="simulated meta write failure"):
            pipeline.generate_project(cfg)

    assert (victim / "canary1.txt").read_text() == "canary1"
    assert (victim / "canary2.txt").read_text() == "canary2"
    assert victim.is_dir()


def test_template_rollback_symlink_swap_leaves_victim_untouched(offline):
    victim = offline / "victim_sym"
    victim.mkdir()
    (victim / "canary1.txt").write_text("canary1")
    (victim / "canary2.txt").write_text("canary2")

    test_link = offline / "test_link"
    try:
        os.symlink(victim, test_link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    else:
        test_link.unlink()

    def hook(proj_path):
        shutil.rmtree(proj_path)
        os.symlink(victim, proj_path, target_is_directory=True)
        raise RuntimeError("simulated failure after symlink swap")

    cfg = _cfg(name="proj")
    with patch("spawn.generators.project_generator.write_changelog", side_effect=hook):
        with pytest.raises(RuntimeError):
            ProjectGenerator().generate(cfg)

    assert (victim / "canary1.txt").read_text() == "canary1"
    assert (victim / "canary2.txt").read_text() == "canary2"
    assert victim.is_dir()


def test_rollback_different_real_dir_replacement_leaves_canary_untouched(offline):
    victim = offline / "victim_dir"
    victim.mkdir()
    (victim / "canary1.txt").write_text("canary1")
    (victim / "canary2.txt").write_text("canary2")

    def hook(proj_path):
        shutil.rmtree(proj_path)
        # Create a new directory at proj_path with different inode
        victim.rename(proj_path)
        raise RuntimeError("simulated failure after different dir swap")

    cfg = _cfg(name="proj")
    with patch("spawn.generators.project_generator.write_changelog", side_effect=hook):
        with pytest.raises(RuntimeError):
            ProjectGenerator().generate(cfg)

    # proj was swapped with a different real directory; it must NOT be deleted
    proj = offline / "proj"
    assert proj.is_dir()
    assert (proj / "canary1.txt").read_text() == "canary1"
    assert (proj / "canary2.txt").read_text() == "canary2"

