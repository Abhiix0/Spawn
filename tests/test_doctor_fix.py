from unittest.mock import patch

from spawn.core.exceptions import SpawnError
from spawn.generators.project_files import (
    write_gitignore,
    write_readme_from_project,
)
from spawn.utils.doctor import ProjectHealthChecker
from spawn.utils.doctor_fix import (
    FixAction,
    FixResult,
    apply_fixes,
    plan_fixes,
    tool_hints,
)


def test_bare_project_plan_apply_and_recheck(tmp_path):
    project = tmp_path / "my_proj"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "my_proj"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (project / "src").mkdir()
    (project / "src" / "main.py").write_text('print("hello")\n', encoding="utf-8")

    checker = ProjectHealthChecker(project)
    initial_checks = checker.run_all_checks()

    def fake_git(p):
        (p / ".git").mkdir()

    with patch("spawn.utils.doctor_fix.initialize_git", side_effect=fake_git):
        actions, _manual = plan_fixes(project, initial_checks, license_kind="mit")
        results = apply_fixes(actions)

    assert all(r.status == "applied" for r in results)

    fresh_checker = ProjectHealthChecker(project)
    post_checks = {c.name: c for c in fresh_checker.run_all_checks()}

    fixed_check_names = [a.check for a in actions]
    for name in fixed_check_names:
        assert post_checks[name].passed is True

    second_checks = fresh_checker.run_all_checks()
    second_actions, _ = plan_fixes(project, second_checks, license_kind="mit")
    assert second_actions == []


def test_preexisting_files_byte_identical(tmp_path):
    project = tmp_path / "my_proj"
    project.mkdir()
    readme = project / "README.md"
    readme_content = "# Custom Readme\nDo not overwrite.\n"
    readme.write_text(readme_content, encoding="utf-8")

    gitignore = project / ".gitignore"
    gi_content = "*.custom\n"
    gitignore.write_text(gi_content, encoding="utf-8")

    (project / "pyproject.toml").write_text(
        '[project]\nname = "my_proj"\n',
        encoding="utf-8",
    )

    action_readme = FixAction(
        "README.md", "desc", lambda: write_readme_from_project(project)
    )
    action_gi = FixAction(".gitignore", "desc", lambda: write_gitignore(project))
    results = apply_fixes([action_readme, action_gi])

    assert all(r.status == "skipped" for r in results)
    assert all(r.detail == "already exists" for r in results)
    assert readme.read_text(encoding="utf-8") == readme_content
    assert gitignore.read_text(encoding="utf-8") == gi_content


def test_no_pyproject_sends_config_fixers_to_manual(tmp_path):
    project = tmp_path / "no_pyproject"
    project.mkdir()

    checker = ProjectHealthChecker(project)
    checks = checker.run_all_checks()

    actions, manual = plan_fixes(project, checks)
    manual_dict = dict(manual)

    assert manual_dict["Pytest"] == "no pyproject.toml"
    assert manual_dict["Ruff"] == "no pyproject.toml"
    assert manual_dict["Type Checking"] == "no pyproject.toml"
    assert manual_dict["GitHub Actions"] == "no pyproject.toml"
    assert manual_dict["pyproject.toml"] == "run 'uv init'"

    action_checks = {a.check for a in actions}
    assert "Pytest" not in action_checks
    assert "Ruff" not in action_checks
    assert "Type Checking" not in action_checks
    assert "GitHub Actions" not in action_checks


def test_license_manual_without_license_kind(tmp_path):
    project = tmp_path / "lic_test"
    project.mkdir()
    checker = ProjectHealthChecker(project)
    checks = checker.run_all_checks()

    actions, manual = plan_fixes(project, checks, license_kind=None)
    manual_dict = dict(manual)
    assert manual_dict["LICENSE"] == "pass --license mit to add one"
    assert not any(a.check == "LICENSE" for a in actions)


def test_license_written_with_mit(tmp_path):
    project = tmp_path / "lic_test_mit"
    project.mkdir()
    checker = ProjectHealthChecker(project)
    checks = checker.run_all_checks()

    actions, _ = plan_fixes(project, checks, license_kind="mit")
    lic_action = next(a for a in actions if a.check == "LICENSE")
    results = apply_fixes([lic_action])

    assert results[0].status == "applied"
    lic_file = project / "LICENSE"
    assert lic_file.is_file()
    assert "MIT License" in lic_file.read_text(encoding="utf-8")


def test_ci_workflow_step_inclusion(tmp_path):
    p1 = tmp_path / "p1"
    p1.mkdir()
    (p1 / "pyproject.toml").write_text('[project]\nname = "p1"\n', encoding="utf-8")
    checker1 = ProjectHealthChecker(p1)
    actions1, _ = plan_fixes(p1, checker1.run_all_checks())
    ci_action1 = next(a for a in actions1 if a.check == "GitHub Actions")
    apply_fixes([ci_action1])
    ci_content1 = (p1 / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pytest" not in ci_content1
    assert "ruff" not in ci_content1

    p2 = tmp_path / "p2"
    p2.mkdir()
    (p2 / "pyproject.toml").write_text(
        '[project]\nname = "p2"\ndependencies = ["ruff", "pytest"]\n',
        encoding="utf-8",
    )
    checker2 = ProjectHealthChecker(p2)
    actions2, _ = plan_fixes(p2, checker2.run_all_checks())
    ci_action2 = next(a for a in actions2 if a.check == "GitHub Actions")
    apply_fixes([ci_action2])
    ci_content2 = (p2 / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "uv run pytest" in ci_content2
    assert "uv run ruff check" in ci_content2


def test_git_init_mock_and_failure_path(tmp_path):
    project = tmp_path / "git_fail"
    project.mkdir()
    checker = ProjectHealthChecker(project)
    actions, _ = plan_fixes(project, checker.run_all_checks())
    git_action = next(a for a in actions if a.check == "Git Repository")

    with patch("spawn.utils.doctor_fix.initialize_git") as mock_init:
        res = apply_fixes([git_action])
        assert res[0].status == "applied"
        assert res[0].detail == ""
        mock_init.assert_called_once_with(project)

    with patch(
        "spawn.utils.doctor_fix.initialize_git",
        side_effect=SpawnError("Git not found"),
    ):
        res = apply_fixes([git_action])
        assert res[0].status == "failed"
        assert res[0].detail == "Git not found"

    with patch(
        "spawn.utils.doctor_fix.initialize_git",
        side_effect=OSError("Disk error"),
    ):
        res = apply_fixes([git_action])
        assert res[0].status == "failed"
        assert res[0].detail == "Disk error"


def test_tool_hints():
    a_pytest = FixAction("Pytest", "", lambda: True)
    a_ruff = FixAction("Ruff", "", lambda: True)
    a_mypy = FixAction("Type Checking", "", lambda: True)
    a_precommit = FixAction("Pre-commit", "", lambda: True)
    a_readme = FixAction("README.md", "", lambda: True)

    results = [
        FixResult(a_pytest, "applied"),
        FixResult(a_ruff, "applied"),
        FixResult(a_mypy, "applied"),
        FixResult(a_precommit, "applied"),
    ]
    assert tool_hints(results) == [
        "uv add --dev pytest ruff mypy pre-commit",
        "pre-commit install",
    ]

    results_sub = [
        FixResult(a_pytest, "applied"),
        FixResult(a_precommit, "applied"),
    ]
    assert tool_hints(results_sub) == [
        "uv add --dev pytest pre-commit",
        "pre-commit install",
    ]

    results_non_tool = [
        FixResult(a_readme, "applied"),
    ]
    assert tool_hints(results_non_tool) == []

    results_skipped = [
        FixResult(a_pytest, "skipped", "already exists"),
    ]
    assert tool_hints(results_skipped) == []
