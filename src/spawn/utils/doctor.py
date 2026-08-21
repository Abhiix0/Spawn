"""Project health checker for Spawn CLI.

This module provides comprehensive project health analysis,
checking for best practices and common project standards.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List

from rich.panel import Panel
from rich.text import Text

from spawn.utils.console import console
from spawn.utils.theme import BORDER_COLOR

# ---------------------------------------------------------------------------
# Tier sets for recommendations
# ---------------------------------------------------------------------------

_CRITICAL: set[str] = {"Git Repository", "Tests"}

_RECOMMENDED: set[str] = {
    "README.md",
    "AGENTS.md",
    ".gitignore",
    "LICENSE",
    "Ruff",
    "Pytest",
    "GitHub Actions",
    "pyproject.toml",
}

_OPTIONAL: set[str] = {
    "Dockerfile",
    ".env.example",
    "CHANGELOG.md",
    "Type Checking",
    "Pre-commit",
}

# Complete-sentence recommendation text keyed by check name
_REC_TEXT: dict[str, str] = {
    "Git Repository":   "Initialize a git repository with 'git init'.",
    "Tests":            "Create a tests/ directory and add test files.",
    "README.md":        "Add a README.md file to document your project.",
    "AGENTS.md":        "Add an AGENTS.md file so coding agents understand this project's conventions.",
    ".gitignore":       "Add a .gitignore file to exclude generated files from version control.",
    "LICENSE":          "Add a LICENSE file to specify usage terms for your project.",
    "Ruff":             "Configure Ruff in pyproject.toml for automated code quality checks.",
    "Pytest":           "Configure Pytest in pyproject.toml or create pytest.ini.",
    "GitHub Actions":   "Set up GitHub Actions in .github/workflows/ for automated CI/CD.",
    "pyproject.toml":   "Add a pyproject.toml to centralise project configuration.",
    "Dockerfile":       "Add a Dockerfile for reproducible, containerised deployment.",
    ".env.example":     "Create a .env.example file to document required environment variables.",
    "CHANGELOG.md":     "Add a CHANGELOG.md to document project history and releases.",
    "Type Checking":    "Configure a type checker (mypy or pyright) to catch type errors early.",
    "Pre-commit":       "Add a .pre-commit-config.yaml to enforce checks before every commit.",
}

# Estimated effort per check name
_EFFORT: dict[str, str] = {
    "Git Repository":   "30 seconds",
    "README.md":        "2 minutes",
    "AGENTS.md":        "1 minute",
    "LICENSE":          "1 minute",
    "CHANGELOG.md":     "2 minutes",
    ".gitignore":       "1 minute",
    "pyproject.toml":   "2 minutes",
    ".env.example":     "2 minutes",
    "Tests":            "10 minutes",
    "Pytest":           "5 minutes",
    "Ruff":             "5 minutes",
    "Type Checking":    "5 minutes",
    "Pre-commit":       "5 minutes",
    "GitHub Actions":   "10 minutes",
    "Dockerfile":       "15 minutes",
}


@dataclass
class HealthCheck:
    """Represents a single health check result."""

    name: str
    category: str
    passed: bool
    message: str
    weight: int = 10


class ProjectHealthChecker:
    """Analyzes project health and best-practices compliance."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()

    # ------------------------------------------------------------------
    # Documentation Checks
    # ------------------------------------------------------------------

    def check_readme(self) -> HealthCheck:
        p = self.project_path / "README.md"
        ok = p.exists() and p.is_file()
        return HealthCheck(
            name="README.md",
            category="Documentation",
            passed=ok,
            message="Documentation file present" if ok else "Missing README.md",
            weight=10,
        )

    def check_agents_md(self) -> HealthCheck:
        p = self.project_path / "AGENTS.md"
        ok = p.exists() and p.is_file()
        return HealthCheck(
            name="AGENTS.md",
            category="Documentation",
            passed=ok,
            message="Agent context file present" if ok else "Missing AGENTS.md",
            weight=5,
        )

    def check_license(self) -> HealthCheck:
        p = self.project_path / "LICENSE"
        ok = p.exists() and p.is_file()
        return HealthCheck(
            name="LICENSE",
            category="Documentation",
            passed=ok,
            message="License file present" if ok else "Missing LICENSE file",
            weight=5,
        )

    def check_changelog(self) -> HealthCheck:
        p = self.project_path / "CHANGELOG.md"
        ok = p.exists() and p.is_file()
        return HealthCheck(
            name="CHANGELOG.md",
            category="Documentation",
            passed=ok,
            message="Changelog present" if ok else "Missing CHANGELOG.md",
            weight=5,
        )

    # ------------------------------------------------------------------
    # Version Control Checks
    # ------------------------------------------------------------------

    def check_git_repository(self) -> HealthCheck:
        p = self.project_path / ".git"
        ok = p.exists() and p.is_dir()
        return HealthCheck(
            name="Git Repository",
            category="Version Control",
            passed=ok,
            message="Git initialized" if ok else "Not a git repository",
            weight=15,
        )

    def check_gitignore(self) -> HealthCheck:
        p = self.project_path / ".gitignore"
        ok = p.exists() and p.is_file()
        return HealthCheck(
            name=".gitignore",
            category="Version Control",
            passed=ok,
            message="Git ignore configured" if ok else "Missing .gitignore",
            weight=10,
        )

    # ------------------------------------------------------------------
    # Configuration Checks
    # ------------------------------------------------------------------

    def check_env_example(self) -> HealthCheck:
        p = self.project_path / ".env.example"
        ok = p.exists() and p.is_file()
        return HealthCheck(
            name=".env.example",
            category="Configuration",
            passed=ok,
            message="Environment template present" if ok else "Missing .env.example",
            weight=5,
        )

    def check_pyproject(self) -> HealthCheck:
        p = self.project_path / "pyproject.toml"
        ok = p.exists() and p.is_file()
        return HealthCheck(
            name="pyproject.toml",
            category="Configuration",
            passed=ok,
            message="Project configuration present" if ok else "Missing pyproject.toml",
            weight=10,
        )

    # ------------------------------------------------------------------
    # Testing Checks
    # ------------------------------------------------------------------

    def check_tests_directory(self) -> HealthCheck:
        p = self.project_path / "tests"
        ok = p.exists() and p.is_dir()
        return HealthCheck(
            name="Tests",
            category="Testing",
            passed=ok,
            message="Test directory configured" if ok else "Missing tests directory",
            weight=15,
        )

    def check_pytest_configured(self) -> HealthCheck:
        pyproject = self.project_path / "pyproject.toml"
        pytest_ini = self.project_path / "pytest.ini"
        setup_cfg = self.project_path / "setup.cfg"

        ok = False
        location = None

        if pytest_ini.exists():
            ok, location = True, "pytest.ini"
        elif setup_cfg.exists():
            try:
                content = setup_cfg.read_text(encoding="utf-8")
                if "[pytest]" in content or "[tool:pytest]" in content:
                    ok, location = True, "setup.cfg"
            except (OSError, ValueError):
                pass

        if not ok and pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8")
                if "[tool.pytest" in content:
                    ok, location = True, "pyproject.toml [tool.pytest]"
                elif "pytest>=" in content or '"pytest"' in content:
                    ok, location = True, "pyproject.toml (dependency)"
            except (OSError, ValueError):
                pass

        msg = f"Pytest configured in {location}" if ok else "Pytest not configured"
        return HealthCheck(name="Pytest", category="Testing", passed=ok, message=msg, weight=10)

    # ------------------------------------------------------------------
    # Automation Checks
    # ------------------------------------------------------------------

    def check_dockerfile(self) -> HealthCheck:
        p = self.project_path / "Dockerfile"
        ok = p.exists() and p.is_file()
        return HealthCheck(
            name="Dockerfile",
            category="Automation",
            passed=ok,
            message="Docker configuration present" if ok else "Missing Dockerfile",
            weight=10,
        )

    def check_github_actions(self) -> HealthCheck:
        workflows = self.project_path / ".github" / "workflows"
        count = 0
        if workflows.exists() and workflows.is_dir():
            count = len(list(workflows.glob("*.yml")) + list(workflows.glob("*.yaml")))

        ok = count > 0
        msg = (
            f"GitHub Actions configured ({count} workflow{'s' if count != 1 else ''})"
            if ok
            else "GitHub Actions not configured"
        )
        return HealthCheck(
            name="GitHub Actions",
            category="Automation",
            passed=ok,
            message=msg,
            weight=10,
        )

    # ------------------------------------------------------------------
    # Code Quality Checks
    # ------------------------------------------------------------------

    def check_ruff_configured(self) -> HealthCheck:
        pyproject = self.project_path / "pyproject.toml"
        ruff_toml = self.project_path / "ruff.toml"
        ruff_toml_alt = self.project_path / ".ruff.toml"

        ok = False
        location = None

        if ruff_toml.exists():
            ok, location = True, "ruff.toml"
        elif ruff_toml_alt.exists():
            ok, location = True, ".ruff.toml"
        elif pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8")
                if "[tool.ruff]" in content:
                    ok, location = True, "pyproject.toml [tool.ruff]"
                elif "ruff>=" in content or '"ruff"' in content:
                    ok, location = True, "pyproject.toml (dependency)"
            except (OSError, ValueError):
                pass

        msg = f"Ruff configured in {location}" if ok else "Ruff not configured"
        return HealthCheck(
            name="Ruff", category="Code Quality", passed=ok, message=msg, weight=10
        )

    def check_type_checker_configured(self) -> HealthCheck:
        """Check for mypy or pyright configuration."""
        pyproject = self.project_path / "pyproject.toml"
        mypy_ini = self.project_path / "mypy.ini"
        pyright_cfg = self.project_path / "pyrightconfig.json"

        ok = False
        location = None

        if mypy_ini.exists():
            ok, location = True, "mypy.ini"
        elif pyright_cfg.exists():
            ok, location = True, "pyrightconfig.json"
        elif pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8")
                if "[tool.mypy]" in content:
                    ok, location = True, "pyproject.toml [tool.mypy]"
                elif "[tool.pyright]" in content:
                    ok, location = True, "pyproject.toml [tool.pyright]"
            except (OSError, ValueError):
                pass

        msg = f"Type checking configured ({location})" if ok else "Type checking not configured"
        return HealthCheck(
            name="Type Checking",
            category="Code Quality",
            passed=ok,
            message=msg,
            weight=10,
        )

    def check_precommit_configured(self) -> HealthCheck:
        """Check for .pre-commit-config.yaml."""
        p = self.project_path / ".pre-commit-config.yaml"
        ok = p.exists() and p.is_file()
        return HealthCheck(
            name="Pre-commit",
            category="Code Quality",
            passed=ok,
            message="Pre-commit configured" if ok else "Pre-commit not configured",
            weight=5,
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def get_all_checks(self) -> List[Callable[[], HealthCheck]]:
        return [
            self.check_readme,
            self.check_agents_md,
            self.check_license,
            self.check_changelog,
            self.check_git_repository,
            self.check_gitignore,
            self.check_env_example,
            self.check_pyproject,
            self.check_tests_directory,
            self.check_pytest_configured,
            self.check_dockerfile,
            self.check_github_actions,
            self.check_ruff_configured,
            self.check_type_checker_configured,
            self.check_precommit_configured,
        ]

    def run_all_checks(self) -> List[HealthCheck]:
        return [check() for check in self.get_all_checks()]

    def calculate_score(self, checks: List[HealthCheck]) -> tuple[int, int]:
        if not checks:
            return 0, 0
        total = sum(c.weight for c in checks)
        earned = sum(c.weight for c in checks if c.passed)
        return earned, total

    def calculate_category_scores(
        self, checks: List[HealthCheck]
    ) -> dict[str, tuple[int, int]]:
        """Return {category: (earned_weight, total_weight)} per category."""
        cats = self.group_checks_by_category(checks)
        return {
            cat: (
                sum(c.weight for c in cs if c.passed),
                sum(c.weight for c in cs),
            )
            for cat, cs in cats.items()
        }

    def group_checks_by_category(
        self, checks: List[HealthCheck]
    ) -> dict[str, List[HealthCheck]]:
        result: dict[str, List[HealthCheck]] = {}
        for check in checks:
            result.setdefault(check.category, []).append(check)
        return result

    def get_health_rating(self, score_percent: int) -> tuple[str, str, str]:
        """Return (emoji, label, description) for a 0-100 score."""
        if score_percent >= 90:
            return ("🟢", "Excellent", "Project follows most recommended practices.")
        if score_percent >= 70:
            return ("🟡", "Good", "Some improvements recommended.")
        if score_percent >= 50:
            return ("🟠", "Fair", "Several recommended practices are missing.")
        return ("🔴", "Needs Attention", "Core project setup is incomplete.")

    def get_next_best_step(
        self, checks: List[HealthCheck]
    ) -> tuple[str, str] | None:
        """Return (recommendation, effort) for the single highest-priority failed check."""
        failed = [c for c in checks if not c.passed]
        if not failed:
            return None

        def _tier_key(c: HealthCheck) -> tuple[int, int]:
            if c.name in _CRITICAL:
                return (0, -c.weight)
            if c.name in _RECOMMENDED:
                return (1, -c.weight)
            return (2, -c.weight)

        top = min(failed, key=_tier_key)
        rec = _REC_TEXT.get(top.name, f"Address: {top.name}.")
        effort = _EFFORT.get(top.name, "a few minutes")
        return (rec, effort)

    def generate_recommendations(
        self, checks: List[HealthCheck]
    ) -> List[str]:
        """Return tiered recommendations for all failed checks.

        Returns a flat list ordered Critical → Recommended → Optional,
        with each item sorted by weight (descending) within its tier.
        Only failed checks are included.
        """
        failed = [c for c in checks if not c.passed]

        def _sort_key(c: HealthCheck) -> tuple[int, int]:
            if c.name in _CRITICAL:
                tier = 0
            elif c.name in _RECOMMENDED:
                tier = 1
            else:
                tier = 2
            return (tier, -c.weight)

        return [
            _REC_TEXT.get(c.name, f"Address: {c.name}.")
            for c in sorted(failed, key=_sort_key)
        ]

    def _tiered_recs(
        self, checks: List[HealthCheck]
    ) -> tuple[List[str], List[str], List[str]]:
        """Return (critical_recs, recommended_recs, optional_recs) — failed checks only."""
        failed = [c for c in checks if not c.passed]
        critical, recommended, optional = [], [], []
        for c in sorted(failed, key=lambda x: -x.weight):
            text = _REC_TEXT.get(c.name, f"Address: {c.name}.")
            if c.name in _CRITICAL:
                critical.append(text)
            elif c.name in _RECOMMENDED:
                recommended.append(text)
            else:
                optional.append(text)
        return critical, recommended, optional

    def format_report(self, checks: List[HealthCheck]) -> None:
        score, max_score = self.calculate_score(checks)
        score_percent = int((score / max_score * 100) if max_score > 0 else 0)
        emoji, label, description = self.get_health_rating(score_percent)
        categories = self.group_checks_by_category(checks)
        category_scores = self.calculate_category_scores(checks)

        content = Text()

        # Health rating
        content.append(f"{emoji} {label}\n", style="bold")
        content.append(f"{description}\n", style="dim")
        content.append("\n")

        # Score
        if score_percent >= 80:
            score_color = "green"
        elif score_percent >= 50:
            score_color = "yellow"
        else:
            score_color = "red"
        content.append("Project Score: ", style="bold")
        content.append(f"{score_percent}%  ({score}/{max_score})\n", style=f"bold {score_color}")

        category_order = [
            "Documentation",
            "Version Control",
            "Configuration",
            "Testing",
            "Automation",
            "Code Quality",
        ]

        for category in category_order:
            if category not in categories:
                continue
            cat_earned, cat_total = category_scores.get(category, (0, 0))
            cat_pct = int((cat_earned / cat_total * 100) if cat_total else 0)
            content.append(f"\n{category} — {cat_pct}%\n", style="bold cyan")

            for check in categories[category]:
                if check.passed:
                    status, style = "✓", "green"
                else:
                    status, style = "⚠", "yellow"
                content.append(f"  {status} ", style=style)
                content.append(check.name, style=f"bold {style}")
                content.append(f" — {check.message}\n", style=style)

        console.print()
        console.print(
            Panel(
                content,
                title="[bold cyan]🏥 Project Health Report[/bold cyan]",
                border_style=BORDER_COLOR,
                padding=(1, 2),
            )
        )

        # Tiered recommendations panel
        critical, recommended, optional = self._tiered_recs(checks)
        if critical or recommended or optional:
            rec_content = Text()
            if critical:
                rec_content.append("Critical\n", style="bold red")
                for r in critical:
                    rec_content.append(f"  • {r}\n", style="red")
            if recommended:
                if critical:
                    rec_content.append("\n")
                rec_content.append("Recommended\n", style="bold yellow")
                for r in recommended:
                    rec_content.append(f"  • {r}\n", style="yellow")
            if optional:
                if critical or recommended:
                    rec_content.append("\n")
                rec_content.append("Optional\n", style="bold dim")
                for r in optional:
                    rec_content.append(f"  • {r}\n", style="dim")

            console.print()
            console.print(
                Panel(
                    rec_content,
                    title="[bold yellow]💡 Recommendations[/bold yellow]",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )

        # Next Best Step panel
        nbs = self.get_next_best_step(checks)
        if nbs:
            rec_text, effort = nbs
            nbs_content = Text()
            nbs_content.append(f"{rec_text}\n\n", style="bold")
            nbs_content.append("Estimated effort: ", style="dim")
            nbs_content.append(effort, style="bold dim")
            console.print()
            console.print(
                Panel(
                    nbs_content,
                    title="[bold green]🎯 Next Best Step[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                )
            )

        console.print()


def run_health_check(project_path: Path | None = None) -> None:
    """CLI entry point for `spawn doctor`."""
    checker = ProjectHealthChecker(project_path)
    checks = checker.run_all_checks()
    checker.format_report(checks)
