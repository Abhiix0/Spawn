from pathlib import Path
from unittest.mock import patch

import pytest

from spawn.core.exceptions import SpawnError, StructureParseError
from spawn.generators.custom_structure import (
    CustomStructureGenerator,
    detect_format,
    parse_structure,
)

# ─── detect_format ────────────────────────────────────────────────────────


def test_detect_format_tree():
    raw = """\
app/
├── api/
├── services/
├── models/
└── tests/
"""
    assert detect_format(raw) == "tree"


def test_detect_format_markdown():
    raw = """\
app/
- api/
- services/
- models/
- tests/
"""
    assert detect_format(raw) == "markdown"


def test_detect_format_indented():
    raw = """\
app/
    api/
    services/
    models/
    tests/
"""
    assert detect_format(raw) == "indented"


# ─── Tree format ──────────────────────────────────────────────────────────


def test_parse_tree_format():
    raw = """\
app/
├── api/
├── services/
├── models/
└── tests/
"""
    entries = parse_structure(raw)
    folders = [e.path for e in entries if not e.is_file]
    assert len(folders) == 5  # app + 4 children
    assert "app" in folders
    assert "app/api" in folders
    assert "app/services" in folders
    assert "app/models" in folders
    assert "app/tests" in folders


def test_parse_tree_format_with_files():
    raw = """\
app/
├── api/
│   └── main.py
├── README.md
└── .env.example
"""
    entries = parse_structure(raw)
    paths = {e.path: e.is_file for e in entries}
    assert paths["app"] is False
    assert paths["app/api"] is False
    assert paths["app/api/main.py"] is True
    assert paths["app/README.md"] is True
    assert paths["app/.env.example"] is True


def test_parse_tree_full_validation():
    """Parser correctly produces 5 folders (app + 4 children) and 2 top-level files."""
    raw = """\
app/
├── api/
├── services/
├── models/
└── tests/
README.md
.env.example"""
    entries = parse_structure(raw)
    folders = [e.path for e in entries if not e.is_file]
    files = [e.path for e in entries if e.is_file]
    assert len(folders) == 5, folders
    assert "app/api" in folders
    assert "README.md" in files
    assert ".env.example" in files


# ─── Markdown format ──────────────────────────────────────────────────────


def test_parse_markdown_format():
    raw = """\
app/
- api/
- services/
- models/
- tests/
"""
    entries = parse_structure(raw)
    paths = [e.path for e in entries]
    assert "app" in paths
    for child in ("api", "services", "models", "tests"):
        assert any(child in p for p in paths), f"Missing {child}"


def test_parse_markdown_nested():
    raw = """\
- src/
  - main.py
  - utils/
    - helpers.py
- tests/
"""
    entries = parse_structure(raw)
    paths = {e.path: e.is_file for e in entries}
    assert paths["src"] is False
    assert paths["src/main.py"] is True
    assert paths["src/utils"] is False
    assert paths["src/utils/helpers.py"] is True
    assert paths["tests"] is False


# ─── Indented format ──────────────────────────────────────────────────────


def test_parse_indented_format():
    raw = """\
app/
    api/
    services/
    models/
    tests/
"""
    entries = parse_structure(raw)
    paths = [e.path for e in entries]
    assert "app" in paths
    for child in ("api", "services", "models", "tests"):
        assert any(child in p for p in paths), f"Missing {child}"


def test_parse_indented_with_tabs():
    raw = "src/\n\tmain.py\n\tutils/\n\t\thelpers.py\n"
    entries = parse_structure(raw)
    paths = {e.path: e.is_file for e in entries}
    assert paths["src"] is False
    assert paths["src/main.py"] is True
    assert paths["src/utils"] is False
    assert paths["src/utils/helpers.py"] is True


# ─── File detection ───────────────────────────────────────────────────────


def test_parse_detects_files_by_extension():
    raw = """\
project/
├── README.md
├── .env.example
├── .gitignore
└── src/
"""
    entries = parse_structure(raw)
    paths = {e.path: e.is_file for e in entries}
    assert paths["project/README.md"] is True
    assert paths["project/.env.example"] is True
    assert paths["project/.gitignore"] is True
    assert paths["project/src"] is False


def test_bare_name_no_extension_is_folder():
    raw = "myproject\n    src\n    tests\n"
    entries = parse_structure(raw)
    for entry in entries:
        assert not entry.is_file, f"Expected folder, got file: {entry.path}"


def test_trailing_slash_forces_folder():
    raw = "app/\n    data/\n    logs/\n"
    entries = parse_structure(raw)
    for entry in entries:
        assert not entry.is_file, f"Expected folder: {entry.path}"


# ─── Error cases ──────────────────────────────────────────────────────────


def test_parse_empty_input_raises():
    with pytest.raises(StructureParseError):
        parse_structure("")


def test_parse_blank_lines_only_raises():
    with pytest.raises(StructureParseError):
        parse_structure("   \n\n   \n")


def test_parse_duplicate_path_raises():
    raw = """\
src/
    main.py
    main.py
"""
    with pytest.raises(StructureParseError, match="Duplicate"):
        parse_structure(raw)


def test_parse_malformed_indent_raises():
    """A line indented 4 levels with parent at level 1 (jump of 3) should raise."""
    raw = "src/\n    a/\n                deep/\n"  # unit=4: a/ depth 1, deep/ depth 4 → jump of 3
    with pytest.raises(StructureParseError):
        parse_structure(raw)


# ─── Round-trip / edge cases ──────────────────────────────────────────────


def test_inline_comments_stripped():
    raw = """\
app/
├── api/      # REST routes
└── main.py   # entry point
"""
    entries = parse_structure(raw)
    paths = [e.path for e in entries]
    assert "app/api" in paths
    assert "app/main.py" in paths
    assert not any("REST" in p or "entry" in p for p in paths)


def test_parse_returns_correct_order():
    raw = """\
src/
├── a.py
├── b.py
└── c.py
"""
    entries = parse_structure(raw)
    names = [e.path.rsplit("/", 1)[-1] for e in entries if e.is_file]
    assert names == ["a.py", "b.py", "c.py"]


def test_single_root_file():
    raw = "README.md\n"
    entries = parse_structure(raw)
    assert len(entries) == 1
    assert entries[0].path == "README.md"
    assert entries[0].is_file is True


def test_single_root_folder():
    raw = "myproject/\n"
    entries = parse_structure(raw)
    assert len(entries) == 1
    assert entries[0].path == "myproject"
    assert entries[0].is_file is False


# ─── CustomStructureGenerator ─────────────────────────────────────────────

_TREE_RAW = """\
app/
├── api/
├── services/
├── models/
└── tests/
README.md
.env.example
"""


def test_generator_creates_all_folders(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    with patch("spawn.generators.custom_structure.initialize_uv"), \
         patch("spawn.generators.custom_structure.initialize_git"):
        CustomStructureGenerator().generate("my-project", entries, use_git=False, use_uv=False)
    root = tmp_path / "my-project"
    assert (root / "app" / "api").is_dir()
    assert (root / "app" / "services").is_dir()
    assert (root / "app" / "models").is_dir()
    assert (root / "app" / "tests").is_dir()


def test_generator_creates_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    with patch("spawn.generators.custom_structure.initialize_uv"), \
         patch("spawn.generators.custom_structure.initialize_git"):
        CustomStructureGenerator().generate("my-project", entries, use_git=False, use_uv=False)
    root = tmp_path / "my-project"
    assert (root / "README.md").is_file()
    assert (root / ".env.example").is_file()


def test_generator_raises_if_dir_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "my-project").mkdir()
    entries = parse_structure(_TREE_RAW)
    with pytest.raises(SpawnError, match="already exists"):
        CustomStructureGenerator().generate("my-project", entries, use_git=False, use_uv=False)


def test_generator_skips_git_when_false(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    with patch("spawn.generators.custom_structure.initialize_git") as mock_git, \
         patch("spawn.generators.custom_structure.initialize_uv"):
        CustomStructureGenerator().generate("my-project", entries, use_git=False, use_uv=False)
    mock_git.assert_not_called()


def test_generator_calls_git_when_true(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    with patch("spawn.generators.custom_structure.initialize_git") as mock_git, \
         patch("spawn.generators.custom_structure.initialize_uv"):
        CustomStructureGenerator().generate("my-project", entries, use_git=True, use_uv=False)
    mock_git.assert_called_once()


def test_generator_rolls_back_on_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    call_count = 0
    original_mkdir = Path.mkdir

    def patched_mkdir(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise OSError("simulated disk error")
        return original_mkdir(self, *args, **kwargs)

    with patch.object(Path, "mkdir", patched_mkdir):
        with pytest.raises((SpawnError, OSError)):
            CustomStructureGenerator().generate(
                "my-project", entries, use_git=False, use_uv=False
            )

    assert not (tmp_path / "my-project").exists(), "rollback failed — directory still exists"


# ─── Dependency installation ───────────────────────────────────────────────


def test_generate_installs_dependencies_when_uv_and_deps_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    with patch("spawn.generators.custom_structure.initialize_uv"), \
         patch("spawn.generators.custom_structure.initialize_git"), \
         patch("spawn.generators.custom_structure.install_packages") as mock_install:
        CustomStructureGenerator().generate(
            "my-project",
            entries,
            use_git=False,
            use_uv=True,
            dependencies=["requests", "rich"],
        )
    mock_install.assert_called_once_with(Path("my-project"), ["requests", "rich"])


def test_generate_skips_install_when_use_uv_false(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    with patch("spawn.generators.custom_structure.initialize_uv"), \
         patch("spawn.generators.custom_structure.initialize_git"), \
         patch("spawn.generators.custom_structure.install_packages") as mock_install:
        CustomStructureGenerator().generate(
            "my-project",
            entries,
            use_git=False,
            use_uv=False,
            dependencies=["requests", "rich"],
        )
    mock_install.assert_not_called()


def test_generate_skips_install_when_no_dependencies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    with patch("spawn.generators.custom_structure.initialize_uv"), \
         patch("spawn.generators.custom_structure.initialize_git"), \
         patch("spawn.generators.custom_structure.install_packages") as mock_install:
        # empty list
        CustomStructureGenerator().generate(
            "my-project-a",
            entries,
            use_git=False,
            use_uv=True,
            dependencies=[],
        )
    mock_install.assert_not_called()


def test_generate_skips_install_when_dependencies_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    with patch("spawn.generators.custom_structure.initialize_uv"), \
         patch("spawn.generators.custom_structure.initialize_git"), \
         patch("spawn.generators.custom_structure.install_packages") as mock_install:
        # None (default)
        CustomStructureGenerator().generate(
            "my-project-b",
            entries,
            use_git=False,
            use_uv=True,
            dependencies=None,
        )
    mock_install.assert_not_called()


# ─── _apply_dev_setup / dev_setup wiring ──────────────────────────────────

_PATCH_UV   = "spawn.generators.custom_structure.initialize_uv"
_PATCH_GIT  = "spawn.generators.custom_structure.initialize_git"
_PATCH_INST = "spawn.generators.custom_structure.install_packages"


def _generate_with_dev_setup(tmp_path, dev_setup, *, use_uv=True):
    """Helper: generate project with mocked uv/git/install, return project_path."""
    entries = parse_structure(_TREE_RAW)
    with patch(_PATCH_UV), patch(_PATCH_GIT), patch(_PATCH_INST):
        return CustomStructureGenerator().generate(
            "dev-project",
            entries,
            use_git=False,
            use_uv=use_uv,
            dev_setup=dev_setup,
        )


def test_ruff_selected_creates_ruff_toml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path = _generate_with_dev_setup(tmp_path, ["ruff"])
    assert (project_path / "ruff.toml").is_file()
    content = (project_path / "ruff.toml").read_text(encoding="utf-8")
    assert "line-length" in content
    assert "py312" in content


def test_pytest_selected_creates_tests_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path = _generate_with_dev_setup(tmp_path, ["pytest"])
    assert (project_path / "tests").is_dir()
    assert (project_path / "tests" / "__init__.py").is_file()


def test_precommit_selected_creates_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path = _generate_with_dev_setup(tmp_path, ["precommit"])
    cfg = project_path / ".pre-commit-config.yaml"
    assert cfg.is_file()
    assert "ruff-pre-commit" in cfg.read_text(encoding="utf-8")


def test_dockerfile_selected_creates_dockerfile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path = _generate_with_dev_setup(tmp_path, ["dockerfile"])
    df = project_path / "Dockerfile"
    assert df.is_file()
    assert "python:3.12-slim" in df.read_text(encoding="utf-8")


def test_dev_setup_skipped_when_use_uv_false(tmp_path, monkeypatch):
    """Even with dev_setup=['ruff'], nothing is created when use_uv=False."""
    monkeypatch.chdir(tmp_path)
    project_path = _generate_with_dev_setup(tmp_path, ["ruff"], use_uv=False)
    assert not (project_path / "ruff.toml").exists()
    assert not (project_path / "tests").exists()


def test_install_packages_called_with_dev_flag(tmp_path, monkeypatch):
    """ruff + pytest + precommit selections must call install_packages with dev=True."""
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    with patch(_PATCH_UV), patch(_PATCH_GIT), \
         patch(_PATCH_INST) as mock_install:
        CustomStructureGenerator().generate(
            "dev-project",
            entries,
            use_git=False,
            use_uv=True,
            dev_setup=["ruff", "pytest", "precommit"],
        )
    mock_install.assert_called_once_with(
        Path("dev-project"),
        ["ruff", "pytest", "pre-commit"],
        dev=True,
    )


def test_dockerfile_no_dependency_install(tmp_path, monkeypatch):
    """Dockerfile-only selection must NOT trigger install_packages at all."""
    monkeypatch.chdir(tmp_path)
    entries = parse_structure(_TREE_RAW)
    with patch(_PATCH_UV), patch(_PATCH_GIT), \
         patch(_PATCH_INST) as mock_install:
        CustomStructureGenerator().generate(
            "dev-project",
            entries,
            use_git=False,
            use_uv=True,
            dev_setup=["dockerfile"],
        )
    mock_install.assert_not_called()


# ─── README generation ────────────────────────────────────────────────────

_README_RAW = """\
app/
├── api/
├── services/
└── main.py
README.md
.env.example
"""

_PATCH_UV_R   = "spawn.generators.custom_structure.initialize_uv"
_PATCH_GIT_R  = "spawn.generators.custom_structure.initialize_git"
_PATCH_INST_R = "spawn.generators.custom_structure.install_packages"


def _gen_with_readme(tmp_path, raw, project_name="my-proj", use_uv=True):
    entries = parse_structure(raw)
    with patch(_PATCH_UV_R), patch(_PATCH_GIT_R), patch(_PATCH_INST_R):
        return CustomStructureGenerator().generate(
            project_name,
            entries,
            use_git=False,
            use_uv=use_uv,
        ), entries


def test_readme_populated_when_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path, _ = _gen_with_readme(tmp_path, _README_RAW)
    readme = project_path / "README.md"
    assert readme.is_file()
    content = readme.read_text(encoding="utf-8")
    assert content.strip(), "README.md should not be empty"
    assert "my-proj" in content


def test_readme_contains_structure_tree(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path, entries = _gen_with_readme(tmp_path, _README_RAW)
    content = (project_path / "README.md").read_text(encoding="utf-8")
    # names from the parsed entries should appear in the tree section
    assert "app/" in content
    assert "api/" in content
    assert "main.py" in content


def test_readme_setup_section_reflects_use_uv_true(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path, _ = _gen_with_readme(tmp_path, _README_RAW, use_uv=True)
    content = (project_path / "README.md").read_text(encoding="utf-8")
    assert "uv sync" in content


def test_readme_setup_section_reflects_use_uv_false(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path, _ = _gen_with_readme(tmp_path, _README_RAW, use_uv=False)
    content = (project_path / "README.md").read_text(encoding="utf-8")
    assert "uv sync" not in content


def test_no_readme_in_structure_no_error(tmp_path, monkeypatch):
    """A structure without README.md must generate without errors."""
    monkeypatch.chdir(tmp_path)
    raw = "src/\n    main.py\n.env.example\n"
    entries = parse_structure(raw)
    with patch(_PATCH_UV_R), patch(_PATCH_GIT_R), patch(_PATCH_INST_R):
        project_path = CustomStructureGenerator().generate(
            "no-readme-proj", entries, use_git=False, use_uv=False
        )
    assert (project_path / "src" / "main.py").is_file()
    assert not (project_path / "README.md").exists()


def test_nested_readme_populated(tmp_path, monkeypatch):
    """docs/README.md inside the pasted structure also gets generated content."""
    monkeypatch.chdir(tmp_path)
    raw = "docs/\n    README.md\nsrc/\n    main.py\n"
    entries = parse_structure(raw)
    with patch(_PATCH_UV_R), patch(_PATCH_GIT_R), patch(_PATCH_INST_R):
        project_path = CustomStructureGenerator().generate(
            "nested-proj", entries, use_git=False, use_uv=True
        )
    nested_readme = project_path / "docs" / "README.md"
    assert nested_readme.is_file()
    content = nested_readme.read_text(encoding="utf-8")
    assert content.strip(), "nested README.md should not be empty"
    assert "nested-proj" in content


def test_other_files_remain_empty(tmp_path, monkeypatch):
    """.env.example and LICENSE entries stay zero-byte; only README.md gets content."""
    monkeypatch.chdir(tmp_path)
    raw = "README.md\n.env.example\nLICENSE\n"
    entries = parse_structure(raw)
    with patch(_PATCH_UV_R), patch(_PATCH_GIT_R), patch(_PATCH_INST_R):
        project_path = CustomStructureGenerator().generate(
            "mixed-proj", entries, use_git=False, use_uv=False
        )
    assert (project_path / "README.md").read_text(encoding="utf-8").strip()
    assert (project_path / ".env.example").stat().st_size == 0
    assert (project_path / "LICENSE").stat().st_size == 0


# ─── .gitignore generation ────────────────────────────────────────────────

_GITIGNORE_RAW = """\
src/
    main.py
.gitignore
README.md
"""

_PATCH_UV_G   = "spawn.generators.custom_structure.initialize_uv"
_PATCH_GIT_G  = "spawn.generators.custom_structure.initialize_git"
_PATCH_INST_G = "spawn.generators.custom_structure.install_packages"


def _gen_with_gitignore(tmp_path, raw, project_name="gi-proj", gitignore_extra=None):
    entries = parse_structure(raw)
    with patch(_PATCH_UV_G), patch(_PATCH_GIT_G), patch(_PATCH_INST_G):
        project_path = CustomStructureGenerator().generate(
            project_name,
            entries,
            use_git=False,
            use_uv=False,
            gitignore_extra=gitignore_extra or [],
        )
    return project_path


def test_gitignore_populated_when_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path = _gen_with_gitignore(tmp_path, _GITIGNORE_RAW)
    gi = project_path / ".gitignore"
    assert gi.is_file()
    content = gi.read_text(encoding="utf-8")
    assert content.strip(), ".gitignore should not be empty"
    assert "__pycache__/" in content


def test_gitignore_includes_python_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path = _gen_with_gitignore(tmp_path, _GITIGNORE_RAW)
    content = (project_path / ".gitignore").read_text(encoding="utf-8")
    for pattern in (".venv/", ".env", "__pycache__/", ".pytest_cache/", ".mypy_cache/", ".ruff_cache/"):
        assert pattern in content, f"Expected '{pattern}' in .gitignore"


def test_gitignore_appends_user_patterns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_path = _gen_with_gitignore(
        tmp_path, _GITIGNORE_RAW, gitignore_extra=["data/", "*.csv"]
    )
    content = (project_path / ".gitignore").read_text(encoding="utf-8")
    assert "data/" in content
    assert "*.csv" in content


def test_gitignore_deduplicates_existing_patterns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # "__pycache__/" is already in GITIGNORE_CONTENT — must not appear twice
    project_path = _gen_with_gitignore(
        tmp_path, _GITIGNORE_RAW, gitignore_extra=["__pycache__/", "data/"]
    )
    content = (project_path / ".gitignore").read_text(encoding="utf-8")
    assert content.count("__pycache__/") == 1, "__pycache__/ should appear exactly once"
    assert "data/" in content


def test_no_gitignore_in_structure_no_error(tmp_path, monkeypatch):
    """A structure without .gitignore generates normally, no crash."""
    monkeypatch.chdir(tmp_path)
    raw = "src/\n    main.py\nREADME.md\n"
    entries = parse_structure(raw)
    with patch(_PATCH_UV_G), patch(_PATCH_GIT_G), patch(_PATCH_INST_G):
        project_path = CustomStructureGenerator().generate(
            "no-gi-proj", entries, use_git=False, use_uv=False
        )
    assert (project_path / "src" / "main.py").is_file()
    assert not (project_path / ".gitignore").exists()
