"""Contract-level tests for static language detection (#55)."""

from dataclasses import replace
from pathlib import Path

import pytest

from spawn.inspection.discovery import discover_repository
from spawn.inspection.languages import MAX_FILE_SIZE, LanguageDetector
from spawn.inspection.models import (
    AnalysisStatus,
    DetectionState,
    FindingCategory,
    InspectionTarget,
)


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


def _write_bytes(root: Path, rel: str, data: bytes) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_bytes(data)


def test_extension_lookup_is_case_insensitive(tmp_path):
    write(tmp_path, "A.PY", "x = 1")
    write(tmp_path, "App.Tsx", "")
    result = run(tmp_path)
    assert {f.subject for f in result.findings} == {"python", "typescript"}
    assert result.findings[0].evidence[0].indicator == ".py source-file extension"


def test_manifest_size_is_measured_in_bytes(tmp_path):
    pad = b" " * (MAX_FILE_SIZE - 2)
    _write_bytes(tmp_path, "ok/package.json", b"{}" + pad[: MAX_FILE_SIZE - 2])
    _write_bytes(tmp_path, "big/package.json", b"{}" + b" " * (MAX_FILE_SIZE - 1))
    _write_bytes(
        tmp_path, "wide/package.json", b'{"a":"' + "é".encode() * 600_000 + b'"}'
    )
    result = run(tmp_path)
    assert [(d.code, d.path) for d in result.diagnostics] == [
        ("language.manifest_too_large", "big/package.json"),
        ("language.manifest_too_large", "wide/package.json"),
    ]
    assert result.status.value == "partial"


def test_manifest_read_is_bounded(tmp_path, monkeypatch):
    _write_bytes(tmp_path, "package.json", b" " * (MAX_FILE_SIZE * 3))
    target = InspectionTarget(tmp_path.resolve())
    inventory = discover_repository(target)
    sizes = []
    real_open = Path.open

    def spy(self, *args, **kwargs):
        fh = real_open(self, *args, **kwargs)
        real_read = fh.read

        def read(n=-1):
            sizes.append(n)
            return real_read(n)

        fh.read = read
        return fh

    monkeypatch.setattr(Path, "open", spy)
    LanguageDetector().run(target, inventory)
    assert sizes == [MAX_FILE_SIZE + 1]


def test_bom_empty_and_non_utf8_manifests(tmp_path):
    _write_bytes(tmp_path, "a/package.json", b'\xef\xbb\xbf{"scripts": {}}')
    _write_bytes(tmp_path, "b/package.json", b"")
    _write_bytes(tmp_path, "c/package.json", "{}".encode("utf-16"))
    _write_bytes(tmp_path, "d/package.json", b"[1]")
    result = run(tmp_path)
    assert [f.subject for f in result.findings] == ["javascript"]
    assert [(d.code, d.path) for d in result.diagnostics] == [
        ("language.malformed_manifest", "b/package.json"),
        ("language.malformed_manifest", "c/package.json"),
    ]


@pytest.mark.parametrize("body", ["tool = 1\n", "[tool]\npoetry = 1\n"])
def test_non_table_tool_or_poetry_does_not_raise(tmp_path, body):
    write(tmp_path, "pyproject.toml", body)
    result = run(tmp_path)
    assert result.status.value == "complete"
    assert result.findings == ()


def test_empty_project_table_is_still_python_evidence(tmp_path):
    write(tmp_path, "pyproject.toml", "[project]\n")
    assert [f.subject for f in run(tmp_path).findings] == ["python"]


def test_unexpected_exception_yields_failed_result(tmp_path, monkeypatch):
    write(tmp_path, "main.go", "package main")
    write(tmp_path, "package.json", "{}")
    target = InspectionTarget(tmp_path.resolve())
    inventory = discover_repository(target)

    def boom(*args, **kwargs):
        raise RuntimeError(str(tmp_path))

    monkeypatch.setattr("spawn.inspection.languages.read_text_bounded", boom)
    result = LanguageDetector().run(target, inventory)
    assert result.status is AnalysisStatus.FAILED
    assert [f.subject for f in result.findings] == ["go"]
    assert result.diagnostics[-1].code == "language.internal_error"
    assert result.diagnostics[-1].fatal
    assert str(tmp_path) not in result.diagnostics[-1].message


def test_diagnostics_do_not_leak_paths(tmp_path, monkeypatch):
    write(tmp_path, "package.json", "{}")
    target = InspectionTarget(tmp_path.resolve())
    inventory = discover_repository(target)

    def deny(self, *args, **kwargs):
        raise OSError(f"cannot open {tmp_path}")

    monkeypatch.setattr(Path, "open", deny)
    diagnostic = LanguageDetector().run(target, inventory).diagnostics[0]
    assert diagnostic.code == "language.malformed_manifest"
    assert str(tmp_path) not in diagnostic.message
    assert "OSError" in diagnostic.message


def test_malformed_toml_message_has_no_raw_exception_text(tmp_path):
    write(tmp_path, "pyproject.toml", "[project\ninvalid")
    message = run(tmp_path).diagnostics[0].message
    assert message == "Could not parse manifest (TOMLDecodeError)."


def test_monorepo_nested_manifests_and_sorted_evidence(tmp_path):
    write(tmp_path, "services/api/pyproject.toml", "[project]\nname='api'\n")
    write(tmp_path, "services/api/app.py", "")
    write(tmp_path, "services/web/package.json", '{"dependencies": {}}')
    write(tmp_path, "services/gateway/go.mod", "module x\n")
    write(tmp_path, "libs/core/src/lib.rs", "")
    result = run(tmp_path)
    assert [f.subject for f in result.findings] == [
        "go",
        "javascript",
        "python",
        "rust",
    ]
    python = next(f for f in result.findings if f.subject == "python")
    assert [e.path for e in python.evidence] == [
        "services/api/app.py",
        "services/api/pyproject.toml",
    ]


def test_deterministic_across_runs_and_inventory_order(tmp_path):
    write(tmp_path, "b/main.go", "")
    write(tmp_path, "a/app.py", "")
    write(tmp_path, "c/package.json", '{"type": "module"}')
    target = InspectionTarget(tmp_path.resolve())
    inventory = discover_repository(target)
    first = LanguageDetector().run(target, inventory)
    assert LanguageDetector().run(target, inventory) == first
    flipped = replace(inventory, files=tuple(reversed(inventory.files)))
    assert LanguageDetector().run(target, flipped) == first
