"""Offline Ruff regression coverage for every registered template variant."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import spawn.generators.project_generator as project_generator
from spawn.core.models import ProjectConfig
from spawn.core.planning import supported_providers
from spawn.core.registry import TEMPLATES


def _ruff_matrix() -> list[tuple[str, dict[str, str]]]:
    cases: list[tuple[str, dict[str, str]]] = []
    for slug, metadata in TEMPLATES.items():
        if slug == "backend-api":
            cases.extend(
                (slug, {"framework": value}) for value in metadata.available_frameworks
            )
        elif slug == "cli":
            cases.extend(
                (slug, {"framework": framework, "cli_type": cli_type})
                for framework in metadata.available_frameworks
                for cli_type in metadata.available_cli_types
            )
        elif slug in {"agent", "chatbot"}:
            cases.extend(
                (slug, {"framework": framework, "provider": provider})
                for framework in metadata.available_frameworks
                for provider in supported_providers(
                    slug, framework, metadata.available_providers
                )
            )
        elif slug == "data":
            cases.extend(
                (slug, {"data_type": value}) for value in metadata.available_data_types
            )
        else:
            cases.append((slug, {}))
    return cases


def test_all_ruff_variants_are_formatted_and_clean(tmp_path, monkeypatch):
    """Generate all 40 registry variants without network or dependency installs."""
    ruff = shutil.which("ruff") or str(Path(sys.executable).parent / "ruff.exe")
    if not Path(ruff).exists():
        pytest.fail("Ruff is required for the generated-project lint regression")

    def fake_initialize_uv(project_path: Path) -> None:
        (project_path / "pyproject.toml").write_text(
            '[project]\nname = "generated"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )

    monkeypatch.setattr(project_generator, "initialize_uv", fake_initialize_uv)
    monkeypatch.setattr(project_generator, "install_packages", lambda *a, **k: None)

    failures = []
    cases = _ruff_matrix()
    assert len(cases) == 40
    for index, (slug, options) in enumerate(cases):
        config = ProjectConfig(
            name=f"variant-{index}",
            template=slug,
            use_git=False,
            use_uv=True,
            extras=["ruff"],
            destination=tmp_path / f"variant-{index}",
            **options,
        )
        project_generator.ProjectGenerator().generate(config)
        check = subprocess.run(
            [ruff, "check", "."],
            cwd=config.destination,
            capture_output=True,
            text=True,
            check=False,
        )
        formatted = subprocess.run(
            [ruff, "format", "--check", "."],
            cwd=config.destination,
            capture_output=True,
            text=True,
            check=False,
        )
        if check.returncode or formatted.returncode:
            failures.append(
                f"{slug} {options}:\n{check.stdout}{check.stderr}"
                f"{formatted.stdout}{formatted.stderr}"
            )

    assert not failures, "\n\n".join(failures)
