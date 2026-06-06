"""Project health checker for Spawn CLI.

This module provides comprehensive project health analysis,
checking for best practices and common project standards.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Callable

from rich.panel import Panel
from rich.text import Text

from spawn.utils.console import console


@dataclass
class HealthCheck:
    """Represents a single health check result.

    Attributes:
        name: Display name of the check
        category: Category this check belongs to
        passed: Whether the check passed
        message: Descriptive message about the result
        weight: Weight for scoring (higher = more important)
    """

    name: str
    category: str
    passed: bool
    message: str
    weight: int = 10


class ProjectHealthChecker:
    """Analyzes project health and best practices compliance.

    This class performs various checks on a project directory to ensure
    it follows common best practices and has essential configurations.
    """

    def __init__(self, project_path: Path | None = None):
        """Initialize the health checker.

        Args:
            project_path: Path to the project directory. Defaults to current directory.
        """
        self.project_path = project_path or Path.cwd()

    # Documentation Checks

    def check_readme(self) -> HealthCheck:
        """Check if README.md exists."""
        readme_path = self.project_path / "README.md"
        passed = readme_path.exists() and readme_path.is_file()
        return HealthCheck(
            name="README.md",
            category="Documentation",
            passed=passed,
            message="Documentation file present" if passed else "Missing README.md",
            weight=10,
        )

    def check_license(self) -> HealthCheck:
        """Check if LICENSE exists."""
        license_path = self.project_path / "LICENSE"
        passed = license_path.exists() and license_path.is_file()
        return HealthCheck(
            name="LICENSE",
            category="Documentation",
            passed=passed,
            message="License file present" if passed else "Missing LICENSE file",
            weight=5,
        )

    # Version Control Checks

    def check_git_repository(self) -> HealthCheck:
        """Check if project is a git repository."""
        git_path = self.project_path / ".git"
        passed = git_path.exists() and git_path.is_dir()
        return HealthCheck(
            name="Git Repository",
            category="Version Control",
            passed=passed,
            message="Git initialized"
            if passed
            else "Not a git repository",
            weight=15,
        )

    def check_gitignore(self) -> HealthCheck:
        """Check if .gitignore exists."""
        gitignore_path = self.project_path / ".gitignore"
        passed = gitignore_path.exists() and gitignore_path.is_file()
        return HealthCheck(
            name=".gitignore",
            category="Version Control",
            passed=passed,
            message="Git ignore configured" if passed else "Missing .gitignore",
            weight=10,
        )

    # Quality Checks

    def check_tests_directory(self) -> HealthCheck:
        """Check if tests directory exists."""
        tests_path = self.project_path / "tests"
        passed = tests_path.exists() and tests_path.is_dir()
        return HealthCheck(
            name="Tests",
            category="Quality",
            passed=passed,
            message="Test directory configured"
            if passed
            else "Missing tests directory",
            weight=15,
        )

    def check_ruff_configured(self) -> HealthCheck:
        """Check if Ruff linter is configured.

        Checks for Ruff configuration in:
        - pyproject.toml ([tool.ruff] or ruff dependency)
        - ruff.toml
        - .ruff.toml
        """
        pyproject_path = self.project_path / "pyproject.toml"
        ruff_config_path = self.project_path / "ruff.toml"
        ruff_config_alt_path = self.project_path / ".ruff.toml"

        passed = False
        config_location = None

        if ruff_config_path.exists():
            passed = True
            config_location = "ruff.toml"
        elif ruff_config_alt_path.exists():
            passed = True
            config_location = ".ruff.toml"
        elif pyproject_path.exists():
            try:
                content = pyproject_path.read_text(encoding="utf-8")
                if "[tool.ruff]" in content:
                    passed = True
                    config_location = "pyproject.toml [tool.ruff]"
                elif "ruff>=" in content or '"ruff"' in content:
                    passed = True
                    config_location = "pyproject.toml (dependency)"
            except Exception:
                pass

        message = (
            f"Ruff configured in {config_location}"
            if passed
            else "Ruff not configured"
        )

        return HealthCheck(
            name="Ruff",
            category="Quality",
            passed=passed,
            message=message,
            weight=10,
        )

    def check_pytest_configured(self) -> HealthCheck:
        """Check if Pytest is configured.

        Checks for Pytest configuration in:
        - pyproject.toml ([tool.pytest] or pytest dependency)
        - pytest.ini
        - setup.cfg
        """
        pyproject_path = self.project_path / "pyproject.toml"
        pytest_ini_path = self.project_path / "pytest.ini"
        setup_cfg_path = self.project_path / "setup.cfg"

        passed = False
        config_location = None

        if pytest_ini_path.exists():
            passed = True
            config_location = "pytest.ini"
        elif setup_cfg_path.exists():
            try:
                content = setup_cfg_path.read_text(encoding="utf-8")
                if "[pytest]" in content or "[tool:pytest]" in content:
                    passed = True
                    config_location = "setup.cfg"
            except Exception:
                pass
        
        if not passed and pyproject_path.exists():
            try:
                content = pyproject_path.read_text(encoding="utf-8")
                if "[tool.pytest" in content:
                    passed = True
                    config_location = "pyproject.toml [tool.pytest]"
                elif "pytest>=" in content or '"pytest"' in content:
                    passed = True
                    config_location = "pyproject.toml (dependency)"
            except Exception:
                pass

        message = (
            f"Pytest configured in {config_location}"
            if passed
            else "Pytest not configured"
        )

        return HealthCheck(
            name="Pytest",
            category="Quality",
            passed=passed,
            message=message,
            weight=10,
        )

    # Deployment Checks

    def check_dockerfile(self) -> HealthCheck:
        """Check if Dockerfile exists."""
        dockerfile_path = self.project_path / "Dockerfile"
        passed = dockerfile_path.exists() and dockerfile_path.is_file()
        return HealthCheck(
            name="Dockerfile",
            category="Deployment",
            passed=passed,
            message="Docker configuration present"
            if passed
            else "Missing Dockerfile",
            weight=10,
        )

    def check_github_actions(self) -> HealthCheck:
        """Check if GitHub Actions workflow exists.

        Checks for workflow files (.yml or .yaml) in .github/workflows/
        """
        workflows_path = self.project_path / ".github" / "workflows"
        passed = False
        workflow_count = 0

        if workflows_path.exists() and workflows_path.is_dir():
            workflow_files = list(workflows_path.glob("*.yml")) + list(
                workflows_path.glob("*.yaml")
            )
            workflow_count = len(workflow_files)
            passed = workflow_count > 0

        message = (
            f"GitHub Actions configured ({workflow_count} workflow{'s' if workflow_count != 1 else ''})"
            if passed
            else "GitHub Actions not configured"
        )

        return HealthCheck(
            name="GitHub Actions",
            category="Deployment",
            passed=passed,
            message=message,
            weight=10,
        )

    # Configuration Checks

    def check_env_example(self) -> HealthCheck:
        """Check if .env.example exists."""
        env_example_path = self.project_path / ".env.example"
        passed = env_example_path.exists() and env_example_path.is_file()
        return HealthCheck(
            name=".env.example",
            category="Configuration",
            passed=passed,
            message="Environment template present"
            if passed
            else "Missing .env.example",
            weight=5,
        )

    def get_all_checks(self) -> List[Callable[[], HealthCheck]]:
        """Get all health check methods.

        Returns:
            List of health check methods to run
        """
        return [
            self.check_readme,
            self.check_license,
            self.check_git_repository,
            self.check_gitignore,
            self.check_tests_directory,
            self.check_ruff_configured,
            self.check_pytest_configured,
            self.check_dockerfile,
            self.check_github_actions,
            self.check_env_example,
        ]

    def run_all_checks(self) -> List[HealthCheck]:
        """Run all health checks and return results.

        Returns:
            List of HealthCheck results
        """
        return [check() for check in self.get_all_checks()]

    def calculate_score(self, checks: List[HealthCheck]) -> tuple[int, int]:
        """Calculate overall health score using weighted scoring.

        Args:
            checks: List of health check results

        Returns:
            Tuple of (score, max_score) where score is the weighted sum
        """
        if not checks:
            return 0, 0

        total_weight = sum(check.weight for check in checks)
        earned_weight = sum(check.weight for check in checks if check.passed)

        return earned_weight, total_weight

    def group_checks_by_category(
        self, checks: List[HealthCheck]
    ) -> dict[str, List[HealthCheck]]:
        """Group health checks by category.

        Args:
            checks: List of health check results

        Returns:
            Dictionary mapping category names to lists of checks
        """
        categories: dict[str, List[HealthCheck]] = {}
        for check in checks:
            if check.category not in categories:
                categories[check.category] = []
            categories[check.category].append(check)
        return categories

    def generate_recommendations(self, checks: List[HealthCheck]) -> List[str]:
        """Generate actionable recommendations for failed checks.

        Args:
            checks: List of health check results

        Returns:
            List of recommendation strings
        """
        recommendations = []
        failed_checks = [check for check in checks if not check.passed]

        # Priority order for recommendations
        priority_map = {
            "Git Repository": (
                "Initialize a git repository with 'git init'",
                1,
            ),
            "README.md": (
                "Add a README.md file to document your project",
                2,
            ),
            "Tests": (
                "Create a tests/ directory and add test files",
                3,
            ),
            ".gitignore": (
                "Add a .gitignore file to exclude unnecessary files from version control",
                4,
            ),
            "Pytest": (
                "Configure Pytest in pyproject.toml or create pytest.ini",
                5,
            ),
            "Ruff": (
                "Configure Ruff linter in pyproject.toml for code quality",
                6,
            ),
            "GitHub Actions": (
                "Set up GitHub Actions in .github/workflows/ for CI/CD",
                7,
            ),
            "Dockerfile": (
                "Add a Dockerfile for containerized deployment",
                8,
            ),
            "LICENSE": (
                "Add a LICENSE file to specify usage terms",
                9,
            ),
            ".env.example": (
                "Create a .env.example file to document required environment variables",
                10,
            ),
        }

        # Sort by priority and generate recommendations
        sorted_failed = sorted(
            failed_checks,
            key=lambda c: priority_map.get(c.name, (c.name, 999))[1],
        )

        for check in sorted_failed:
            rec = priority_map.get(check.name, (f"Address: {check.name}", 999))[0]
            recommendations.append(rec)

        return recommendations

    def format_report(self, checks: List[HealthCheck]) -> None:
        """Display formatted health check report using Rich.

        Args:
            checks: List of health check results
        """
        score, max_score = self.calculate_score(checks)
        score_percent = int((score / max_score * 100) if max_score > 0 else 0)
        categories = self.group_checks_by_category(checks)

        # Create main content
        content = Text()

        # Add category sections
        category_order = [
            "Documentation",
            "Version Control",
            "Quality",
            "Deployment",
            "Configuration",
        ]

        for category in category_order:
            if category not in categories:
                continue

            content.append(f"\n{category}\n", style="bold cyan")

            for check in categories[category]:
                if check.passed:
                    status = "✓"
                    style = "green"
                else:
                    status = "⚠"
                    style = "yellow"

                content.append(f"  {status} ", style=style)
                content.append(f"{check.name}", style=f"bold {style}")
                content.append(f" — {check.message}\n", style=style)

        # Add score
        content.append("\n")
        if score_percent >= 80:
            score_color = "green"
        elif score_percent >= 50:
            score_color = "yellow"
        else:
            score_color = "red"

        content.append("Project Score: ", style="bold")
        content.append(
            f"{score}/{max_score} ({score_percent}%)",
            style=f"bold {score_color}",
        )

        # Display main panel
        console.print()
        console.print(
            Panel(
                content,
                title="[bold cyan]🏥 Project Health Report[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

        # Display recommendations if any
        recommendations = self.generate_recommendations(checks)
        if recommendations:
            console.print()
            rec_content = Text()
            for i, rec in enumerate(recommendations, 1):
                rec_content.append(f"{i}. ", style="bold yellow")
                rec_content.append(f"{rec}\n", style="yellow")

            console.print(
                Panel(
                    rec_content,
                    title="[bold yellow]💡 Recommendations[/bold yellow]",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )

        console.print()


def run_health_check(project_path: Path | None = None) -> None:
    """Run project health check and display report.

    This is the main entry point for the doctor command.

    Args:
        project_path: Path to the project directory. Defaults to current directory.
    """
    checker = ProjectHealthChecker(project_path)
    checks = checker.run_all_checks()
    checker.format_report(checks)
