import datetime
import re
import tomllib
from pathlib import Path

from spawn.core.exceptions import InvalidInputError
from spawn.templates.shared_content import (
    AGENTS_MD_FIX_CONTENT,
    CHANGELOG_CONTENT,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITIGNORE_CONTENT,
    MIT_LICENSE_CONTENT,
    MYPY_INI_CONTENT,
    MYPY_PYPROJECT_SECTION,
    PRECOMMIT_CONFIG_CONTENT,
    PYTEST_PYPROJECT_SECTION,
    RUFF_PYPROJECT_SECTION,
)

SUPPORTED_LICENSES = ["mit", "none"]


def _write_new(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _append_section(project_path: Path, marker: str, section: str) -> bool:
    pyproject = project_path / "pyproject.toml"
    if not pyproject.exists():
        return False
    text = pyproject.read_text(encoding="utf-8")
    if marker in text:
        return False
    pyproject.write_text(text + section, encoding="utf-8")
    return True


def write_license(
    project_path: Path,
    kind: str,
    holder: str,
    year: int | None = None,
) -> bool:
    if kind == "none":
        return False
    if kind == "mit":
        target_year = year or datetime.datetime.now(datetime.UTC).year
        content = MIT_LICENSE_CONTENT.format(year=target_year, holder=holder)
        return _write_new(project_path / "LICENSE", content)
    raise InvalidInputError(f"Unsupported license: '{kind}'.")


def write_changelog(project_path: Path) -> bool:
    return _write_new(project_path / "CHANGELOG.md", CHANGELOG_CONTENT)


def write_precommit_config(project_path: Path) -> bool:
    return _write_new(
        project_path / ".pre-commit-config.yaml", PRECOMMIT_CONFIG_CONTENT
    )


def write_gitignore(project_path: Path) -> bool:
    return _write_new(project_path / ".gitignore", GITIGNORE_CONTENT)


def add_ruff_config(project_path: Path) -> bool:
    return _append_section(project_path, "[tool.ruff]", RUFF_PYPROJECT_SECTION)


def add_mypy_config(project_path: Path) -> bool:
    return _append_section(project_path, "[tool.mypy]", MYPY_PYPROJECT_SECTION)


def add_pytest_config(project_path: Path) -> bool:
    return _append_section(project_path, "[tool.pytest", PYTEST_PYPROJECT_SECTION)


def write_mypy_ini(project_path: Path) -> bool:
    return _write_new(project_path / "mypy.ini", MYPY_INI_CONTENT)


def declares_dependency(project_path: Path, name: str) -> bool:
    pyproject = project_path / "pyproject.toml"
    if not pyproject.exists():
        return False
    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return False

    requirements: list[str] = []
    project = data.get("project")
    if isinstance(project, dict):
        deps = project.get("dependencies")
        if isinstance(deps, list):
            for item in deps:
                if isinstance(item, str):
                    requirements.append(item)

    dep_groups = data.get("dependency-groups")
    if isinstance(dep_groups, dict):
        for group in dep_groups.values():
            if isinstance(group, list):
                for item in group:
                    if isinstance(item, str):
                        requirements.append(item)

    tool = data.get("tool")
    if isinstance(tool, dict):
        uv = tool.get("uv")
        if isinstance(uv, dict):
            uv_dev = uv.get("dev-dependencies")
            if isinstance(uv_dev, list):
                for item in uv_dev:
                    if isinstance(item, str):
                        requirements.append(item)

    target = name.lower()
    for req in requirements:
        match = re.match(r"[A-Za-z0-9_.-]+", req)
        if match and match.group(0).lower() == target:
            return True
    return False


def write_ci_workflow(project_path: Path) -> bool:
    workflows_dir = project_path / ".github" / "workflows"
    if workflows_dir.is_dir() and (
        any(workflows_dir.glob("*.yml")) or any(workflows_dir.glob("*.yaml"))
    ):
        return False
    content = GITHUB_ACTIONS_CI_BASE
    if declares_dependency(project_path, "ruff"):
        content += GITHUB_ACTIONS_CI_RUFF_STEP
    if declares_dependency(project_path, "pytest"):
        content += GITHUB_ACTIONS_CI_PYTEST_STEP
    return _write_new(workflows_dir / "ci.yml", content)


def write_readme_from_project(project_path: Path) -> bool:
    name = project_path.name
    description = None
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            with pyproject.open("rb") as f:
                data = tomllib.load(f)
            project = data.get("project")
            if isinstance(project, dict):
                proj_name = project.get("name")
                if isinstance(proj_name, str) and proj_name.strip():
                    name = proj_name
                proj_desc = project.get("description")
                if isinstance(proj_desc, str) and proj_desc:
                    description = proj_desc
        except (OSError, tomllib.TOMLDecodeError):
            pass

    content = f"# {name}\n"
    if description:
        content += f"\n{description}\n"
    return _write_new(project_path / "README.md", content)


def write_agents_md_generic(project_path: Path) -> bool:
    uv = (project_path / "uv.lock").exists()
    install_cmd = "uv sync" if uv else "pip install -e ."
    test_cmd = "uv run pytest" if uv else "pytest"
    content = AGENTS_MD_FIX_CONTENT.format(
        project_name=project_path.name,
        install_cmd=install_cmd,
        test_cmd=test_cmd,
    )
    return _write_new(project_path / "AGENTS.md", content)


def write_tests_dir(project_path: Path) -> bool:
    tests_dir = project_path / "tests"
    if tests_dir.exists():
        return False
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    return True
