"""Regression tests for Issue 7: Default CLI testing setup.

Verifies that:
- pytest is installed as a dev dep via post_install (not in get_dependencies)
- [tool.pytest.ini_options] with testpaths is written by post_install
  whenever a pyproject.toml exists
- Existing extras (ruff, github-actions) are unaffected
- argparse runtime deps remain empty
- The pytest extra in get_dependencies still works when explicitly selected
"""

from unittest.mock import patch

from spawn.templates.cli_application import CLITemplate

# Correct patch target: install_packages is imported at module level in
# spawn.templates.cli_application, so that name must be patched there.
_PATCH = "spawn.templates.cli_application.install_packages"


# ---------------------------------------------------------------------------
# get_dependencies: pytest NOT in runtime deps (stays in dev group)
# ---------------------------------------------------------------------------


def test_typer_default_deps_do_not_include_pytest():
    """pytest must NOT be in get_dependencies — it goes via post_install dev."""
    t = CLITemplate(framework="typer")
    assert "pytest" not in t.get_dependencies()


def test_argparse_default_deps_remain_empty():
    """argparse has no runtime deps and pytest must not inflate them."""
    t = CLITemplate(framework="argparse")
    assert t.get_dependencies() == []


def test_pytest_extra_still_adds_pytest_to_runtime_deps():
    """Explicitly selecting the pytest extra still adds it to get_dependencies."""
    t = CLITemplate(framework="typer", extras=["pytest"])
    assert "pytest" in t.get_dependencies()


def test_ruff_extra_still_adds_ruff_dep():
    t = CLITemplate(framework="typer", extras=["ruff"])
    assert "ruff" in t.get_dependencies()


# ---------------------------------------------------------------------------
# post_install: pytest installed as dev dep + testpaths written
# ---------------------------------------------------------------------------


def test_post_install_writes_pytest_section_when_pyproject_exists(tmp_path):
    """When pyproject.toml exists, post_install must write [tool.pytest.ini_options]."""
    t = CLITemplate(framework="typer", extras=[])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")

    with patch(_PATCH):
        t.post_install(tmp_path)

    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in content
    assert 'testpaths = ["tests"]' in content


def test_post_install_installs_pytest_as_dev_dep(tmp_path):
    """post_install must call install_packages(['pytest'], dev=True)."""
    t = CLITemplate(framework="typer", extras=[])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")

    with patch(_PATCH) as mock_install:
        t.post_install(tmp_path)

    mock_install.assert_called_once_with(tmp_path, ["pytest"], dev=True)


def test_post_install_with_pytest_extra_skips_dev_install(tmp_path):
    """When pytest extra is selected it's already in get_dependencies;
    post_install must NOT call install_packages a second time for pytest."""
    t = CLITemplate(framework="typer", extras=["pytest"])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")

    with patch(_PATCH) as mock_install:
        t.post_install(tmp_path)

    mock_install.assert_not_called()


# ---------------------------------------------------------------------------
# ruff and github-actions extras unaffected
# ---------------------------------------------------------------------------


def test_ruff_extra_still_writes_ruff_section(tmp_path):
    t = CLITemplate(framework="typer", extras=["ruff"])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")
    with patch(_PATCH):
        t.post_install(tmp_path)
    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.ruff]" in content


def test_github_actions_extra_creates_ci_yml(tmp_path):
    t = CLITemplate(framework="typer", extras=["github-actions"])
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")
    with patch(_PATCH):
        t.post_install(tmp_path)
    ci = tmp_path / ".github" / "workflows" / "ci.yml"
    assert ci.exists()
    assert "uv sync" in ci.read_text(encoding="utf-8")


def test_argparse_post_install_writes_pytest_section(tmp_path):
    """argparse has no runtime deps but should still get pytest dev install."""
    t = CLITemplate(framework="argparse", extras=[])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")
    with patch(_PATCH) as mock_install:
        t.post_install(tmp_path)
    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in content
    mock_install.assert_called_once_with(tmp_path, ["pytest"], dev=True)
