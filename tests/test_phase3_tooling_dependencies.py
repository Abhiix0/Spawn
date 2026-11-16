"""Comprehensive verification tests for Phase 3: Tooling and Dependencies.

Verifies:
1. ISSUE 8: Ruff version consistency across root pyproject.toml, CI workflows,
   root and template pre-commit configs, and generated template configs.
2. ISSUE 9: Development dependency placement across the entire template matrix,
   ensuring dev tools (pytest, ruff, mypy, pre-commit, and test helpers) are
   strictly isolated in development dependency groups and never leak into
   runtime dependencies.
"""

from pathlib import Path
import re
import tomllib

import pytest

from spawn.core.models import ProjectConfig
from spawn.core.planning import supported_providers
from spawn.core.registry import TEMPLATES, instantiate_template
from spawn.generators import project_generator
from spawn.generators.custom_structure import CustomStructureGenerator
from spawn.generators.project_files import declares_dependency
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.shared_content import (
    PRECOMMIT_CONFIG_CONTENT,
    RUFF_PRECOMMIT_REV,
    RUFF_VERSION,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
DEV_TOOL_NAMES = {"pytest", "ruff", "mypy", "pre-commit", "httpx", "pytest-django"}


# ===========================================================================
# ISSUE 8: RUFF VERSION CONSISTENCY
# ===========================================================================


def test_ruff_version_constant_and_rev_agreement():
    """RUFF_VERSION and RUFF_PRECOMMIT_REV must strictly agree."""
    assert RUFF_VERSION == "0.15.16"
    assert RUFF_PRECOMMIT_REV == f"v{RUFF_VERSION}"


def test_root_pyproject_ruff_dependency_and_config():
    """Root pyproject.toml dev group must pin ruff to the canonical version."""
    pyproject_path = ROOT_DIR / "pyproject.toml"
    assert pyproject_path.is_file()

    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    dev_group = data.get("dependency-groups", {}).get("dev", [])
    ruff_pin = next((d for d in dev_group if d.startswith("ruff")), None)
    assert ruff_pin is not None, "ruff must be in root dependency-groups.dev"
    assert f">={RUFF_VERSION}" in ruff_pin

    ruff_tool = data.get("tool", {}).get("ruff", {})
    assert ruff_tool.get("line-length") == 88


def _validate_precommit_text(text: str) -> None:
    assert "https://github.com/astral-sh/ruff-pre-commit" in text
    assert f"rev: {RUFF_PRECOMMIT_REV}" in text
    assert re.search(r"-\s*id:\s*ruff\b", text)
    assert re.search(r"-\s*id:\s*ruff-format\b", text)


def test_root_precommit_config_matches_canonical_ruff():
    """Root .pre-commit-config.yaml must match canonical Ruff version and hooks."""
    precommit_path = ROOT_DIR / ".pre-commit-config.yaml"
    if not precommit_path.is_file():
        pytest.skip(".pre-commit-config.yaml not present in extracted distribution")
    _validate_precommit_text(precommit_path.read_text(encoding="utf-8"))


def test_template_precommit_content_matches_canonical_ruff():
    """Generated PRECOMMIT_CONFIG_CONTENT must match canonical Ruff rev & hooks."""
    _validate_precommit_text(PRECOMMIT_CONFIG_CONTENT)


def test_root_ci_workflow_runs_ruff_check_and_format():
    """GitHub Actions CI workflow must enforce both ruff check and ruff format."""
    ci_path = ROOT_DIR / ".github" / "workflows" / "ci.yml"
    if not ci_path.is_file():
        pytest.skip("CI workflows not present in extracted distribution")
    ci_text = ci_path.read_text(encoding="utf-8")

    assert "uv run ruff check ." in ci_text
    assert "uv run ruff format --check ." in ci_text


def test_root_pr_check_workflow_runs_format_check():
    """PR Check workflow must run ruff format --check."""
    pr_path = ROOT_DIR / ".github" / "workflows" / "pr-check.yml"
    if not pr_path.is_file():
        pytest.skip("PR check workflow not present in extracted distribution")
    pr_text = pr_path.read_text(encoding="utf-8")

    assert "uv run ruff format --check ." in pr_text


# ===========================================================================
# ISSUE 9: DEVELOPMENT DEPENDENCY PLACEMENT ACROSS TEMPLATE MATRIX
# ===========================================================================


def _all_template_variants() -> list[tuple[str, dict[str, str]]]:
    cases: list[tuple[str, dict[str, str]]] = []
    for slug, meta in TEMPLATES.items():
        if slug == "backend-api":
            cases.extend((slug, {"framework": fw}) for fw in meta.available_frameworks)
        elif slug == "cli":
            cases.extend(
                (slug, {"framework": fw, "cli_type": ct})
                for fw in meta.available_frameworks
                for ct in meta.available_cli_types
            )
        elif slug in {"agent", "chatbot"}:
            cases.extend(
                (slug, {"framework": fw, "provider": pv})
                for fw in meta.available_frameworks
                for pv in supported_providers(slug, fw, meta.available_providers)
            )
        elif slug == "data":
            cases.extend((slug, {"data_type": dt}) for dt in meta.available_data_types)
        else:
            cases.append((slug, {}))
    return cases


@pytest.mark.parametrize("slug, options", _all_template_variants())
def test_all_templates_isolate_dev_dependencies_when_extras_selected(slug, options):
    """When testing/linting extras are selected, dev tools must only be in dev deps."""
    config = ProjectConfig(
        name="test-project",
        template=slug,
        use_git=False,
        extras=["ruff", "pytest", "mypy", "pre-commit"],
        **options,
    )
    template = instantiate_template(config)

    runtime_deps = template.get_dependencies()
    dev_deps = template.get_dev_dependencies()

    # Runtime dependencies must NOT contain any developer tool
    for dep in runtime_deps:
        dep_name = dep.split(">=")[0].split("==")[0].split("[")[0].strip()
        assert dep_name not in DEV_TOOL_NAMES, (
            f"Template {slug} leaked dev tool '{dep}' into runtime dependencies!"
        )

    # Developer dependencies MUST contain the selected dev tools
    assert any(d.startswith(f"ruff>={RUFF_VERSION}") for d in dev_deps)
    assert "pytest" in dev_deps
    assert "mypy" in dev_deps
    assert "pre-commit" in dev_deps

    if slug == "backend-api":
        if options.get("framework") == "django":
            assert "pytest-django" in dev_deps
            assert "pytest-django" not in runtime_deps
        else:
            assert "httpx" in dev_deps
            assert "httpx" not in runtime_deps


@pytest.mark.parametrize("slug, options", _all_template_variants())
def test_all_templates_no_extras_runtime_clean(slug, options):
    """With no extras, runtime dependencies only contain application libraries."""
    config = ProjectConfig(
        name="clean-project",
        template=slug,
        use_git=False,
        extras=[],
        **options,
    )
    template = instantiate_template(config)

    runtime_deps = template.get_dependencies()
    for dep in runtime_deps:
        dep_name = dep.split(">=")[0].split("==")[0].split("[")[0].strip()
        assert dep_name not in DEV_TOOL_NAMES, (
            f"Template {slug} without extras has dev tool '{dep}' in runtime deps!"
        )

    dev_deps = template.get_dev_dependencies()
    if slug == "cli":
        # CLI projects always ship pytest in dev group for out-of-the-box testing
        assert dev_deps == ["pytest"]
    else:
        assert dev_deps == []


def test_generator_installs_runtime_and_dev_dependencies_separately(
    tmp_path, monkeypatch
):
    """ProjectGenerator must pass runtime deps without dev=True and dev deps with dev=True."""
    installed_calls: list[tuple[list[str], bool]] = []

    def fake_install(project_path, packages, dev=False):
        installed_calls.append((list(packages), dev))

    def fake_init_uv(project_path):
        (project_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8"
        )

    monkeypatch.setattr(project_generator, "install_packages", fake_install)
    monkeypatch.setattr(project_generator, "initialize_uv", fake_init_uv)
    monkeypatch.chdir(tmp_path)

    config = ProjectConfig(
        name="demo",
        template="backend-api",
        use_git=False,
        framework="fastapi",
        extras=["ruff", "pytest", "mypy", "pre-commit"],
        use_uv=True,
        destination=tmp_path / "demo",
    )
    ProjectGenerator().generate(config)

    runtime_installs = [pkgs for pkgs, is_dev in installed_calls if not is_dev]
    dev_installs = [pkgs for pkgs, is_dev in installed_calls if is_dev]

    assert len(runtime_installs) == 1
    assert "fastapi" in runtime_installs[0]
    assert "uvicorn[standard]" in runtime_installs[0]
    for dev_tool in DEV_TOOL_NAMES:
        assert not any(p.startswith(dev_tool) for p in runtime_installs[0])

    assert len(dev_installs) == 1
    assert any(p.startswith(f"ruff>={RUFF_VERSION}") for p in dev_installs[0])
    assert "pytest" in dev_installs[0]
    assert "httpx" in dev_installs[0]
    assert "mypy" in dev_installs[0]
    assert "pre-commit" in dev_installs[0]


def test_custom_structure_generator_dev_dependencies(tmp_path, monkeypatch):
    """CustomStructureGenerator must install dev_setup packages with dev=True."""
    installed_calls: list[tuple[list[str], bool]] = []

    def fake_install(project_path, packages, dev=False):
        installed_calls.append((list(packages), dev))

    def fake_init_uv(project_path):
        (project_path / "pyproject.toml").write_text(
            '[project]\nname = "custom-demo"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )

    from spawn.generators import custom_structure

    monkeypatch.setattr(custom_structure, "install_packages", fake_install)
    monkeypatch.setattr(custom_structure, "initialize_uv", fake_init_uv)
    monkeypatch.chdir(tmp_path)

    generator = CustomStructureGenerator()
    generator.generate(
        project_name="custom-demo",
        entries=[],
        use_uv=True,
        dependencies=["requests>=2.0.0"],
        dev_setup=["ruff", "pytest", "mypy", "precommit"],
        destination=tmp_path / "custom-demo",
    )

    runtime_installs = [pkgs for pkgs, is_dev in installed_calls if not is_dev]
    dev_installs = [pkgs for pkgs, is_dev in installed_calls if is_dev]

    assert runtime_installs == [["requests>=2.0.0"]]
    assert len(dev_installs) == 1
    assert any(p.startswith(f"ruff>={RUFF_VERSION}") for p in dev_installs[0])
    assert "pytest" in dev_installs[0]
    assert "mypy" in dev_installs[0]
    assert "pre-commit" in dev_installs[0]


def test_declares_dependency_recognizes_dev_group_and_runtime(tmp_path):
    """declares_dependency correctly inspects dependencies and dependency-groups."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        f"""[project]
dependencies = ["fastapi>=0.115.0"]

[dependency-groups]
dev = ["ruff>={RUFF_VERSION}", "pytest>=9.0.3", "mypy>=1.14.0", "pre-commit>=4.0.0"]
""",
        encoding="utf-8",
    )

    assert declares_dependency(tmp_path, "fastapi") is True
    assert declares_dependency(tmp_path, "ruff") is True
    assert declares_dependency(tmp_path, "pytest") is True
    assert declares_dependency(tmp_path, "mypy") is True
    assert declares_dependency(tmp_path, "pre-commit") is True
    assert declares_dependency(tmp_path, "nonexistent") is False
