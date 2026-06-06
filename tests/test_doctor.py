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
    (temp_project_dir / "LICENSE").write_text("MIT License")

    # Version control
    (temp_project_dir / ".git").mkdir()
    (temp_project_dir / ".gitignore").write_text("*.pyc\n__pycache__/")

    # Quality
    (temp_project_dir / "tests").mkdir()
    (temp_project_dir / "tests" / "__init__.py").touch()

    # Deployment
    (temp_project_dir / "Dockerfile").write_text("FROM python:3.12")
    workflows_dir = temp_project_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI")

    # Configuration
    (temp_project_dir / ".env.example").write_text("API_KEY=")

    # Python project files with ruff and pytest
    pyproject = temp_project_dir / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-project"
dependencies = []

[dependency-groups]
dev = ["pytest>=9.0.0", "ruff>=0.15.0"]

[tool.ruff]
line-length = 88
""")

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
        """Test creating a HealthCheck instance."""
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
        """Test HealthCheck with default weight."""
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
        """Test checker initializes with current directory by default."""
        checker = ProjectHealthChecker()
        assert checker.project_path == Path.cwd()

    def test_checker_initialization_custom_path(self, temp_project_dir):
        """Test checker initializes with custom path."""
        checker = ProjectHealthChecker(temp_project_dir)
        assert checker.project_path == temp_project_dir

    # Documentation Checks

    def test_check_readme_exists(self, temp_project_dir):
        """Test README.md check when file exists."""
        (temp_project_dir / "README.md").write_text("# Test")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_readme()

        assert result.name == "README.md"
        assert result.category == "Documentation"
        assert result.passed is True
        assert "present" in result.message.lower()

    def test_check_readme_missing(self, temp_project_dir):
        """Test README.md check when file is missing."""
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_readme()

        assert result.passed is False
        assert "missing" in result.message.lower()

    def test_check_license_exists(self, temp_project_dir):
        """Test LICENSE check when file exists."""
        (temp_project_dir / "LICENSE").write_text("MIT")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_license()

        assert result.name == "LICENSE"
        assert result.passed is True

    def test_check_license_missing(self, temp_project_dir):
        """Test LICENSE check when file is missing."""
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_license()

        assert result.passed is False

    # Version Control Checks

    def test_check_git_repository_exists(self, temp_project_dir):
        """Test git repository check when .git exists."""
        (temp_project_dir / ".git").mkdir()
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_git_repository()

        assert result.name == "Git Repository"
        assert result.category == "Version Control"
        assert result.passed is True
        assert "initialized" in result.message.lower()

    def test_check_git_repository_missing(self, temp_project_dir):
        """Test git repository check when .git is missing."""
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_git_repository()

        assert result.passed is False
        assert "not a git repository" in result.message.lower()

    def test_check_gitignore_exists(self, temp_project_dir):
        """Test .gitignore check when file exists."""
        (temp_project_dir / ".gitignore").write_text("*.pyc")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_gitignore()

        assert result.name == ".gitignore"
        assert result.passed is True

    def test_check_gitignore_missing(self, temp_project_dir):
        """Test .gitignore check when file is missing."""
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_gitignore()

        assert result.passed is False

    # Quality Checks

    def test_check_tests_directory_exists(self, temp_project_dir):
        """Test tests directory check when directory exists."""
        (temp_project_dir / "tests").mkdir()
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_tests_directory()

        assert result.name == "Tests"
        assert result.category == "Quality"
        assert result.passed is True

    def test_check_tests_directory_missing(self, temp_project_dir):
        """Test tests directory check when directory is missing."""
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_tests_directory()

        assert result.passed is False

    def test_check_ruff_in_pyproject_tool_section(self, temp_project_dir):
        """Test Ruff check with [tool.ruff] in pyproject.toml."""
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 88")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_ruff_configured()

        assert result.name == "Ruff"
        assert result.passed is True
        assert "pyproject.toml" in result.message

    def test_check_ruff_in_pyproject_dependency(self, temp_project_dir):
        """Test Ruff check with ruff as dependency in pyproject.toml."""
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[dependency-groups]\ndev = ["ruff>=0.15.0"]')
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_ruff_configured()

        assert result.passed is True
        assert "dependency" in result.message

    def test_check_ruff_in_ruff_toml(self, temp_project_dir):
        """Test Ruff check with ruff.toml file."""
        (temp_project_dir / "ruff.toml").write_text("line-length = 88")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_ruff_configured()

        assert result.passed is True
        assert "ruff.toml" in result.message

    def test_check_ruff_not_configured(self, temp_project_dir):
        """Test Ruff check when not configured."""
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_ruff_configured()

        assert result.passed is False
        assert "not configured" in result.message

    def test_check_pytest_in_pyproject_tool_section(self, temp_project_dir):
        """Test Pytest check with [tool.pytest] in pyproject.toml."""
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("[tool.pytest.ini_options]\ntestpaths = ['tests']")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_pytest_configured()

        assert result.name == "Pytest"
        assert result.passed is True
        assert "pyproject.toml" in result.message

    def test_check_pytest_in_pyproject_dependency(self, temp_project_dir):
        """Test Pytest check with pytest as dependency."""
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[dependency-groups]\ndev = ["pytest>=9.0.0"]')
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_pytest_configured()

        assert result.passed is True

    def test_check_pytest_in_pytest_ini(self, temp_project_dir):
        """Test Pytest check with pytest.ini file."""
        (temp_project_dir / "pytest.ini").write_text("[pytest]\ntestpaths = tests")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_pytest_configured()

        assert result.passed is True
        assert "pytest.ini" in result.message

    def test_check_pytest_not_configured(self, temp_project_dir):
        """Test Pytest check when not configured."""
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_pytest_configured()

        assert result.passed is False

    # Deployment Checks

    def test_check_dockerfile_exists(self, temp_project_dir):
        """Test Dockerfile check when file exists."""
        (temp_project_dir / "Dockerfile").write_text("FROM python:3.12")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_dockerfile()

        assert result.name == "Dockerfile"
        assert result.category == "Deployment"
        assert result.passed is True

    def test_check_dockerfile_missing(self, temp_project_dir):
        """Test Dockerfile check when file is missing."""
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_dockerfile()

        assert result.passed is False

    def test_check_github_actions_with_workflows(self, temp_project_dir):
        """Test GitHub Actions check with workflow files."""
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
        """Test GitHub Actions check without workflow files."""
        workflows_dir = temp_project_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_github_actions()

        assert result.passed is False
        assert "not configured" in result.message

    def test_check_github_actions_missing_directory(self, temp_project_dir):
        """Test GitHub Actions check when directory is missing."""
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_github_actions()

        assert result.passed is False

    # Configuration Checks

    def test_check_env_example_exists(self, temp_project_dir):
        """Test .env.example check when file exists."""
        (temp_project_dir / ".env.example").write_text("API_KEY=")
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_env_example()

        assert result.name == ".env.example"
        assert result.category == "Configuration"
        assert result.passed is True

    def test_check_env_example_missing(self, temp_project_dir):
        """Test .env.example check when file is missing."""
        checker = ProjectHealthChecker(temp_project_dir)
        result = checker.check_env_example()

        assert result.passed is False

    # Integration Tests

    def test_run_all_checks_complete_project(self, complete_project):
        """Test running all checks on a complete project."""
        checker = ProjectHealthChecker(complete_project)
        checks = checker.run_all_checks()

        assert len(checks) == 10
        assert all(isinstance(check, HealthCheck) for check in checks)
        # All checks should pass for complete project
        assert all(check.passed for check in checks)

    def test_run_all_checks_minimal_project(self, minimal_project):
        """Test running all checks on a minimal project."""
        checker = ProjectHealthChecker(minimal_project)
        checks = checker.run_all_checks()

        assert len(checks) == 10
        # Only README and Git should pass
        passed_checks = [check for check in checks if check.passed]
        assert len(passed_checks) == 2

    def test_run_all_checks_empty_project(self, temp_project_dir):
        """Test running all checks on an empty project."""
        checker = ProjectHealthChecker(temp_project_dir)
        checks = checker.run_all_checks()

        assert len(checks) == 10
        # No checks should pass
        assert all(not check.passed for check in checks)

    # Scoring Tests

    def test_calculate_score_all_passed(self, complete_project):
        """Test score calculation when all checks pass."""
        checker = ProjectHealthChecker(complete_project)
        checks = checker.run_all_checks()
        score, max_score = checker.calculate_score(checks)

        assert score == max_score
        assert max_score == 100  # Sum of all weights

    def test_calculate_score_none_passed(self, temp_project_dir):
        """Test score calculation when no checks pass."""
        checker = ProjectHealthChecker(temp_project_dir)
        checks = checker.run_all_checks()
        score, max_score = checker.calculate_score(checks)

        assert score == 0
        assert max_score == 100

    def test_calculate_score_empty_checks(self):
        """Test score calculation with empty checks list."""
        checker = ProjectHealthChecker()
        score, max_score = checker.calculate_score([])

        assert score == 0
        assert max_score == 0

    def test_calculate_score_weighted(self, temp_project_dir):
        """Test that scoring is properly weighted."""
        # Create a project with only high-weight items
        (temp_project_dir / ".git").mkdir()  # Weight 15
        (temp_project_dir / "tests").mkdir()  # Weight 15

        checker = ProjectHealthChecker(temp_project_dir)
        checks = checker.run_all_checks()
        score, max_score = checker.calculate_score(checks)

        assert score == 30  # 15 + 15
        assert max_score == 100

    # Grouping Tests

    def test_group_checks_by_category(self, complete_project):
        """Test grouping checks by category."""
        checker = ProjectHealthChecker(complete_project)
        checks = checker.run_all_checks()
        categories = checker.group_checks_by_category(checks)

        assert "Documentation" in categories
        assert "Version Control" in categories
        assert "Quality" in categories
        assert "Deployment" in categories
        assert "Configuration" in categories

        assert len(categories["Documentation"]) == 2
        assert len(categories["Version Control"]) == 2
        assert len(categories["Quality"]) == 3
        assert len(categories["Deployment"]) == 2
        assert len(categories["Configuration"]) == 1

    # Recommendations Tests

    def test_generate_recommendations_complete_project(self, complete_project):
        """Test recommendations for a complete project."""
        checker = ProjectHealthChecker(complete_project)
        checks = checker.run_all_checks()
        recommendations = checker.generate_recommendations(checks)

        # Complete project should have no recommendations
        assert len(recommendations) == 0

    def test_generate_recommendations_empty_project(self, temp_project_dir):
        """Test recommendations for an empty project."""
        checker = ProjectHealthChecker(temp_project_dir)
        checks = checker.run_all_checks()
        recommendations = checker.generate_recommendations(checks)

        # All 10 checks should generate recommendations
        assert len(recommendations) == 10
        # Git should be first priority
        assert "git init" in recommendations[0].lower()

    def test_generate_recommendations_prioritization(self, temp_project_dir):
        """Test that recommendations are prioritized correctly."""
        # Create a project missing only low-priority items
        (temp_project_dir / ".git").mkdir()
        (temp_project_dir / "README.md").write_text("# Test")
        (temp_project_dir / "tests").mkdir()
        (temp_project_dir / ".gitignore").write_text("*.pyc")

        checker = ProjectHealthChecker(temp_project_dir)
        checks = checker.run_all_checks()
        recommendations = checker.generate_recommendations(checks)

        # Should have 6 recommendations (missing pytest, ruff, gh actions, etc.)
        assert len(recommendations) == 6
        # Higher priority items should come first
        assert any("pytest" in rec.lower() for rec in recommendations[:3])

    def test_format_report_runs_without_error(self, complete_project, capsys):
        """Test that format_report executes without errors."""
        checker = ProjectHealthChecker(complete_project)
        checks = checker.run_all_checks()

        # Should not raise any exceptions
        checker.format_report(checks)

        # Verify some output was generated
        captured = capsys.readouterr()
        # Rich output goes to stdout
        assert len(captured.out) > 0 or len(captured.err) > 0


class TestRunHealthCheck:
    """Tests for the run_health_check function."""

    def test_run_health_check_default_path(self, capsys):
        """Test run_health_check with default path."""
        from spawn.utils.doctor import run_health_check

        # Should run without errors on current directory
        run_health_check()

        captured = capsys.readouterr()
        # Should produce output
        assert len(captured.out) > 0 or len(captured.err) > 0

    def test_run_health_check_custom_path(self, complete_project, capsys):
        """Test run_health_check with custom path."""
        from spawn.utils.doctor import run_health_check

        run_health_check(complete_project)

        captured = capsys.readouterr()
        # Should produce output
        assert len(captured.out) > 0 or len(captured.err) > 0
