"""Contract-level tests for static language detection (#55)."""

from pathlib import Path

from spawn.inspection.discovery import discover_repository
from spawn.inspection.models import DetectionState, FindingCategory, InspectionTarget
from spawn.inspection.languages import LanguageDetector


def write(root: Path, rel: str, text: str = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(root: Path):
    target = InspectionTarget(root.resolve())
    return LanguageDetector().run(target, discover_repository(target))


def test_detects_multiple_languages_with_repository_relative_evidence(tmp_path):
    write(tmp_path, "src/main.py", "print('hello')")
    write(tmp_path, "web/app.tsx", "export default function App() {}")
    write(tmp_path, "service/main.go", "package main")
    result = run(tmp_path)
    assert result.status.value == "complete"
    by_subject = {f.subject: f for f in result.findings}
    assert set(by_subject) == {"python", "typescript", "go"}
    assert all(f.category is FindingCategory.LANGUAGE for f in result.findings)
    assert all(
        f.detection_state is DetectionState.DETECTED and f.evidence
        for f in result.findings
    )
    assert by_subject["typescript"].evidence[0].path == "web/app.tsx"


def test_manifest_only_language_detection(tmp_path):
    write(tmp_path, "go.mod", "module example.test/app\n")
    write(tmp_path, "pyproject.toml", "[project]\nname='demo'\nversion='1.0'\n")
    result = run(tmp_path)
    by_subject = {f.subject: f for f in result.findings}
    assert set(by_subject) == {"go", "python"}
    assert by_subject["go"].evidence[0].path == "go.mod"
    assert by_subject["python"].evidence[0].path == "pyproject.toml"


def test_no_supported_indicators_returns_no_positive_findings(tmp_path):
    write(tmp_path, "README.md", "A project named python and react")
    write(tmp_path, "mystery.data", "")
    assert run(tmp_path).findings == ()


def test_malformed_manifest_is_diagnostic_not_crash(tmp_path):
    write(tmp_path, "pyproject.toml", "[project\ninvalid")
    result = run(tmp_path)
    assert result.status.value == "partial"
    assert result.findings == ()
    assert result.diagnostics[0].code == "language.malformed_manifest"
    assert result.diagnostics[0].path == "pyproject.toml"


def test_c_headers_do_not_force_c_or_cpp_claim(tmp_path):
    write(tmp_path, "include/common.h", "/* shared C/C++ header */")
    result = run(tmp_path)
    assert result.findings == ()
