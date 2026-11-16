"""Regression tests for Issue 7: Default CLI testing setup.

Verifies that:
- pytest is a *dev* dependency (via get_dev_dependencies), never a runtime one
- [tool.pytest.ini_options] with testpaths is written by post_install
  whenever a pyproject.toml exists, so `uv run pytest` works out of the box
- Existing extras (ruff, github-actions) are unaffected
- argparse runtime deps remain empty

Dev tools (pytest, ruff, mypy, pre-commit) are installed by the generator from
get_dev_dependencies() with dev=True, so post_install only writes config files.
"""

from spawn.templates.cli_application import CLITemplate


# ---------------------------------------------------------------------------
# get_dependencies: pytest/ruff never appear as runtime deps
# ---------------------------------------------------------------------------


def test_typer_default_deps_do_not_include_pytest():
    """pytest must NOT be in get_dependencies — it is always a dev dep."""
    t = CLITemplate(framework="typer")
    assert "pytest" not in t.get_dependencies()


def test_argparse_default_deps_remain_empty():
    """argparse has no runtime deps and pytest must not inflate them."""
    t = CLITemplate(framework="argparse")
    assert t.get_dependencies() == []


def test_pytest_extra_adds_pytest_to_dev_deps():
    """The pytest extra keeps pytest in the dev group, not runtime deps."""
    t = CLITemplate(framework="typer", extras=["pytest"])
    assert "pytest" in t.get_dev_dependencies()
    assert "pytest" not in t.get_dependencies()


def test_ruff_extra_adds_ruff_to_dev_deps():
    t = CLITemplate(framework="typer", extras=["ruff"])
    assert any(d.startswith("ruff") for d in t.get_dev_dependencies())
    assert not any(d.startswith("ruff") for d in t.get_dependencies())


def test_cli_always_has_pytest_as_dev_dep():
    """CLI projects always ship a working test setup, even with no extras."""
    for framework in ("typer", "click", "argparse"):
        t = CLITemplate(framework=framework, extras=[])
        assert "pytest" in t.get_dev_dependencies()


# ---------------------------------------------------------------------------
# post_install: writes [tool.pytest] / [tool.ruff] config sections only
# ---------------------------------------------------------------------------


def test_post_install_writes_pytest_section_when_pyproject_exists(tmp_path):
    """When pyproject.toml exists, post_install must write [tool.pytest.ini_options]."""
    t = CLITemplate(framework="typer", extras=[])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")

    t.post_install(tmp_path)

    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in content
    assert 'testpaths = ["tests"]' in content


def test_post_install_with_pytest_extra_writes_pytest_section(tmp_path):
    """post_install writes the pytest section regardless of the pytest extra."""
    t = CLITemplate(framework="typer", extras=["pytest"])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")

    t.post_install(tmp_path)

    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in content


# ---------------------------------------------------------------------------
# ruff and github-actions extras unaffected
# ---------------------------------------------------------------------------


def test_ruff_extra_still_writes_ruff_section(tmp_path):
    t = CLITemplate(framework="typer", extras=["ruff"])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")

    t.post_install(tmp_path)

    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.ruff]" in content


def test_github_actions_extra_creates_ci_yml(tmp_path):
    t = CLITemplate(framework="typer", extras=["github-actions"])
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")

    t.post_install(tmp_path)

    ci = tmp_path / ".github" / "workflows" / "ci.yml"
    assert ci.exists()
    assert "uv sync" in ci.read_text(encoding="utf-8")


def test_argparse_post_install_writes_pytest_section(tmp_path):
    """argparse has no runtime deps but should still get the pytest config."""
    t = CLITemplate(framework="argparse", extras=[])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")

    t.post_install(tmp_path)

    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in content
