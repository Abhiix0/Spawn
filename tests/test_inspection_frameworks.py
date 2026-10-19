"""Contract-level tests for static framework detection (#55)."""
from pathlib import Path

from spawn.inspection.discovery import discover_repository
from spawn.inspection.models import DetectionState, FindingCategory, InspectionTarget
from spawn.inspection.frameworks import FrameworkDetector


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(root: Path):
    target = InspectionTarget(root.resolve())
    return FrameworkDetector().run(target, discover_repository(target))


def test_detects_framework_imports_and_multiple_frameworks(tmp_path):
    write(tmp_path, "api/main.py", "from fastapi import FastAPI\napp = FastAPI()\n")
    write(tmp_path, "web/app.tsx", "import React from 'react';\nexport default React;\n")
    result = run(tmp_path)
    by_subject = {f.subject: f for f in result.findings}
    assert set(by_subject) == {"fastapi", "react"}
    assert all(f.category is FindingCategory.FRAMEWORK for f in result.findings)
    assert all(f.detection_state is DetectionState.DETECTED for f in result.findings)
    assert by_subject["fastapi"].evidence[0].path == "api/main.py"


def test_dependency_only_is_inferred_with_explanation(tmp_path):
    write(tmp_path, "requirements.txt", "fastapi>=0.100\n")
    result = run(tmp_path)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.subject == "fastapi"
    assert finding.detection_state is DetectionState.INFERRED
    assert finding.detail
    assert finding.evidence[0].path == "requirements.txt"


def test_framework_name_in_directory_or_readme_is_not_evidence(tmp_path):
    write(tmp_path, "fastapi/README.md", "React, Django, FastAPI")
    write(tmp_path, "README.md", "This directory will use Next.js someday")
    assert run(tmp_path).findings == ()


def test_framework_specific_config_is_direct_evidence(tmp_path):
    write(tmp_path, "next.config.js", "module.exports = {}\n")
    result = run(tmp_path)
    assert result.findings[0].subject == "nextjs"
    assert result.findings[0].detection_state is DetectionState.DETECTED
    assert result.findings[0].evidence[0].path == "next.config.js"


def test_malformed_manifest_is_diagnostic_and_partial(tmp_path):
    write(tmp_path, "package.json", "{bad json")
    result = run(tmp_path)
    assert result.status.value == "partial"
    assert result.findings == ()
    assert result.diagnostics[0].code == "framework.malformed_manifest"


def test_unrecognized_dependency_is_not_reported_as_framework(tmp_path):
    write(tmp_path, "package.json", '{"dependencies": {"some-unknown-framework": "1.0"}}')
    assert run(tmp_path).findings == ()
