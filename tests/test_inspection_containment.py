"""Read-time containment checks against real repository link replacement."""

import os
import sys

import pytest

from spawn.inspection import onboarding, orchestrator
from spawn.inspection.discovery import discover_repository, validate_inspection_root
from spawn.inspection.exceptions import InspectionError


@pytest.mark.skipif(sys.platform != "linux", reason="Linux descriptor regression")
@pytest.mark.parametrize("mode", ["stable", "file-swap", "directory-swap"])
@pytest.mark.parametrize("runner", [orchestrator, onboarding])
def test_external_links_cannot_influence_analysis(tmp_path, monkeypatch, mode, runner):
    root = tmp_path / "repo"
    external = tmp_path / "untrusted"
    root.mkdir()
    external.mkdir()
    files = {
        "app.py": "import flask\nfrom flask import Flask\napp = Flask(__name__)\n",
        "pyproject.toml": '[project]\ndependencies = ["flask"]\n[tool.ruff]\n',
        "requirements.txt": "flask\n",
        "package.json": '{"dependencies":{"react":"1"}}',
        "pytest.ini": "[pytest]\n",
        ".spawn/meta.json": '{"framework":"external-canary"}',
    }
    external_files = external / "nested" if mode == "directory-swap" else external
    repo_files = root / "nested" if mode == "directory-swap" else root
    # Metadata is read only at the root.
    if mode == "directory-swap":
        files.pop(".spawn/meta.json")
    for relative, content in files.items():
        source, target = external_files / relative, repo_files / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(content, encoding="utf-8")
        if mode == "stable":
            target.symlink_to(source)
        else:
            target.write_text("", encoding="utf-8")
    safe = root / "safe.py"
    safe.write_text("import fastapi\n", encoding="utf-8")

    discover = runner.discover_repository

    def replace_after_discovery(target):
        inventory = discover(target)
        if mode == "file-swap":
            for relative in files:
                path = repo_files / relative
                path.unlink()
                path.symlink_to(external_files / relative)
        elif mode == "directory-swap":
            repo_files.rename(tmp_path / "moved")
            repo_files.symlink_to(external_files, target_is_directory=True)
        return inventory

    monkeypatch.setattr(runner, "discover_repository", replace_after_discovery)
    if runner is onboarding:
        result = runner.inspect_python_onboarding(root)
        report = result.inspection
        assert not result.entry_points.entries
    else:
        report = runner.run_inspection(root)
    detected = {f.subject for f in report.findings if f.evidence}
    assert "fastapi" in detected
    # Basename-only tooling evidence is independent of file contents.
    assert not detected.intersection({"flask", "react", "ruff"})
    assert report.recorded_metadata is None
    if mode != "stable":
        assert any(
            d.code == "framework.unreadable_file"
            for item in report.analyzer_results
            for d in item.diagnostics
        )
    assert safe.read_bytes() == b"import fastapi\n"


@pytest.mark.skipif(sys.platform != "linux", reason="Linux descriptor regression")
def test_approved_root_is_not_resolved_again_after_link_replacement(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (external / "app.py").write_text("import flask\n")
    target = validate_inspection_root(root)
    root.rename(tmp_path / "moved")
    root.symlink_to(external, target_is_directory=True)
    with pytest.raises(InspectionError):
        discover_repository(target)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction regression")
def test_junction_substitution_cannot_influence_analysis(tmp_path, monkeypatch):
    import subprocess

    root, outside = tmp_path / "repo", tmp_path / "outside"
    child = root / "nested"
    child.mkdir(parents=True)
    outside.mkdir()
    (child / "app.py").write_text("pass\n")
    (outside / "app.py").write_text("import flask\n")
    discover = orchestrator.discover_repository

    def replace_after_discovery(target):
        inventory = discover(target)
        child.rename(tmp_path / "moved")
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(child), str(outside)],
            capture_output=True,
            check=False,
        )
        if result.returncode or not child.is_junction():
            pytest.skip("Creating Windows junctions is unavailable")
        return inventory

    monkeypatch.setattr(orchestrator, "discover_repository", replace_after_discovery)
    report = orchestrator.run_inspection(root)
    assert not any(f.subject == "flask" for f in report.findings)
    assert any(
        d.code == "framework.unreadable_file"
        for result in report.analyzer_results
        for d in result.diagnostics
    )
