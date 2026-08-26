"""Tests for the spawn doctor health checker."""

import tempfile
from pathlib import Path

import pytest

from spawn.utils.doctor import (
    HealthCheck,
    ProjectHealthChecker,
)


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def complete_project(temp_project_dir):
    """Create a complete project structure for testing."""
    # Documentation
    (temp_project_dir / "README.md").write_text("# Test Project")
    (temp_project_dir / "AGENTS.md").write_text("# Agent Context")
    (temp_project_dir / "LICENSE").write_text("MIT License")
    (temp_project_dir / "CHANGELOG.md").write_text("# Changelog")

    # Version control
    (temp_project_dir / ".git").mkdir()
    (temp_project_dir / ".gitignore").write_text("*.pyc\n__pycache__/")

    # Quality
    (temp_project_dir / "tests").mkdir()
    (temp_project_dir / "tests" / "__init__.py").touch()

    # Automation
    (temp_project_dir / "Dockerfile").write_text("FROM python:3.12")
    workflows_dir = temp_project_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI")

    # Configuration
    (temp_project_dir / ".env.example").write_text("API_KEY=")

    # Python project files with ruff, pytest, mypy, and pre-commit
    pyproject = temp_project_dir / "pyproject.toml"
    pyproject.write_text("""\
[project]
name = "test-project"
dependencies = []

[dependency-groups]
dev = ["pytest>=9.0.0", "ruff>=0.15.0"]

[tool.ruff]
line-length = 88

[tool.mypy]
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
""")

    (temp_project_dir / ".pre-commit-config.yaml").write_text("repos: []")

    return temp_project_dir


@pytest.fixture
def minimal_project(temp_project_dir):
    """Create a minimal project with only essential files."""
    (temp_project_dir / "README.md").write_text("# Minimal Project")
    (temp_project_dir / ".git").mkdir()
    return temp_project_dir


class TestHealthCheck:
    """Tests for HealthCheck dataclass."""

    def test_health_check_creation(self):
        check = HealthCheck(
            name="Test Check",
            category="Testing",
            passed=True,
            message="Test passed",
            weight=10,
        )
        assert check.name == "Test Check"
        assert check.category == "Testing"
        assert check.passed is True
        assert check.message == "Test passed"
        assert check.weight == 10

    def test_health_check_default_weight(self):
        check = HealthCheck(
            name="Test",
            category="Testing",
            passed=False,
            message="Failed",
        )
        assert check.weight == 10


class TestProjectHealthChecker:
    """Tests for ProjectHealthChecker class."""

    def test_checker_initialization_default_path(self):
        checker = ProjectHealthChecker()
        assert checker.project_path == Path.cwd()

    def test_checker_initialization_custom_path(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        assert checker.project_path == temp_project_dir

    # Documentation Checks

    def test_check_readme_exists(self, temp_project_dir):
        (temp_project_dir / "README.md").write_text("# Test")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_readme()
        assert result.name == "README.md"
        assert result.category == "Documentation"
        assert result.passed is True
        assert "present" in result.message.lower()

    def test_check_readme_missing(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_readme()
        assert result.passed is False
        assert "missing" in result.message.lower()

    def test_check_license_exists(self, temp_project_dir):
        (temp_project_dir / "LICENSE").write_text("MIT")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_license()
        assert result.name == "LICENSE"
        assert result.passed is True

    def test_check_license_missing(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_license()
        assert result.passed is False

    # Version Control Checks

    def test_check_git_repository_exists(self, temp_project_dir):
        (temp_project_dir / ".git").mkdir()
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_git_repository()
        assert result.name == "Git Repository"
        assert result.category == "Version Control"
        assert result.passed is True
        assert "initialized" in result.message.lower()

    def test_check_git_repository_missing(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_git_repository()
        assert result.passed is False
        assert "not a git repository" in result.message.lower()

    def test_check_gitignore_exists(self, temp_project_dir):
        (temp_project_dir / ".gitignore").write_text("*.pyc")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_gitignore()
        assert result.name == ".gitignore"
        assert result.passed is True

    def test_check_gitignore_missing(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_gitignore()
        assert result.passed is False

    # Testing Checks

    def test_check_tests_directory_exists(self, temp_project_dir):
        (temp_project_dir / "tests").mkdir()
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_tests_directory()
        assert result.name == "Tests"
        assert result.category == "Testing"
        assert result.passed is True

    def test_check_tests_directory_missing(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_tests_directory()
        assert result.passed is False

    def test_check_ruff_in_pyproject_tool_section(self, temp_project_dir):
        (temp_project_dir / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88"
        )
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_ruff_configured()
        assert result.name == "Ruff"
        assert result.passed is True
        assert "pyproject.toml" in result.message

    def test_check_ruff_in_pyproject_dependency(self, temp_project_dir):
        (temp_project_dir / "pyproject.toml").write_text(
            '[dependency-groups]\ndev = ["ruff>=0.15.0"]'
        )
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_ruff_configured()
        assert result.passed is True
        assert "dependency" in result.message

    def test_check_ruff_in_ruff_toml(self, temp_project_dir):
        (temp_project_dir / "ruff.toml").write_text("line-length = 88")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_ruff_configured()
        assert result.passed is True
        assert "ruff.toml" in result.message

    def test_check_ruff_not_configured(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_ruff_configured()
        assert result.passed is False
        assert "not configured" in result.message

    def test_check_pytest_in_pyproject_tool_section(self, temp_project_dir):
        (temp_project_dir / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\ntestpaths = ['tests']"
        )
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_pytest_configured()
        assert result.name == "Pytest"
        assert result.passed is True
        assert "pyproject.toml" in result.message

    def test_check_pytest_in_pyproject_dependency(self, temp_project_dir):
        (temp_project_dir / "pyproject.toml").write_text(
            '[dependency-groups]\ndev = ["pytest>=9.0.0"]'
        )
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_pytest_configured()
        assert result.passed is True

    def test_check_pytest_in_pytest_ini(self, temp_project_dir):
        (temp_project_dir / "pytest.ini").write_text("[pytest]\ntestpaths = tests")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_pytest_configured()
        assert result.passed is True
        assert "pytest.ini" in result.message

    def test_check_pytest_not_configured(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_pytest_configured()
        assert result.passed is False

    # Automation Checks

    def test_check_dockerfile_exists(self, temp_project_dir):
        (temp_project_dir / "Dockerfile").write_text("FROM python:3.12")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_dockerfile()
        assert result.name == "Dockerfile"
        assert result.category == "Automation"
        assert result.passed is True

    def test_check_dockerfile_missing(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_dockerfile()
        assert result.passed is False

    def test_check_github_actions_with_workflows(self, temp_project_dir):
        workflows_dir = temp_project_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "ci.yml").write_text("name: CI")
        (workflows_dir / "deploy.yaml").write_text("name: Deploy")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_github_actions()
        assert result.name == "GitHub Actions"
        assert result.passed is True
        assert "2 workflows" in result.message

    def test_check_github_actions_without_workflows(self, temp_project_dir):
        workflows_dir = temp_project_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_github_actions()
        assert result.passed is False
        assert "not configured" in result.message

    def test_check_github_actions_missing_directory(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_github_actions()
        assert result.passed is False

    # Configuration Checks

    def test_check_env_example_exists(self, temp_project_dir):
        (temp_project_dir / ".env.example").write_text("API_KEY=")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_env_example()
        assert result.name == ".env.example"
        assert result.category == "Configuration"
        assert result.passed is True

    def test_check_env_example_missing(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_env_example()
        assert result.passed is False

    # Integration Tests

    def test_run_all_checks_complete_project(self, complete_project):
        checker = ProjectHealthChecker(complete_project)
        checks = checker.run_all_checks()
        assert len(checks) == 15
        assert all(isinstance(c, HealthCheck) for c in checks)
        assert all(c.passed for c in checks), [c for c in checks if not c.passed]

    def test_run_all_checks_minimal_project(self, minimal_project):
        checker = ProjectHealthChecker(minimal_project)
        checks = checker.run_all_checks()
        assert len(checks) == 15
        passed = [c for c in checks if c.passed]
        assert len(passed) == 2  # README + Git

    def test_run_all_checks_empty_project(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        checks = checker.run_all_checks()
        assert len(checks) == 15
        assert all(not c.passed for c in checks)

    # Scoring Tests

    def test_calculate_score_all_passed(self, complete_project):
        checker = ProjectHealthChecker(complete_project)
        checks = checker.run_all_checks()
        score, max_score = checker.calculate_score(checks)
        assert score == max_score
        assert max_score == 135

    def test_calculate_score_none_passed(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        checks = checker.run_all_checks()
        score, max_score = checker.calculate_score(checks)
        assert score == 0
        assert max_score == 135

    def test_calculate_score_empty_checks(self):
        checker = ProjectHealthChecker()
        score, max_score = checker.calculate_score([])
        assert score == 0
        assert max_score == 0

    def test_calculate_score_weighted(self, temp_project_dir):
        (temp_project_dir / ".git").mkdir()  # weight 15
        (temp_project_dir / "tests").mkdir()  # weight 15
        checker = ProjectHealthChecker(temp_project_dir)
        checks = checker.run_all_checks()
        score, max_score = checker.calculate_score(checks)
        assert score == 30
        assert max_score == 135

    # Grouping Tests

    def test_group_checks_by_category(self, complete_project):
        checker = ProjectHealthChecker(complete_project)
        checks = checker.run_all_checks()
        cats = checker.group_checks_by_category(checks)

        assert "Documentation" in cats
        assert "Version Control" in cats
        assert "Testing" in cats
        assert "Automation" in cats
        assert "Configuration" in cats
        assert "Code Quality" in cats

        assert (
            len(cats["Documentation"]) == 4
        )  # README + AGENTS.md + LICENSE + CHANGELOG
        assert len(cats["Version Control"]) == 2  # git + .gitignore
        assert len(cats["Testing"]) == 2  # Tests + Pytest
        assert len(cats["Automation"]) == 2  # Dockerfile + GitHub Actions
        assert len(cats["Configuration"]) == 2  # .env.example + pyproject.toml
        assert len(cats["Code Quality"]) == 3  # Ruff + TypeChecker + Pre-commit

    # Recommendations Tests

    def test_generate_recommendations_complete_project(self, complete_project):
        checker = ProjectHealthChecker(complete_project)
        checks = checker.run_all_checks()
        recs = checker.generate_recommendations(checks)
        assert len(recs) == 0

    def test_generate_recommendations_empty_project(self, temp_project_dir):
        checker = ProjectHealthChecker(temp_project_dir)
        checks = checker.run_all_checks()
        recs = checker.generate_recommendations(checks)
        assert len(recs) == 15
        assert "git init" in recs[0].lower()

    def test_generate_recommendations_prioritization(self, temp_project_dir):
        (temp_project_dir / ".git").mkdir()
        (temp_project_dir / "README.md").write_text("# Test")
        (temp_project_dir / "tests").mkdir()
        (temp_project_dir / ".gitignore").write_text("*.pyc")
        checker = ProjectHealthChecker(temp_project_dir)
        checks = checker.run_all_checks()
        recs = checker.generate_recommendations(checks)
        assert len(recs) == 11  # 15 - 4 passing
        assert any("pytest" in r.lower() for r in recs[:3])

    def test_format_report_runs_without_error(self, complete_project, capsys):
        checker = ProjectHealthChecker(complete_project)
        checks = checker.run_all_checks()
        checker.format_report(checks)
        captured = capsys.readouterr()
        assert len(captured.out) > 0 or len(captured.err) > 0


class TestRunHealthCheck:
    def test_run_health_check_default_path(self, capsys):
        from spawn.utils.doctor import run_health_check

        run_health_check()
        captured = capsys.readouterr()
        assert len(captured.out) > 0 or len(captured.err) > 0

    def test_run_health_check_custom_path(self, complete_project, capsys):
        from spawn.utils.doctor import run_health_check

        run_health_check(complete_project)
        captured = capsys.readouterr()
        assert len(captured.out) > 0 or len(captured.err) > 0


def test_doctor_with_valid_path(tmp_path):
    from spawn.utils.doctor import ProjectHealthChecker

    checker = ProjectHealthChecker(tmp_path)
    checks = checker.run_all_checks()
    assert isinstance(checks, list)
    assert len(checks) == 15


def test_doctor_with_invalid_path(tmp_path):
    from spawn.utils.doctor import ProjectHealthChecker

    checker = ProjectHealthChecker(Path("/nonexistent/path/xyz"))
    checks = checker.run_all_checks()
    assert all(not c.passed for c in checks)


# ---------------------------------------------------------------------------
# New checks: CHANGELOG.md and pyproject.toml
# ---------------------------------------------------------------------------


def test_check_changelog_passes_when_present(tmp_path):
    (tmp_path / "CHANGELOG.md").write_text("# Changelog")
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_changelog()
    assert result.name == "CHANGELOG.md"
    assert result.category == "Documentation"
    assert result.passed is True
    assert "present" in result.message.lower()


def test_check_changelog_fails_when_missing(tmp_path):
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_changelog()
    assert result.passed is False
    assert "missing" in result.message.lower()


def test_check_pyproject_passes_when_present(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_pyproject()
    assert result.name == "pyproject.toml"
    assert result.category == "Configuration"
    assert result.passed is True


def test_check_pyproject_fails_when_missing(tmp_path):
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_pyproject()
    assert result.passed is False
    assert "missing" in result.message.lower()


# ---------------------------------------------------------------------------
# Code Quality new checks
# ---------------------------------------------------------------------------


def test_check_type_checker_detects_mypy_ini(tmp_path):
    (tmp_path / "mypy.ini").write_text("[mypy]\nstrict = True")
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_type_checker_configured()
    assert result.category == "Code Quality"
    assert result.passed is True
    assert "mypy.ini" in result.message


def test_check_type_checker_detects_pyproject_section(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_type_checker_configured()
    assert result.passed is True
    assert "mypy" in result.message.lower()


def test_check_type_checker_detects_pyrightconfig(tmp_path):
    (tmp_path / "pyrightconfig.json").write_text("{}")
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_type_checker_configured()
    assert result.passed is True
    assert "pyrightconfig.json" in result.message


def test_check_type_checker_fails_when_missing(tmp_path):
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_type_checker_configured()
    assert result.passed is False
    assert "not configured" in result.message.lower()


def test_check_precommit_configured(tmp_path):
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []")
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_precommit_configured()
    assert result.name == "Pre-commit"
    assert result.category == "Code Quality"
    assert result.passed is True


def test_check_precommit_fails_when_missing(tmp_path):
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_precommit_configured()
    assert result.passed is False


# ---------------------------------------------------------------------------
# Category assertions
# ---------------------------------------------------------------------------


def test_ruff_check_category_is_code_quality(tmp_path):
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_ruff_configured()
    assert result.category == "Code Quality"


def test_tests_check_category_is_testing(tmp_path):
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_tests_directory()
    assert result.category == "Testing"


def test_dockerfile_check_category_is_automation(tmp_path):
    checker = ProjectHealthChecker(tmp_path)
    result = checker.check_dockerfile()
    assert result.category == "Automation"


# ---------------------------------------------------------------------------
# Per-category scoring
# ---------------------------------------------------------------------------


def test_calculate_category_scores_returns_all_categories(tmp_path):
    checker = ProjectHealthChecker(tmp_path)
    checks = checker.run_all_checks()
    scores = checker.calculate_category_scores(checks)
    for cat in (
        "Documentation",
        "Version Control",
        "Configuration",
        "Testing",
        "Automation",
        "Code Quality",
    ):
        assert cat in scores, f"Missing category: {cat}"


def test_calculate_category_scores_correct_math():
    checks = [
        HealthCheck("A", "Documentation", passed=True, message="", weight=10),
        HealthCheck("B", "Documentation", passed=False, message="", weight=5),
        HealthCheck("C", "Testing", passed=True, message="", weight=15),
    ]
    checker = ProjectHealthChecker()
    scores = checker.calculate_category_scores(checks)
    assert scores["Documentation"] == (10, 15)
    assert scores["Testing"] == (15, 15)


# ---------------------------------------------------------------------------
# Health rating
# ---------------------------------------------------------------------------


def test_health_rating_excellent():
    checker = ProjectHealthChecker()
    emoji, label, _ = checker.get_health_rating(90)
    assert emoji == "🟢"
    assert label == "Excellent"
    emoji2, label2, _ = checker.get_health_rating(100)
    assert label2 == "Excellent"


def test_health_rating_good():
    checker = ProjectHealthChecker()
    emoji, label, _ = checker.get_health_rating(70)
    assert emoji == "🟡"
    assert label == "Good"
    emoji2, label2, _ = checker.get_health_rating(89)
    assert label2 == "Good"


def test_health_rating_fair():
    checker = ProjectHealthChecker()
    emoji, label, _ = checker.get_health_rating(50)
    assert emoji == "🟠"
    assert label == "Fair"
    emoji2, label2, _ = checker.get_health_rating(69)
    assert label2 == "Fair"


def test_health_rating_needs_attention():
    checker = ProjectHealthChecker()
    emoji, label, _ = checker.get_health_rating(49)
    assert emoji == "🔴"
    assert label == "Needs Attention"
    emoji2, label2, _ = checker.get_health_rating(0)
    assert label2 == "Needs Attention"


# ---------------------------------------------------------------------------
# Tiered recommendations
# ---------------------------------------------------------------------------


def test_recommendations_are_tiered():
    """Critical items must appear before Recommended before Optional."""
    checks = [
        HealthCheck(
            "Git Repository", "Version Control", passed=False, message="", weight=15
        ),
        HealthCheck("Ruff", "Code Quality", passed=False, message="", weight=10),
        HealthCheck("Dockerfile", "Automation", passed=False, message="", weight=10),
    ]
    checker = ProjectHealthChecker()
    recs = checker.generate_recommendations(checks)
    assert len(recs) == 3
    # Git Repository is Critical → must be first
    assert "git" in recs[0].lower()
    # Ruff is Recommended, Dockerfile is Optional → Ruff before Dockerfile
    ruff_idx = next(i for i, r in enumerate(recs) if "ruff" in r.lower())
    docker_idx = next(i for i, r in enumerate(recs) if "docker" in r.lower())
    assert ruff_idx < docker_idx


def test_passed_check_never_recommended():
    """A passing Ruff check must never appear in recommendations."""
    checks = [
        HealthCheck("Ruff", "Code Quality", passed=True, message="ok", weight=10),
        HealthCheck("Tests", "Testing", passed=False, message="", weight=15),
    ]
    checker = ProjectHealthChecker()
    recs = checker.generate_recommendations(checks)
    assert all("ruff" not in r.lower() for r in recs)
    assert len(recs) == 1


# ---------------------------------------------------------------------------
# Next Best Step
# ---------------------------------------------------------------------------


def test_next_best_step_returns_none_when_all_pass():
    checks = [
        HealthCheck(
            "Git Repository", "Version Control", passed=True, message="ok", weight=15
        ),
        HealthCheck("README.md", "Documentation", passed=True, message="ok", weight=10),
    ]
    checker = ProjectHealthChecker()
    result = checker.get_next_best_step(checks)
    assert result is None


def test_next_best_step_prioritizes_critical():
    """Git failing + LICENSE failing → next best step must be about Git."""
    checks = [
        HealthCheck(
            "Git Repository", "Version Control", passed=False, message="", weight=15
        ),
        HealthCheck("LICENSE", "Documentation", passed=False, message="", weight=5),
    ]
    checker = ProjectHealthChecker()
    rec_text, effort = checker.get_next_best_step(checks)
    assert "git" in rec_text.lower()


def test_next_best_step_has_effort_estimate():
    checks = [
        HealthCheck("Tests", "Testing", passed=False, message="", weight=15),
    ]
    checker = ProjectHealthChecker()
    rec_text, effort = checker.get_next_best_step(checks)
    assert isinstance(effort, str)
    assert len(effort) > 0
