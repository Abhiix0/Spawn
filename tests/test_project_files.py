import datetime
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from spawn.core.exceptions import SpawnError
from spawn.generators.project_files import (
    _append_section,
    _write_new,
    add_mypy_config,
    add_pytest_config,
    add_ruff_config,
    declares_dependency,
    write_agents_md_generic,
    write_changelog,
    write_ci_workflow,
    write_gitignore,
    write_license,
    write_mypy_ini,
    write_precommit_config,
    write_readme_from_project,
    write_tests_dir,
)
from spawn.templates.shared_content import (
    CHANGELOG_CONTENT,
    GITIGNORE_CONTENT,
    MYPY_INI_CONTENT,
    MYPY_PYPROJECT_SECTION,
    PRECOMMIT_CONFIG_CONTENT,
    PYTEST_PYPROJECT_SECTION,
    RUFF_PYPROJECT_SECTION,
)
from spawn.utils.git import get_git_user_name


def test_write_new_creates_file_and_parents(tmp_path):
    target = tmp_path / "deep" / "nested" / "file.txt"
    assert _write_new(target, "hello world") is True
    assert target.read_text(encoding="utf-8") == "hello world"


def test_write_new_skips_when_exists(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("initial", encoding="utf-8")
    assert _write_new(target, "overwritten") is False
    assert target.read_text(encoding="utf-8") == "initial"


def test_append_section_success_and_idempotency(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'demo'\n", encoding="utf-8")

    assert _append_section(tmp_path, "[tool.ruff]", RUFF_PYPROJECT_SECTION) is True
    content_after_first = pyproject.read_text(encoding="utf-8")
    assert "[tool.ruff]" in content_after_first
    assert "line-length = 88" in content_after_first

    assert _append_section(tmp_path, "[tool.ruff]", RUFF_PYPROJECT_SECTION) is False
    assert pyproject.read_text(encoding="utf-8") == content_after_first


def test_append_section_missing_pyproject(tmp_path):
    assert _append_section(tmp_path, "[tool.ruff]", RUFF_PYPROJECT_SECTION) is False


def test_write_license_mit_success(tmp_path):
    assert write_license(tmp_path, "mit", "Test Holder", year=2025) is True
    license_file = tmp_path / "LICENSE"
    assert license_file.exists()
    content = license_file.read_text(encoding="utf-8")
    assert "Copyright (c) 2025 Test Holder" in content
    assert "MIT License" in content


def test_write_license_mit_default_year(tmp_path):
    assert write_license(tmp_path, "mit", "Test Holder") is True
    current_year = datetime.datetime.now(datetime.UTC).year
    content = (tmp_path / "LICENSE").read_text(encoding="utf-8")
    assert f"Copyright (c) {current_year} Test Holder" in content


def test_write_license_skips_when_file_exists(tmp_path):
    license_file = tmp_path / "LICENSE"
    license_file.write_text("custom license", encoding="utf-8")
    assert write_license(tmp_path, "mit", "Test Holder", year=2025) is False
    assert license_file.read_text(encoding="utf-8") == "custom license"


def test_write_license_none_returns_false(tmp_path):
    assert write_license(tmp_path, "none", "Test Holder") is False
    assert not (tmp_path / "LICENSE").exists()


def test_write_license_unsupported_raises(tmp_path):
    with pytest.raises(SpawnError, match="Unsupported license: 'apache'"):
        write_license(tmp_path, "apache", "Test Holder")


def test_write_changelog(tmp_path):
    assert write_changelog(tmp_path) is True
    changelog = tmp_path / "CHANGELOG.md"
    assert changelog.read_text(encoding="utf-8") == CHANGELOG_CONTENT
    assert write_changelog(tmp_path) is False
    assert changelog.read_text(encoding="utf-8") == CHANGELOG_CONTENT


def test_write_precommit_config(tmp_path):
    assert write_precommit_config(tmp_path) is True
    cfg = tmp_path / ".pre-commit-config.yaml"
    assert cfg.read_text(encoding="utf-8") == PRECOMMIT_CONFIG_CONTENT
    assert write_precommit_config(tmp_path) is False
    assert cfg.read_text(encoding="utf-8") == PRECOMMIT_CONFIG_CONTENT


def test_write_gitignore(tmp_path):
    assert write_gitignore(tmp_path) is True
    gitignore = tmp_path / ".gitignore"
    assert gitignore.read_text(encoding="utf-8") == GITIGNORE_CONTENT
    assert write_gitignore(tmp_path) is False
    assert gitignore.read_text(encoding="utf-8") == GITIGNORE_CONTENT


def test_add_ruff_config(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    assert add_ruff_config(tmp_path) is False
    pyproject.write_text("[project]\nname = 'test'\n", encoding="utf-8")
    assert add_ruff_config(tmp_path) is True
    assert "[tool.ruff]" in pyproject.read_text(encoding="utf-8")
    assert add_ruff_config(tmp_path) is False


def test_add_mypy_config(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    assert add_mypy_config(tmp_path) is False
    pyproject.write_text("[project]\nname = 'test'\n", encoding="utf-8")
    assert add_mypy_config(tmp_path) is True
    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.mypy]" in content
    assert MYPY_PYPROJECT_SECTION.strip() in content
    assert add_mypy_config(tmp_path) is False


def test_add_pytest_config(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    assert add_pytest_config(tmp_path) is False
    pyproject.write_text("[project]\nname = 'test'\n", encoding="utf-8")
    assert add_pytest_config(tmp_path) is True
    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in content
    assert PYTEST_PYPROJECT_SECTION.strip() in content
    assert add_pytest_config(tmp_path) is False


def test_write_mypy_ini(tmp_path):
    assert write_mypy_ini(tmp_path) is True
    ini = tmp_path / "mypy.ini"
    assert ini.read_text(encoding="utf-8") == MYPY_INI_CONTENT
    assert write_mypy_ini(tmp_path) is False
    assert ini.read_text(encoding="utf-8") == MYPY_INI_CONTENT


def test_declares_dependency(tmp_path):
    assert declares_dependency(tmp_path, "ruff") is False

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("invalid toml [[]", encoding="utf-8")
    assert declares_dependency(tmp_path, "ruff") is False

    pyproject.write_text(
        """[project]
dependencies = ["fastapi>=0.115.0", "uvicorn[standard]>=0.30.0"]

[dependency-groups]
dev = ["ruff>=0.15.16", "pytest>=9.0.3"]

[tool.uv]
dev-dependencies = ["mypy>=1.14.0"]
""",
        encoding="utf-8",
    )

    assert declares_dependency(tmp_path, "fastapi") is True
    assert declares_dependency(tmp_path, "uvicorn") is True
    assert declares_dependency(tmp_path, "ruff") is True
    assert declares_dependency(tmp_path, "RUFF") is True
    assert declares_dependency(tmp_path, "pytest") is True
    assert declares_dependency(tmp_path, "mypy") is True
    assert declares_dependency(tmp_path, "pytest-cov") is False
    assert declares_dependency(tmp_path, "flask") is False


def test_write_ci_workflow_no_dependencies(tmp_path):
    assert write_ci_workflow(tmp_path) is True
    ci_file = tmp_path / ".github" / "workflows" / "ci.yml"
    assert ci_file.exists()
    content = ci_file.read_text(encoding="utf-8")
    assert "name: CI" in content
    assert "Install dependencies" in content
    assert "uv run ruff check ." not in content
    assert "uv run pytest" not in content


def test_write_ci_workflow_step_selection(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
dependencies = ["ruff>=0.15.16", "pytest>=9.0.3"]
""",
        encoding="utf-8",
    )

    assert write_ci_workflow(tmp_path) is True
    ci_file = tmp_path / ".github" / "workflows" / "ci.yml"
    content = ci_file.read_text(encoding="utf-8")
    assert "uv run ruff check ." in content
    assert "uv run pytest" in content


def test_write_ci_workflow_ruff_only(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
dependencies = ["ruff>=0.15.16"]
""",
        encoding="utf-8",
    )

    assert write_ci_workflow(tmp_path) is True
    ci_file = tmp_path / ".github" / "workflows" / "ci.yml"
    content = ci_file.read_text(encoding="utf-8")
    assert "uv run ruff check ." in content
    assert "uv run pytest" not in content


def test_write_ci_workflow_skips_when_workflow_exists(tmp_path):
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    existing_yaml = workflows_dir / "build.yaml"
    existing_yaml.write_text("existing workflow", encoding="utf-8")

    assert write_ci_workflow(tmp_path) is False
    assert not (workflows_dir / "ci.yml").exists()
    assert existing_yaml.read_text(encoding="utf-8") == "existing workflow"


def test_write_ci_workflow_skips_when_ci_yml_exists(tmp_path):
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    ci_yml = workflows_dir / "ci.yml"
    ci_yml.write_text("existing ci", encoding="utf-8")

    assert write_ci_workflow(tmp_path) is False
    assert ci_yml.read_text(encoding="utf-8") == "existing ci"


def test_write_readme_from_project_with_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "awesome-app"
description = "An awesome application."
""",
        encoding="utf-8",
    )

    assert write_readme_from_project(tmp_path) is True
    readme = tmp_path / "README.md"
    assert (
        readme.read_text(encoding="utf-8")
        == "# awesome-app\n\nAn awesome application.\n"
    )

    assert write_readme_from_project(tmp_path) is False
    assert (
        readme.read_text(encoding="utf-8")
        == "# awesome-app\n\nAn awesome application.\n"
    )


def test_write_readme_from_project_without_pyproject(tmp_path):
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    assert write_readme_from_project(project_dir) is True
    readme = project_dir / "README.md"
    assert readme.read_text(encoding="utf-8") == "# my-project\n"


def test_write_readme_from_project_without_description(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """[project]
name = "simple-pkg"
""",
        encoding="utf-8",
    )
    assert write_readme_from_project(tmp_path) is True
    readme = tmp_path / "README.md"
    assert readme.read_text(encoding="utf-8") == "# simple-pkg\n"


def test_write_agents_md_generic_with_uv(tmp_path):
    (tmp_path / "uv.lock").touch()
    project_dir = tmp_path / "agent-project"
    project_dir.mkdir()
    (project_dir / "uv.lock").touch()

    assert write_agents_md_generic(project_dir) is True
    agents_md = project_dir / "AGENTS.md"
    content = agents_md.read_text(encoding="utf-8")
    assert "# Agent Context: agent-project" in content
    assert "uv sync" in content
    assert "uv run pytest" in content

    assert write_agents_md_generic(project_dir) is False


def test_write_agents_md_generic_without_uv(tmp_path):
    project_dir = tmp_path / "pip-project"
    project_dir.mkdir()

    assert write_agents_md_generic(project_dir) is True
    agents_md = project_dir / "AGENTS.md"
    content = agents_md.read_text(encoding="utf-8")
    assert "# Agent Context: pip-project" in content
    assert "pip install -e ." in content
    assert "```bash\npytest\n```" in content


def test_write_tests_dir(tmp_path):
    assert write_tests_dir(tmp_path) is True
    tests_dir = tmp_path / "tests"
    assert tests_dir.is_dir()
    init_file = tests_dir / "__init__.py"
    assert init_file.exists()
    assert init_file.read_text(encoding="utf-8") == ""

    existing_test = tests_dir / "test_example.py"
    existing_test.write_text("def test_one(): pass", encoding="utf-8")
    assert write_tests_dir(tmp_path) is False
    assert existing_test.read_text(encoding="utf-8") == "def test_one(): pass"


@patch("subprocess.run")
def test_get_git_user_name_success(mock_run):
    mock_run.return_value = MagicMock(stdout="Jane Doe\n")
    assert get_git_user_name() == "Jane Doe"
    mock_run.assert_called_once_with(
        ["git", "config", "user.name"],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("subprocess.run")
def test_get_git_user_name_empty(mock_run):
    mock_run.return_value = MagicMock(stdout="   \n")
    assert get_git_user_name() is None


@patch("subprocess.run")
def test_get_git_user_name_file_not_found(mock_run):
    mock_run.side_effect = FileNotFoundError
    assert get_git_user_name() is None


@patch("subprocess.run")
def test_get_git_user_name_called_process_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "config"])
    assert get_git_user_name() is None
