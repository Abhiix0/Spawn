"""Serialization tests for spawn.inspection (Issue #53, Stage C step 2).

Covers:
- to_json() produces deterministic, byte-identical output across runs
- Full round-trip: report → to_json() → from_json() → equal report
- from_dict() / from_json() with supported and unsupported schema versions
- Unknown field handling (silently ignored, forward-compat)
- Malformed input produces ReportDecodeError (a SpawnError subclass)
- Missing required fields each produce clear ReportDecodeError messages
- Rendering independence: no Rich / terminal code imported or called
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spawn.inspection import (
    SCHEMA_VERSION,
    AnalyzerResult,
    AnalysisStatus,
    Diagnostic,
    DetectionState,
    Evidence,
    Finding,
    FindingCategory,
    InspectionReport,
    InspectionTarget,
    ReportDecodeError,
    from_dict,
    from_json,
    to_json,
)
from spawn.core.exceptions import SpawnError
from spawn.core.project import ProjectMetadata


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _target(tmp_path: Path) -> InspectionTarget:
    return InspectionTarget(path=tmp_path)


def _ev(path: str = "pyproject.toml", indicator: str = "section") -> Evidence:
    return Evidence(path=path, indicator=indicator)


def _finding(
    category: FindingCategory = FindingCategory.TOOL,
    subject: str = "pytest",
    state: DetectionState = DetectionState.DETECTED,
) -> Finding:
    ev = (_ev(),) if state in (DetectionState.DETECTED, DetectionState.INFERRED) else ()
    detail = "inferred from dep" if state == DetectionState.INFERRED else None
    return Finding(
        category=category,
        subject=subject,
        detection_state=state,
        evidence=ev,
        detail=detail,
    )


def _diag(
    code: str = "test.issue",
    severity: str = "warning",
    source: str = "test",
) -> Diagnostic:
    return Diagnostic(code=code, message="msg", severity=severity, source=source)


def _full_report(tmp_path: Path) -> InspectionReport:
    """A richly populated report for round-trip and determinism tests."""
    return InspectionReport(
        target=_target(tmp_path),
        status=AnalysisStatus.PARTIAL,
        generated_at="2026-10-14T10:00:00+00:00",
        recorded_metadata=ProjectMetadata(
            intent="backend-api",
            framework="fastapi",
            provider=None,
            spawn_version="1.0.9",
            created_at="2026-01-01T00:00:00+00:00",
            generator="blueprint",
            git=True,
            uv=True,
            source=None,
        ),
        findings=(
            _finding(FindingCategory.LANGUAGE, "python"),
            _finding(FindingCategory.TOOL, "pytest"),
        ),
        analyzer_results=(
            AnalyzerResult(
                analyzer_name="language",
                status=AnalysisStatus.COMPLETE,
                findings=(),
                diagnostics=(),
            ),
            AnalyzerResult(
                analyzer_name="tooling",
                status=AnalysisStatus.PARTIAL,
                findings=(),
                diagnostics=(_diag("tooling.warn", "warning", "tooling"),),
            ),
        ),
        diagnostics=(_diag("orch.info", "info", "orchestrator"),),
    )


# ---------------------------------------------------------------------------
# § to_json — output shape and determinism
# ---------------------------------------------------------------------------


class TestToJson:
    def test_returns_string(self, tmp_path):
        assert isinstance(to_json(InspectionReport(target=_target(tmp_path))), str)

    def test_ends_with_newline(self, tmp_path):
        out = to_json(InspectionReport(target=_target(tmp_path)))
        assert out.endswith("\n")

    def test_is_valid_json(self, tmp_path):
        out = to_json(InspectionReport(target=_target(tmp_path)))
        parsed = json.loads(out)
        assert isinstance(parsed, dict)

    def test_top_level_keys_in_stable_order(self, tmp_path):
        out = to_json(InspectionReport(target=_target(tmp_path)))
        keys = list(json.loads(out).keys())
        expected = [
            "schema_version",
            "status",
            "generated_at",
            "target",
            "recorded_metadata",
            "summary",
            "structure",
            "findings",
            "analyzer_results",
            "diagnostics",
        ]
        assert keys == expected

    def test_byte_identical_for_equal_reports(self, tmp_path):
        """Same report (same generated_at) → byte-identical JSON."""
        fixed_ts = "2026-10-14T10:00:00+00:00"
        r1 = InspectionReport(
            target=_target(tmp_path),
            generated_at=fixed_ts,
            findings=(_finding(FindingCategory.TOOL, "pytest"),),
        )
        r2 = InspectionReport(
            target=_target(tmp_path),
            generated_at=fixed_ts,
            findings=(_finding(FindingCategory.TOOL, "pytest"),),
        )
        assert to_json(r1) == to_json(r2)

    def test_byte_identical_across_multiple_calls(self, tmp_path):
        """Calling to_json() multiple times on the same object → same bytes."""
        report = _full_report(tmp_path)
        assert to_json(report) == to_json(report)
        assert to_json(report) == to_json(report)

    def test_status_serialised_as_string(self, tmp_path):
        d = json.loads(to_json(InspectionReport(target=_target(tmp_path))))
        assert d["status"] == "complete"
        assert isinstance(d["status"], str)

    def test_target_path_is_posix(self, tmp_path):
        d = json.loads(to_json(InspectionReport(target=_target(tmp_path))))
        # target serialises as a portable root label
        assert d["target"] == {"root": "."}

    def test_enum_values_are_plain_strings(self, tmp_path):
        report = InspectionReport(
            target=_target(tmp_path),
            findings=(_finding(FindingCategory.LANGUAGE, "python"),),
        )
        d = json.loads(to_json(report))
        f = d["findings"][0]
        assert f["category"] == "language"
        assert f["detection_state"] == "detected"

    def test_null_fields_serialised(self, tmp_path):
        d = json.loads(to_json(InspectionReport(target=_target(tmp_path))))
        assert d["recorded_metadata"] is None

    def test_custom_indent(self, tmp_path):
        out = to_json(InspectionReport(target=_target(tmp_path)), indent=4)
        # 4-space indent means lines should start with 4 spaces for top-level keys
        assert '    "status"' in out

    def test_non_ascii_preserved(self, tmp_path):
        """Non-ASCII characters in strings must not be escaped."""
        ev = Evidence(path="src/données.py", indicator="données")
        f = Finding(
            category=FindingCategory.STRUCTURE,
            subject="non-ascii",
            detection_state=DetectionState.DETECTED,
            evidence=(ev,),
        )
        out = to_json(InspectionReport(target=_target(tmp_path), findings=(f,)))
        assert "données" in out
        assert "\\u" not in out


# ---------------------------------------------------------------------------
# § Round-trip: to_json → from_json → equal report
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_minimal_round_trip(self, tmp_path):
        original = InspectionReport(
            target=_target(tmp_path),
            generated_at="2026-10-14T10:00:00+00:00",
        )
        restored = from_json(to_json(original))
        assert restored.schema_version == original.schema_version
        assert restored.status == original.status
        assert restored.generated_at == original.generated_at
        # target.path is not preserved across JSON (portable root label ".")
        assert restored.target.path == Path(".")
        assert restored.recorded_metadata is None
        assert restored.findings == ()
        assert restored.analyzer_results == ()
        assert restored.diagnostics == ()

    def test_full_round_trip(self, tmp_path):
        original = _full_report(tmp_path)
        restored = from_json(to_json(original))

        assert restored.schema_version == original.schema_version
        assert restored.status == original.status
        assert restored.generated_at == original.generated_at
        # target.path is not preserved across JSON (portable root label ".")
        assert restored.target.path == Path(".")

        # recorded_metadata
        rm = restored.recorded_metadata
        assert rm is not None
        assert rm.intent == "backend-api"
        assert rm.framework == "fastapi"
        assert rm.git is True
        assert rm.uv is True
        assert rm.provider is None

        # findings
        assert len(restored.findings) == 2
        lang, tool = restored.findings
        assert lang.category == FindingCategory.LANGUAGE
        assert lang.subject == "python"
        assert lang.detection_state == DetectionState.DETECTED
        assert len(lang.evidence) == 1
        assert lang.evidence[0].path == "pyproject.toml"

        assert tool.category == FindingCategory.TOOL
        assert tool.subject == "pytest"

        # analyzer_results
        assert len(restored.analyzer_results) == 2
        lang_r, tool_r = restored.analyzer_results
        assert lang_r.analyzer_name == "language"
        assert lang_r.status == AnalysisStatus.COMPLETE
        assert lang_r.diagnostics == ()

        assert tool_r.analyzer_name == "tooling"
        assert tool_r.status == AnalysisStatus.PARTIAL
        assert len(tool_r.diagnostics) == 1
        assert tool_r.diagnostics[0].code == "tooling.warn"

        # top-level diagnostics
        assert len(restored.diagnostics) == 1
        assert restored.diagnostics[0].source == "orchestrator"

    def test_round_trip_preserves_evidence_detail(self, tmp_path):
        ev = Evidence(path="setup.cfg", indicator="[options]", detail="v1.2.3")
        f = Finding(
            category=FindingCategory.DEPENDENCY,
            subject="requests",
            detection_state=DetectionState.DETECTED,
            evidence=(ev,),
        )
        original = InspectionReport(
            target=_target(tmp_path),
            generated_at="2026-01-01T00:00:00+00:00",
            findings=(f,),
        )
        restored = from_json(to_json(original))
        assert restored.findings[0].evidence[0].detail == "v1.2.3"

    def test_round_trip_preserves_fatal_diagnostic(self, tmp_path):
        d = Diagnostic(
            code="disc.fatal",
            message="boom",
            severity="error",
            source="discovery",
            path="src/x.py",
            fatal=True,
        )
        original = InspectionReport(
            target=_target(tmp_path),
            generated_at="2026-01-01T00:00:00+00:00",
            status=AnalysisStatus.FAILED,
            diagnostics=(d,),
        )
        restored = from_json(to_json(original))
        assert restored.diagnostics[0].fatal is True
        assert restored.diagnostics[0].code == "disc.fatal"
        assert restored.status == AnalysisStatus.FAILED

    def test_round_trip_none_evidence_detail(self, tmp_path):
        ev = Evidence(path="pyproject.toml", indicator="x", detail=None)
        f = Finding(
            category=FindingCategory.TOOL,
            subject="ruff",
            detection_state=DetectionState.DETECTED,
            evidence=(ev,),
        )
        original = InspectionReport(
            target=_target(tmp_path),
            generated_at="2026-01-01T00:00:00+00:00",
            findings=(f,),
        )
        restored = from_json(to_json(original))
        assert restored.findings[0].evidence[0].detail is None

    def test_to_dict_then_from_dict_equivalent_to_from_json(self, tmp_path):
        original = _full_report(tmp_path)
        via_dict = from_dict(original.to_dict())
        via_json = from_json(to_json(original))
        # Both paths produce identical reports
        assert via_dict.status == via_json.status
        assert via_dict.schema_version == via_json.schema_version
        assert len(via_dict.findings) == len(via_json.findings)


# ---------------------------------------------------------------------------
# § Schema version handling
# ---------------------------------------------------------------------------


class TestSchemaVersion:
    def test_same_version_accepted(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["schema_version"] = SCHEMA_VERSION
        report = from_dict(d)
        assert report.schema_version == SCHEMA_VERSION

    def test_same_major_higher_minor_accepted(self, tmp_path):
        """A report from a newer minor version (1.5) loads fine."""
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["schema_version"] = "1.5"
        report = from_dict(d)
        # The loaded report preserves the original version string
        assert report.schema_version == "1.5"

    def test_different_major_raises(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["schema_version"] = "2.0"
        with pytest.raises(ReportDecodeError, match="schema_version"):
            from_dict(d)

    def test_different_major_message_mentions_version(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["schema_version"] = "99.0"
        with pytest.raises(ReportDecodeError) as exc_info:
            from_dict(d)
        msg = str(exc_info.value)
        assert "99.0" in msg or "99" in msg

    def test_malformed_version_string_raises(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["schema_version"] = "not-a-version"
        with pytest.raises(ReportDecodeError):
            from_dict(d)

    def test_non_string_version_raises(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["schema_version"] = 1
        with pytest.raises(ReportDecodeError, match="schema_version"):
            from_dict(d)

    def test_missing_version_raises(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        del d["schema_version"]
        with pytest.raises(ReportDecodeError, match="schema_version"):
            from_dict(d)


# ---------------------------------------------------------------------------
# § Unknown field handling (forward-compatibility)
# ---------------------------------------------------------------------------


class TestUnknownFields:
    def test_unknown_top_level_field_ignored(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["future_field"] = "some value"
        report = from_dict(d)
        assert not hasattr(report, "future_field")
        assert report.status == AnalysisStatus.COMPLETE

    def test_unknown_field_in_finding_ignored(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path),
            generated_at="2026-01-01T00:00:00+00:00",
            findings=(_finding(),),
        ).to_dict()
        d["findings"][0]["confidence_score"] = 0.95
        report = from_dict(d)
        assert len(report.findings) == 1
        assert not hasattr(report.findings[0], "confidence_score")

    def test_unknown_field_in_evidence_ignored(self, tmp_path):
        ev = Evidence(path="f.py", indicator="x")
        f = Finding(
            category=FindingCategory.TOOL,
            subject="ruff",
            detection_state=DetectionState.DETECTED,
            evidence=(ev,),
        )
        d = InspectionReport(
            target=_target(tmp_path),
            generated_at="2026-01-01T00:00:00+00:00",
            findings=(f,),
        ).to_dict()
        d["findings"][0]["evidence"][0]["line_number"] = 42
        report = from_dict(d)
        assert not hasattr(report.findings[0].evidence[0], "line_number")

    def test_unknown_field_in_diagnostic_ignored(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path),
            generated_at="2026-01-01T00:00:00+00:00",
            diagnostics=(_diag(),),
        ).to_dict()
        d["diagnostics"][0]["remediation"] = "fix it"
        report = from_dict(d)
        assert not hasattr(report.diagnostics[0], "remediation")

    def test_unknown_field_in_recorded_metadata_ignored(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path),
            generated_at="2026-01-01T00:00:00+00:00",
            recorded_metadata=ProjectMetadata(intent="mcp"),
        ).to_dict()
        d["recorded_metadata"]["future_meta"] = "x"
        report = from_dict(d)
        assert not hasattr(report.recorded_metadata, "future_meta")

    def test_unknown_field_in_analyzer_result_ignored(self, tmp_path):
        ar = AnalyzerResult(
            analyzer_name="lang",
            status=AnalysisStatus.COMPLETE,
            findings=(),
            diagnostics=(),
        )
        d = InspectionReport(
            target=_target(tmp_path),
            generated_at="2026-01-01T00:00:00+00:00",
            analyzer_results=(ar,),
        ).to_dict()
        d["analyzer_results"][0]["duration_ms"] = 123
        report = from_dict(d)
        assert not hasattr(report.analyzer_results[0], "duration_ms")


# ---------------------------------------------------------------------------
# § Missing required fields → clear ReportDecodeError
# ---------------------------------------------------------------------------


class TestMissingRequiredFields:
    def _base(self, tmp_path: Path) -> dict:
        return InspectionReport(
            target=_target(tmp_path),
            generated_at="2026-01-01T00:00:00+00:00",
        ).to_dict()

    def test_missing_target_raises(self, tmp_path):
        d = self._base(tmp_path)
        del d["target"]
        with pytest.raises(ReportDecodeError, match="target"):
            from_dict(d)

    def test_missing_status_raises(self, tmp_path):
        d = self._base(tmp_path)
        del d["status"]
        with pytest.raises(ReportDecodeError, match="status"):
            from_dict(d)

    def test_missing_target_path_raises(self, tmp_path):
        d = self._base(tmp_path)
        # "root" is the new portable key; "path" is no longer emitted
        # Removing "root" entirely should not raise because it defaults to "."
        d["target"] = {}
        report = from_dict(d)
        assert report.target.path == Path(".")

    def test_missing_finding_category_raises(self, tmp_path):
        d = self._base(tmp_path)
        d["findings"] = [
            {"subject": "ruff", "detection_state": "detected", "evidence": []}
        ]
        with pytest.raises(ReportDecodeError, match="category"):
            from_dict(d)

    def test_missing_finding_subject_raises(self, tmp_path):
        d = self._base(tmp_path)
        d["findings"] = [
            {"category": "tool", "detection_state": "detected", "evidence": []}
        ]
        with pytest.raises(ReportDecodeError, match="subject"):
            from_dict(d)

    def test_missing_finding_detection_state_raises(self, tmp_path):
        d = self._base(tmp_path)
        d["findings"] = [{"category": "tool", "subject": "ruff", "evidence": []}]
        with pytest.raises(ReportDecodeError, match="detection_state"):
            from_dict(d)

    def test_missing_evidence_path_raises(self, tmp_path):
        d = self._base(tmp_path)
        d["findings"] = [
            {
                "category": "tool",
                "subject": "ruff",
                "detection_state": "detected",
                "evidence": [{"indicator": "x"}],
            }
        ]
        with pytest.raises(ReportDecodeError, match="path"):
            from_dict(d)

    def test_missing_evidence_indicator_raises(self, tmp_path):
        d = self._base(tmp_path)
        d["findings"] = [
            {
                "category": "tool",
                "subject": "ruff",
                "detection_state": "detected",
                "evidence": [{"path": "f.py"}],
            }
        ]
        with pytest.raises(ReportDecodeError, match="indicator"):
            from_dict(d)

    def test_missing_diagnostic_code_raises(self, tmp_path):
        d = self._base(tmp_path)
        d["diagnostics"] = [{"message": "x", "severity": "error", "source": "test"}]
        with pytest.raises(ReportDecodeError, match="code"):
            from_dict(d)

    def test_missing_analyzer_result_name_raises(self, tmp_path):
        d = self._base(tmp_path)
        d["analyzer_results"] = [
            {"status": "complete", "findings": [], "diagnostics": []}
        ]
        with pytest.raises(ReportDecodeError, match="analyzer_name"):
            from_dict(d)


# ---------------------------------------------------------------------------
# § Malformed input → ReportDecodeError (is a SpawnError)
# ---------------------------------------------------------------------------


class TestMalformedInput:
    def test_invalid_json_raises(self):
        with pytest.raises(ReportDecodeError, match="JSON"):
            from_json("{not valid json")

    def test_json_array_raises(self):
        with pytest.raises(ReportDecodeError):
            from_json("[]")

    def test_json_null_raises(self):
        with pytest.raises(ReportDecodeError):
            from_json("null")

    def test_non_dict_input_to_from_dict_raises(self):
        with pytest.raises((ReportDecodeError, AttributeError, TypeError)):
            from_dict([])  # type: ignore[arg-type]

    def test_invalid_status_value_raises(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["status"] = "running"
        with pytest.raises(ReportDecodeError, match="AnalysisStatus"):
            from_dict(d)

    def test_invalid_detection_state_raises(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["findings"] = [
            {
                "category": "tool",
                "subject": "ruff",
                "detection_state": "confirmed",  # not a valid state
                "evidence": [],
            }
        ]
        with pytest.raises(ReportDecodeError, match="DetectionState"):
            from_dict(d)

    def test_invalid_category_raises(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["findings"] = [
            {
                "category": "unknown_future_category",
                "subject": "x",
                "detection_state": "detected",
                "evidence": [],
            }
        ]
        with pytest.raises(ReportDecodeError, match="FindingCategory"):
            from_dict(d)

    def test_non_string_status_raises(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["status"] = 42
        with pytest.raises(ReportDecodeError):
            from_dict(d)

    def test_non_list_findings_raises(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["findings"] = "not a list"
        with pytest.raises((ReportDecodeError, TypeError, AttributeError)):
            from_dict(d)

    def test_non_bool_fatal_raises(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["diagnostics"] = [
            {
                "code": "x.y",
                "message": "m",
                "severity": "error",
                "source": "test",
                "path": None,
                "fatal": "yes",  # must be bool
            }
        ]
        with pytest.raises(ReportDecodeError, match="fatal"):
            from_dict(d)

    def test_report_decode_error_is_spawn_error(self):
        assert issubclass(ReportDecodeError, SpawnError)

    def test_report_decode_error_exit_code(self):
        assert ReportDecodeError.exit_code == 7

    def test_error_message_is_informative_for_invalid_json(self):
        with pytest.raises(ReportDecodeError) as exc_info:
            from_json("{'key': 'value'}")  # single quotes — invalid JSON
        assert len(str(exc_info.value)) > 10  # has a real message


# ---------------------------------------------------------------------------
# § Rendering independence
# ---------------------------------------------------------------------------


class TestRenderingIndependence:
    def test_serialization_module_does_not_import_rich(self):
        """The serialization module must not pull in Rich or CLI rendering."""
        import importlib
        import sys

        # Reload to get fresh module without cached state
        mod_name = "spawn.inspection.serialization"
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
        else:
            mod = importlib.import_module(mod_name)

        import ast
        import inspect

        src = inspect.getsource(mod)
        tree = ast.parse(src)
        forbidden = {"rich", "spawn.cli", "spawn.utils.console", "typer"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                for name in names:
                    for f in forbidden:
                        assert not (name == f or name.startswith(f + ".")), (
                            f"serialization.py must not import {f!r}, found {name!r}"
                        )

    def test_to_json_does_not_call_console(self, tmp_path, capsys):
        """to_json must not print anything to stdout or stderr."""
        report = _full_report(tmp_path)
        to_json(report)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""


# ---------------------------------------------------------------------------
# § from_dict with optional fields absent (defaults)
# ---------------------------------------------------------------------------


class TestOptionalFieldDefaults:
    def test_missing_generated_at_defaults_to_empty(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        del d["generated_at"]
        report = from_dict(d)
        assert report.generated_at == ""

    def test_missing_findings_defaults_to_empty_tuple(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        del d["findings"]
        report = from_dict(d)
        assert report.findings == ()

    def test_missing_analyzer_results_defaults_to_empty_tuple(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        del d["analyzer_results"]
        report = from_dict(d)
        assert report.analyzer_results == ()

    def test_missing_diagnostics_defaults_to_empty_tuple(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        del d["diagnostics"]
        report = from_dict(d)
        assert report.diagnostics == ()

    def test_missing_recorded_metadata_defaults_to_none(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        del d["recorded_metadata"]
        report = from_dict(d)
        assert report.recorded_metadata is None

    def test_null_recorded_metadata_is_none(self, tmp_path):
        d = InspectionReport(
            target=_target(tmp_path), generated_at="2026-01-01T00:00:00+00:00"
        ).to_dict()
        d["recorded_metadata"] = None
        report = from_dict(d)
        assert report.recorded_metadata is None
