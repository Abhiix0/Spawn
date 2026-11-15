from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from spawn.core.exceptions import FilesystemError, SpawnError
from spawn.generators.project_files import (
    add_mypy_config,
    add_pytest_config,
    add_ruff_config,
    write_agents_md_generic,
    write_changelog,
    write_ci_workflow,
    write_gitignore,
    write_license,
    write_precommit_config,
    write_readme_from_project,
    write_tests_dir,
)
from spawn.utils.doctor import HealthCheck
from spawn.utils.git import get_git_user_name, initialize_git


def _safe_write_path(project_path: Path, filename: str) -> Path:
    """Return the resolved write target, raising FilesystemError if it would
    escape *project_path* or write through a symlink to outside it.

    Rules
    -----
    - The final path must be a strict descendant of ``project_path.resolve()``.
    - Neither the target file itself nor any of its ancestor components (between
      the project root and the file) may be a symlink whose resolved destination
      lies outside the project root.
    - Dangling symlinks (symlinks that point to a non-existent target) are
      rejected unconditionally because we cannot verify where they point.
    """
    root = project_path.resolve()
    target = (project_path / filename).resolve()

    # The resolved target must be inside the project root.
    if not target.is_relative_to(root):
        raise FilesystemError(
            f"Doctor --fix refused: '{filename}' resolves outside the project root."
        )

    # Walk every path component between root and the final target.
    # Any intermediate symlink that exits the root is rejected.
    # Also reject dangling symlinks anywhere on the path.
    parts = Path(filename).parts
    partial = project_path
    for part in parts:
        partial = partial / part
        if partial.is_symlink():
            # Dangling symlink — target does not exist.
            if not partial.exists():
                raise FilesystemError(
                    f"Doctor --fix refused: '{filename}' contains a dangling symlink "
                    f"at '{partial.relative_to(project_path)}'."
                )
            # Symlink exists; ensure it resolves inside the root.
            resolved_part = partial.resolve()
            if not resolved_part.is_relative_to(root):
                raise FilesystemError(
                    f"Doctor --fix refused: '{filename}' contains a symlink that "
                    f"escapes the project root at "
                    f"'{partial.relative_to(project_path)}'."
                )
    return target


@dataclass
class FixAction:
    check: str
    description: str
    apply: Callable[[], bool]


@dataclass
class FixResult:
    action: FixAction
    status: str
    detail: str = ""


_ALWAYS_MANUAL: dict[str, str] = {
    "Dockerfile": "needs your app's entrypoint",
    ".env.example": "depends on your project's variables",
    "pyproject.toml": "run 'uv init'",
}

_DEV_TOOL_PACKAGES: list[tuple[str, str]] = [
    ("Pytest", "pytest"),
    ("Ruff", "ruff"),
    ("Type Checking", "mypy"),
    ("Pre-commit", "pre-commit"),
]


def _guarded(
    project_path: Path, filename: str, write_fn: Callable[[], bool]
) -> Callable[[], bool]:
    """Return a lambda that validates the write path before calling *write_fn*."""

    def _apply() -> bool:
        _safe_write_path(project_path, filename)
        return write_fn()

    return _apply


def plan_fixes(
    project_path: Path,
    checks: list[HealthCheck],
    license_kind: str | None = None,
) -> tuple[list[FixAction], list[tuple[str, str]]]:
    failed = {c.name for c in checks if not c.passed}
    has_pyproject = (project_path / "pyproject.toml").is_file()

    actions: list[FixAction] = []
    manual: list[tuple[str, str]] = []

    if "README.md" in failed:
        actions.append(
            FixAction(
                check="README.md",
                description="Create README.md",
                apply=_guarded(
                    project_path,
                    "README.md",
                    lambda: write_readme_from_project(project_path),
                ),
            )
        )

    if "AGENTS.md" in failed:
        actions.append(
            FixAction(
                check="AGENTS.md",
                description="Create AGENTS.md",
                apply=_guarded(
                    project_path,
                    "AGENTS.md",
                    lambda: write_agents_md_generic(project_path),
                ),
            )
        )

    if ".gitignore" in failed:
        actions.append(
            FixAction(
                check=".gitignore",
                description="Create .gitignore",
                apply=_guarded(
                    project_path, ".gitignore", lambda: write_gitignore(project_path)
                ),
            )
        )

    if "CHANGELOG.md" in failed:
        actions.append(
            FixAction(
                check="CHANGELOG.md",
                description="Create CHANGELOG.md",
                apply=_guarded(
                    project_path, "CHANGELOG.md", lambda: write_changelog(project_path)
                ),
            )
        )

    if "LICENSE" in failed:
        if license_kind == "mit":

            def _apply_license() -> bool:
                _safe_write_path(project_path, "LICENSE")
                holder = get_git_user_name() or f"{project_path.name} contributors"
                return write_license(project_path, "mit", holder)

            actions.append(
                FixAction(
                    check="LICENSE",
                    description="Create LICENSE (MIT)",
                    apply=_apply_license,
                )
            )
        else:
            manual.append(("LICENSE", "pass --license mit to add one"))

    if "Tests" in failed:
        actions.append(
            FixAction(
                check="Tests",
                description="Create tests/ directory",
                apply=_guarded(
                    project_path, "tests", lambda: write_tests_dir(project_path)
                ),
            )
        )

    if "Pytest" in failed:
        if has_pyproject:
            actions.append(
                FixAction(
                    check="Pytest",
                    description="Add Pytest configuration to pyproject.toml",
                    apply=_guarded(
                        project_path,
                        "pyproject.toml",
                        lambda: add_pytest_config(project_path),
                    ),
                )
            )
        else:
            manual.append(("Pytest", "no pyproject.toml"))

    if "Ruff" in failed:
        if has_pyproject:
            actions.append(
                FixAction(
                    check="Ruff",
                    description="Add Ruff configuration to pyproject.toml",
                    apply=_guarded(
                        project_path,
                        "pyproject.toml",
                        lambda: add_ruff_config(project_path),
                    ),
                )
            )
        else:
            manual.append(("Ruff", "no pyproject.toml"))

    if "Type Checking" in failed:
        if has_pyproject:
            actions.append(
                FixAction(
                    check="Type Checking",
                    description="Add Mypy configuration to pyproject.toml",
                    apply=_guarded(
                        project_path,
                        "pyproject.toml",
                        lambda: add_mypy_config(project_path),
                    ),
                )
            )
        else:
            manual.append(("Type Checking", "no pyproject.toml"))

    if "Pre-commit" in failed:
        actions.append(
            FixAction(
                check="Pre-commit",
                description="Create .pre-commit-config.yaml",
                apply=_guarded(
                    project_path,
                    ".pre-commit-config.yaml",
                    lambda: write_precommit_config(project_path),
                ),
            )
        )

    if "GitHub Actions" in failed:
        if has_pyproject:
            actions.append(
                FixAction(
                    check="GitHub Actions",
                    description="Create GitHub Actions CI workflow",
                    apply=_guarded(
                        project_path,
                        ".github/workflows/ci.yml",
                        lambda: write_ci_workflow(project_path),
                    ),
                )
            )
        else:
            manual.append(("GitHub Actions", "no pyproject.toml"))

    if "Git Repository" in failed:

        def _apply_git() -> bool:
            initialize_git(project_path)
            return True

        actions.append(
            FixAction(
                check="Git Repository",
                description="Initialize Git repository",
                apply=_apply_git,
            )
        )

    for check_name, reason in _ALWAYS_MANUAL.items():
        if check_name in failed:
            manual.append((check_name, reason))

    return actions, manual


def apply_fixes(actions: list[FixAction]) -> list[FixResult]:
    results: list[FixResult] = []
    for action in actions:
        try:
            ok = action.apply()
            if ok:
                results.append(FixResult(action=action, status="applied", detail=""))
            else:
                results.append(
                    FixResult(action=action, status="skipped", detail="already exists")
                )
        except (SpawnError, OSError) as e:
            results.append(FixResult(action=action, status="failed", detail=str(e)))
    return results


def tool_hints(results: list[FixResult]) -> list[str]:
    applied = {r.action.check for r in results if r.status == "applied"}
    tools = [pkg for check, pkg in _DEV_TOOL_PACKAGES if check in applied]
    hints: list[str] = []
    if tools:
        hints.append(f"uv add --dev {' '.join(tools)}")
    if "Pre-commit" in applied:
        hints.append("pre-commit install")
    return hints
