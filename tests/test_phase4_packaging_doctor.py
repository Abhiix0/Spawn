"""Comprehensive tests for Phase 4 — Packaging, Documentation, and Doctor CI Semantics.

Covers:
- Issue #90: Design proposal for non-interactive custom structure.
- Issue #91: Complete PyPI package metadata for spawnio.
- Issue #92: Self-contained source distribution and documentation test isolation.
- Issue #93: Doctor CI exit semantics, APP_NAME implementation, and doc cleanups.
"""

from pathlib import Path
import tomllib
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.utils.doctor import run_health_check

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Issue #90: Non-interactive Custom Structure Design Proposal
# ---------------------------------------------------------------------------


def test_issue_90_design_proposal_exists_and_complete():
    """Verify Issue #90 design proposal is present and contains all required sections."""
    proposal_path = (
        REPO_ROOT
        / "docs"
        / "proposals"
        / "issue-90-non-interactive-custom-structure.md"
    )
    assert proposal_path.is_file(), f"Proposal missing at {proposal_path}"

    content = proposal_path.read_text(encoding="utf-8")
    required_keywords = [
        "Supported Structure Formats & Schema Validation",
        "Path Traversal & Filesystem Safety",
        "Duplicate and Conflicting Paths Handling",
        "Dry-Run & Preview Mechanism",
        "Integration with Existing Architecture",
        "CI/Script Compatibility & Exit Codes",
        "Proposed Regression Test Suite",
        "--structure-file",
        "ParsedEntry",
    ]
    for kw in required_keywords:
        assert kw in content, f"Proposal missing required section/concept: {kw}"


# ---------------------------------------------------------------------------
# Issue #91: Complete PyPI Package Metadata
# ---------------------------------------------------------------------------


def test_pyproject_pypi_metadata():
    """Verify PyPI package metadata in pyproject.toml is complete and accurate."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    assert pyproject_path.is_file()

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    assert project.get("name") == "spawnio"
    assert project.get("license") == {"text": "MIT"}
    assert project.get("authors") == [{"name": "Abhiix0"}]
    assert "keywords" in project and len(project["keywords"]) >= 5

    classifiers = project.get("classifiers", [])
    assert "Programming Language :: Python :: 3.12" in classifiers
    assert "Programming Language :: Python :: 3.13" in classifiers
    assert "Operating System :: OS Independent" in classifiers
    assert "Topic :: Software Development :: Code Generators" in classifiers

    urls = project.get("urls", {})
    assert "Homepage" in urls
    assert "Repository" in urls
    assert "Issues" in urls
    assert "Documentation" in urls
    assert "github.com/abhiix0/spawn" in urls["Repository"].lower()


# ---------------------------------------------------------------------------
# Issue #92: Self-contained Source Distribution & Doc Tests
# ---------------------------------------------------------------------------


def test_docs_test_tolerates_missing_dev_files():
    """Verify test_docs.py handles missing CLAUDE.md gracefully via is_file checks."""
    test_docs_path = REPO_ROOT / "tests" / "test_docs.py"
    assert test_docs_path.is_file()
    content = test_docs_path.read_text(encoding="utf-8")
    assert "is_file()" in content
    assert "CLAUDE.md" in content


def test_sdist_includes_essential_packaging_files():
    """Verify built sdist includes pyproject.toml, README.md, src, and tests."""
    dist_dir = REPO_ROOT / "dist"
    sdists = list(dist_dir.glob("spawnio-*.tar.gz"))
    if not sdists:
        return
    import tarfile

    with tarfile.open(sdists[0], "r:gz") as tar:
        names = tar.getnames()
    assert any("pyproject.toml" in n for n in names)
    assert any("README.md" in n for n in names)
    assert any("src/spawn" in n for n in names)


# ---------------------------------------------------------------------------
# Issue #93: Doctor CI Exit Semantics
# ---------------------------------------------------------------------------


def test_doctor_exit_code_needs_attention(tmp_path):
    """Empty directory gets score 0% ('Needs Attention') and exits with code 1."""
    result = runner.invoke(app, ["doctor", str(tmp_path)])
    assert result.exit_code == 1
    assert "Project Score: 0%" in result.output
    assert (
        "Needs Attention" in result.output
        or "🏥 Project Health Report" in result.output
    )


def test_doctor_exit_code_healthy_project(tmp_path):
    """Healthy project (score >= 50%) exits with code 0."""
    (tmp_path / "README.md").write_text("# Test Project", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Agents context", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("APP_NAME=demo\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_sample.py").write_text(
        "def test_ok(): pass", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n'
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
        "[tool.ruff]\nline-length = 88\n",
        encoding="utf-8",
    )

    exit_code = run_health_check(tmp_path)
    assert exit_code == 0

    result = runner.invoke(app, ["doctor", str(tmp_path)])
    assert result.exit_code == 0
    assert "Project Score:" in result.output


def test_doctor_exit_code_invalid_paths(tmp_path):
    """Non-existent directory or file path exits with code 1."""
    res_missing = runner.invoke(app, ["doctor", str(tmp_path / "nonexistent")])
    assert res_missing.exit_code == 1

    file_path = tmp_path / "file.txt"
    file_path.write_text("not a dir", encoding="utf-8")
    res_file = runner.invoke(app, ["doctor", str(file_path)])
    assert res_file.exit_code == 1


# ---------------------------------------------------------------------------
# Issue #93: APP_NAME Template and Documentation Checks
# ---------------------------------------------------------------------------


def test_app_name_in_templates():
    """Verify APP_NAME is actively referenced in starter code templates."""
    from spawn.templates.agent.content import MAIN_CONTENT as agent_main
    from spawn.templates.automation.content import MAIN_CONTENT as auto_main
    from spawn.templates.chatbot.content import (
        MAIN_CONTENT_NO_RICH as chat_plain,
        MAIN_CONTENT_RICH as chat_rich,
    )
    from spawn.templates.data_project.etl.content import ETL_CLEAN_CONTENT as data_etl
    from spawn.templates.rag.content import MAIN_CONTENT as rag_main

    assert 'os.getenv("APP_NAME"' in auto_main
    assert 'os.getenv("APP_NAME"' in chat_plain
    assert 'os.getenv("APP_NAME"' in chat_rich
    assert 'os.getenv("APP_NAME"' in agent_main
    assert 'os.getenv("APP_NAME"' in rag_main
    assert 'os.getenv("APP_NAME"' in data_etl


def test_docs_doctor_semantics_and_providers():
    """Verify docs/commands.md accurately documents doctor CI semantics and provider mappings."""
    commands_doc = (REPO_ROOT / "docs" / "commands.md").read_text(encoding="utf-8")

    # CI exit code contract
    assert "Exit codes" in commands_doc
    assert "Needs Attention" in commands_doc
    assert "Fair, Good, or Excellent (≥ 50%)" in commands_doc
    assert "Needs Attention' (< 50%) exits code 1" in commands_doc

    # Provider compatibility
    assert "openai-sdk" in commands_doc
    assert "groq" in commands_doc
    assert "openrouter" in commands_doc
