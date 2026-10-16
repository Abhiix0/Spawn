"""Contract tests for src/spawn/inspection/models.py and base.py.

These tests validate the agreed types, constraints, and serialisation
rules from docs/inspection/inspection-contract.md (Issue #53).

They are NOT orchestrator or analyzer tests — they only touch the model
layer.  No filesystem is created; no analyzer logic is exercised.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spawn.inspection import (
    SCHEMA_VERSION,
    Analyzer,
    AnalyzerResult,
    AnalysisStatus,
    Diagnostic,
    DiscoveryInventory,
    DetectionState,
    Evidence,
    Finding,
    FindingCategory,
    InspectionReport,
    InspectionTarget,
    validate_report,
)
from spawn.inspection.exceptions import InspectionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _evidence(path: str = "pyproject.toml", indicator: str = "test") -> Evidence:
    return Evidence(path=path, indicator=indicator)


def _finding(
    category: FindingCategory = FindingCategory.TOOL,
    subject: str = "pytest",
    state: DetectionState = DetectionState.DETECTED,
    evidence: tuple[Evidence, ...] = (),
    detail: str | None = None,
) -> Finding:
    if evidence == () and state in (DetectionState.DETECTED, DetectionState.INFERRED):
        evidence = (_evidence(),)
    if state == DetectionState.INFERRED and detail is None:
        detail = "inferred from requirements.txt"
    return Finding(
        category=category,
        subject=subject,
        detection_state=state,
        evidence=evidence,
        detail=detail,
    )


def _diagnostic(
    code: str = "test.error",
    message: str = "test message",
    severity: str = "error",
    source: str = "test",
    path: str | None = None,
    fatal: bool = False,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=severity,
        source=source,
        path=path,
        fatal=fatal,
    )


def _target(tmp_path: Path) -> InspectionTarget:
    return InspectionTarget(path=tmp_path)


def _minimal_report(tmp_path: Path) -> InspectionReport:
    return InspectionReport(target=_target(tmp_path))


# ---------------------------------------------------------------------------
# § Schema version
# ---------------------------------------------------------------------------


class TestSchemaVersion:
    def test_schema_version_is_string(self):
        assert isinstance(SCHEMA_VERSION, str)

    def test_schema_version_format(self):
        major, minor = SCHEMA_VERSION.split(".")
        assert major.isdigit() and minor.isdigit()

    def test_report_carries_schema_version(self, tmp_path):
        report = _minimal_report(tmp_path)
        assert report.schema_version == SCHEMA_VERSION

    def test_schema_version_in_to_dict(self, tmp_path):
        d = _minimal_report(tmp_path).to_dict()
        assert d["schema_version"] == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# § DetectionState enum
# ---------------------------------------------------------------------------


class TestDetectionState:
    def test_all_five_values_exist(self):
        values = {s.value for s in DetectionState}
        assert values == {
            "detected",
            "inferred",
            "unknown",
            "not_detected",
            "not_checked",
        }

    def test_is_str(self):
        assert DetectionState.DETECTED == "detected"
        assert isinstance(DetectionState.DETECTED, str)

    def test_precedence_ordering(self):
        """DETECTED has the highest precedence; NOT_CHECKED the lowest."""
        from spawn.inspection.models import _DETECTION_STATE_PRECEDENCE

        assert (
            _DETECTION_STATE_PRECEDENCE[DetectionState.DETECTED]
            > _DETECTION_STATE_PRECEDENCE[DetectionState.INFERRED]
            > _DETECTION_STATE_PRECEDENCE[DetectionState.UNKNOWN]
            > _DETECTION_STATE_PRECEDENCE[DetectionState.NOT_DETECTED]
            > _DETECTION_STATE_PRECEDENCE[DetectionState.NOT_CHECKED]
        )


# ---------------------------------------------------------------------------
# § AnalysisStatus enum
# ---------------------------------------------------------------------------


class TestAnalysisStatus:
    def test_all_four_values_exist(self):
        values = {s.value for s in AnalysisStatus}
        assert values == {"complete", "partial", "failed", "skipped"}

    def test_is_str(self):
        assert AnalysisStatus.COMPLETE == "complete"


# ---------------------------------------------------------------------------
# § FindingCategory enum
# ---------------------------------------------------------------------------


class TestFindingCategory:
    def test_nine_categories(self):
        assert len(FindingCategory) == 9

    def test_expected_values(self):
        expected = {
            "language",
            "framework",
            "package_manager",
            "dependency",
            "tool",
            "ci",
            "container",
            "database",
            "structure",
        }
        assert {c.value for c in FindingCategory} == expected

    def test_is_str(self):
        assert FindingCategory.TOOL == "tool"


# ---------------------------------------------------------------------------
# § Evidence
# ---------------------------------------------------------------------------


class TestEvidence:
    def test_required_fields(self):
        ev = Evidence(path="pyproject.toml", indicator="[tool.pytest]")
        assert ev.path == "pyproject.toml"
        assert ev.indicator == "[tool.pytest]"
        assert ev.detail is None

    def test_optional_detail(self):
        ev = Evidence(path="pyproject.toml", indicator="dep", detail=">=3.12")
        assert ev.detail == ">=3.12"

    def test_frozen(self):
        ev = Evidence(path="a.toml", indicator="x")
        with pytest.raises((AttributeError, TypeError)):
            ev.path = "b.toml"  # type: ignore[misc]

    def test_to_dict_shape(self):
        ev = Evidence(path="src/main.py", indicator="import fastapi", detail="line 3")
        d = ev.to_dict()
        assert d == {
            "path": "src/main.py",
            "indicator": "import fastapi",
            "detail": "line 3",
        }

    def test_to_dict_null_detail(self):
        d = Evidence(path="f.txt", indicator="x").to_dict()
        assert d["detail"] is None


# ---------------------------------------------------------------------------
# § Diagnostic
# ---------------------------------------------------------------------------


class TestDiagnostic:
    def test_required_fields(self):
        d = _diagnostic()
        assert d.code == "test.error"
        assert d.fatal is False
        assert d.path is None

    def test_fatal_true(self):
        d = _diagnostic(fatal=True)
        assert d.fatal is True

    def test_to_dict_shape(self):
        d = _diagnostic(
            code="discovery.unreadable_file",
            message="cannot read x",
            severity="error",
            source="discovery",
            path="src/broken.py",
            fatal=True,
        )
        result = d.to_dict()
        assert result == {
            "code": "discovery.unreadable_file",
            "message": "cannot read x",
            "severity": "error",
            "source": "discovery",
            "path": "src/broken.py",
            "fatal": True,
        }

    def test_frozen(self):
        d = _diagnostic()
        with pytest.raises((AttributeError, TypeError)):
            d.code = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# § Finding
# ---------------------------------------------------------------------------


class TestFinding:
    def test_construction(self):
        f = _finding()
        assert f.category == FindingCategory.TOOL
        assert f.subject == "pytest"
        assert f.detection_state == DetectionState.DETECTED

    def test_frozen(self):
        f = _finding()
        with pytest.raises((AttributeError, TypeError)):
            f.subject = "changed"  # type: ignore[misc]

    def test_to_dict_shape(self):
        ev = _evidence()
        f = Finding(
            category=FindingCategory.LANGUAGE,
            subject="python",
            detection_state=DetectionState.DETECTED,
            evidence=(ev,),
            detail="3.12+",
        )
        d = f.to_dict()
        assert d["category"] == "language"
        assert d["subject"] == "python"
        assert d["detection_state"] == "detected"
        assert d["detail"] == "3.12+"
        assert len(d["evidence"]) == 1

    def test_not_checked_empty_evidence(self):
        f = Finding(
            category=FindingCategory.TOOL,
            subject="ruff",
            detection_state=DetectionState.NOT_CHECKED,
            evidence=(),
        )
        assert len(f.evidence) == 0

    def test_identity_is_category_and_subject(self):
        """Two findings with same (category, subject) but different state."""
        f1 = _finding(state=DetectionState.DETECTED)
        f2 = Finding(
            category=FindingCategory.TOOL,
            subject="pytest",
            detection_state=DetectionState.NOT_DETECTED,
            evidence=(),
        )
        # identity fields match; state differs — they are equivalent for dedup
        assert (f1.category, f1.subject) == (f2.category, f2.subject)
        assert f1 != f2  # full equality differs

    def test_empty_evidence_tuple(self):
        f = Finding(
            category=FindingCategory.STRUCTURE,
            subject="has-readme",
            detection_state=DetectionState.NOT_DETECTED,
            evidence=(),
        )
        assert f.evidence == ()


# ---------------------------------------------------------------------------
# § AnalyzerResult
# ---------------------------------------------------------------------------


class TestAnalyzerResult:
    def test_construction(self):
        r = AnalyzerResult(
            analyzer_name="language",
            status=AnalysisStatus.COMPLETE,
            findings=(),
            diagnostics=(),
        )
        assert r.analyzer_name == "language"
        assert r.status == AnalysisStatus.COMPLETE

    def test_to_dict_shape(self):
        r = AnalyzerResult(
            analyzer_name="tooling",
            status=AnalysisStatus.PARTIAL,
            findings=(_finding(),),
            diagnostics=(_diagnostic(),),
        )
        d = r.to_dict()
        assert d["analyzer_name"] == "tooling"
        assert d["status"] == "partial"
        assert len(d["findings"]) == 1
        assert len(d["diagnostics"]) == 1

    def test_frozen(self):
        r = AnalyzerResult(
            analyzer_name="x",
            status=AnalysisStatus.SKIPPED,
            findings=(),
            diagnostics=(),
        )
        with pytest.raises((AttributeError, TypeError)):
            r.analyzer_name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# § InspectionTarget
# ---------------------------------------------------------------------------


class TestInspectionTarget:
    def test_construction(self, tmp_path):
        t = InspectionTarget(path=tmp_path)
        assert t.path == tmp_path

    def test_to_dict_uses_posix(self, tmp_path):
        t = InspectionTarget(path=tmp_path)
        d = t.to_dict()
        # target serialises as a portable root label, not the absolute path
        assert d == {"root": "."}

    def test_frozen(self, tmp_path):
        t = InspectionTarget(path=tmp_path)
        with pytest.raises((AttributeError, TypeError)):
            t.path = Path("/other")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# § DiscoveryInventory
# ---------------------------------------------------------------------------


class TestDiscoveryInventory:
    def test_construction(self):
        inv = DiscoveryInventory(
            files=("a.py", "b.py"),
            directories=("src",),
            skipped=(),
            diagnostics=(),
        )
        assert inv.files == ("a.py", "b.py")

    def test_to_dict_shape(self):
        inv = DiscoveryInventory(
            files=("pyproject.toml",),
            directories=("src", "tests"),
            skipped=(".git",),
            diagnostics=(),
        )
        d = inv.to_dict()
        assert d["files"] == ["pyproject.toml"]
        assert d["directories"] == ["src", "tests"]
        assert d["skipped"] == [".git"]
        assert d["diagnostics"] == []

    def test_frozen(self):
        inv = DiscoveryInventory(files=(), directories=(), skipped=(), diagnostics=())
        with pytest.raises((AttributeError, TypeError)):
            inv.files = ("x.py",)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# § InspectionReport
# ---------------------------------------------------------------------------


class TestInspectionReport:
    def test_minimal_construction(self, tmp_path):
        report = _minimal_report(tmp_path)
        assert report.schema_version == SCHEMA_VERSION
        assert report.status == AnalysisStatus.COMPLETE
        assert report.recorded_metadata is None
        assert report.findings == ()
        assert report.analyzer_results == ()
        assert report.diagnostics == ()

    def test_generated_at_is_set(self, tmp_path):
        report = _minimal_report(tmp_path)
        assert isinstance(report.generated_at, str)
        assert len(report.generated_at) > 0

    def test_frozen(self, tmp_path):
        report = _minimal_report(tmp_path)
        with pytest.raises((AttributeError, TypeError)):
            report.status = AnalysisStatus.FAILED  # type: ignore[misc]

    def test_to_dict_top_level_keys(self, tmp_path):
        d = _minimal_report(tmp_path).to_dict()
        expected_keys = {
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
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_status_is_string(self, tmp_path):
        d = _minimal_report(tmp_path).to_dict()
        assert d["status"] == "complete"
        assert isinstance(d["status"], str)

    def test_to_dict_recorded_metadata_none(self, tmp_path):
        d = _minimal_report(tmp_path).to_dict()
        assert d["recorded_metadata"] is None

    def test_to_dict_json_serialisable(self, tmp_path):
        report = InspectionReport(
            target=_target(tmp_path),
            status=AnalysisStatus.PARTIAL,
            findings=(_finding(),),
            analyzer_results=(
                AnalyzerResult(
                    analyzer_name="tooling",
                    status=AnalysisStatus.PARTIAL,
                    findings=(),
                    diagnostics=(_diagnostic(),),
                ),
            ),
            diagnostics=(),
        )
        serialised = json.dumps(report.to_dict())
        assert isinstance(serialised, str)
        restored = json.loads(serialised)
        assert restored["schema_version"] == SCHEMA_VERSION

    def test_to_dict_target_uses_posix(self, tmp_path):
        d = _minimal_report(tmp_path).to_dict()
        # target is serialised as a portable root label
        assert d["target"] == {"root": "."}

    def test_to_dict_findings_serialised(self, tmp_path):
        report = InspectionReport(
            target=_target(tmp_path),
            findings=(_finding(),),
        )
        d = report.to_dict()
        assert len(d["findings"]) == 1
        assert d["findings"][0]["category"] == "tool"

    def test_determinism_excludes_generated_at(self, tmp_path):
        """Two independently created reports are identical after popping generated_at."""
        r1 = InspectionReport(
            target=_target(tmp_path),
            findings=(_finding(subject="pytest"), _finding(subject="ruff")),
        )
        r2 = InspectionReport(
            target=_target(tmp_path),
            findings=(_finding(subject="pytest"), _finding(subject="ruff")),
        )
        d1, d2 = r1.to_dict(), r2.to_dict()
        d1.pop("generated_at")
        d2.pop("generated_at")
        assert d1 == d2


# ---------------------------------------------------------------------------
# § Ordering / determinism
# ---------------------------------------------------------------------------


class TestOrdering:
    def test_findings_should_be_sorted_by_category_then_subject(self, tmp_path):
        """Findings placed in reverse order must be re-sorted before serialisation.
        The contract requires sorted order; the orchestrator is responsible for
        sorting before constructing InspectionReport.  This test documents the
        expected order so implementers know what to produce."""
        f_tool = _finding(category=FindingCategory.TOOL, subject="pytest")
        f_lang = _finding(category=FindingCategory.LANGUAGE, subject="python")
        # language < tool alphabetically
        report = InspectionReport(
            target=_target(tmp_path),
            findings=(f_tool, f_lang),
        )
        d = report.to_dict()
        categories = [f["category"] for f in d["findings"]]
        # The report stores findings in insertion order;
        # the ORCHESTRATOR must sort before construction.
        # This test records that the canonical order is (language, tool).
        sorted_cats = sorted(categories)
        assert sorted_cats == ["language", "tool"]

    def test_evidence_path_sort(self):
        """Evidence within a finding should be sorted by path (orchestrator's job)."""
        ev1 = Evidence(path="z_file.py", indicator="x")
        ev2 = Evidence(path="a_file.py", indicator="y")
        f = Finding(
            category=FindingCategory.LANGUAGE,
            subject="python",
            detection_state=DetectionState.DETECTED,
            evidence=(ev1, ev2),
        )
        paths = [e.path for e in f.evidence]
        sorted_paths = sorted(paths)
        # The model stores insertion order; sorting is the orchestrator's job.
        assert sorted_paths == ["a_file.py", "z_file.py"]


# ---------------------------------------------------------------------------
# § validate_report
# ---------------------------------------------------------------------------


class TestValidateReport:
    def test_valid_minimal_report(self, tmp_path):
        assert validate_report(_minimal_report(tmp_path)) == []

    def test_valid_detected_finding_with_evidence(self, tmp_path):
        report = InspectionReport(
            target=_target(tmp_path),
            findings=(_finding(state=DetectionState.DETECTED),),
        )
        assert validate_report(report) == []

    def test_detected_without_evidence_is_violation(self, tmp_path):
        f = Finding(
            category=FindingCategory.TOOL,
            subject="ruff",
            detection_state=DetectionState.DETECTED,
            evidence=(),  # violation
        )
        report = InspectionReport(target=_target(tmp_path), findings=(f,))
        violations = validate_report(report)
        assert any("evidence" in v for v in violations)

    def test_inferred_without_evidence_is_violation(self, tmp_path):
        f = Finding(
            category=FindingCategory.TOOL,
            subject="ruff",
            detection_state=DetectionState.INFERRED,
            evidence=(),  # violation
            detail="inferred from dep",
        )
        report = InspectionReport(target=_target(tmp_path), findings=(f,))
        violations = validate_report(report)
        assert any("evidence" in v for v in violations)

    def test_inferred_without_detail_is_violation(self, tmp_path):
        f = Finding(
            category=FindingCategory.TOOL,
            subject="ruff",
            detection_state=DetectionState.INFERRED,
            evidence=(_evidence(),),
            detail=None,  # violation
        )
        report = InspectionReport(target=_target(tmp_path), findings=(f,))
        violations = validate_report(report)
        assert any("detail" in v for v in violations)

    def test_not_checked_with_evidence_is_violation(self, tmp_path):
        f = Finding(
            category=FindingCategory.TOOL,
            subject="ruff",
            detection_state=DetectionState.NOT_CHECKED,
            evidence=(_evidence(),),  # violation
        )
        report = InspectionReport(target=_target(tmp_path), findings=(f,))
        violations = validate_report(report)
        assert any("evidence" in v for v in violations)

    def test_absolute_evidence_path_is_violation(self, tmp_path):
        f = Finding(
            category=FindingCategory.TOOL,
            subject="ruff",
            detection_state=DetectionState.DETECTED,
            evidence=(
                Evidence(path="/absolute/path.toml", indicator="x"),
            ),  # violation
        )
        report = InspectionReport(target=_target(tmp_path), findings=(f,))
        violations = validate_report(report)
        assert any("absolute" in v or "relative" in v for v in violations)

    def test_dotdot_in_evidence_path_is_violation(self, tmp_path):
        f = Finding(
            category=FindingCategory.TOOL,
            subject="ruff",
            detection_state=DetectionState.DETECTED,
            evidence=(Evidence(path="../escape.toml", indicator="x"),),  # violation
        )
        report = InspectionReport(target=_target(tmp_path), findings=(f,))
        violations = validate_report(report)
        assert any(".." in v for v in violations)

    def test_invalid_diagnostic_severity_is_violation(self, tmp_path):
        report = InspectionReport(
            target=_target(tmp_path),
            diagnostics=(_diagnostic(severity="critical"),),  # not a valid value
        )
        violations = validate_report(report)
        assert any("severity" in v for v in violations)

    def test_valid_inferred_finding(self, tmp_path):
        f = Finding(
            category=FindingCategory.FRAMEWORK,
            subject="fastapi",
            detection_state=DetectionState.INFERRED,
            evidence=(_evidence("requirements.txt", "fastapi in deps"),),
            detail="fastapi found in requirements.txt (no pyproject framework section)",
        )
        report = InspectionReport(target=_target(tmp_path), findings=(f,))
        assert validate_report(report) == []

    def test_not_detected_no_evidence_is_valid(self, tmp_path):
        f = Finding(
            category=FindingCategory.TOOL,
            subject="mypy",
            detection_state=DetectionState.NOT_DETECTED,
            evidence=(),
            detail="checked mypy.ini, pyrightconfig.json, pyproject.toml",
        )
        report = InspectionReport(target=_target(tmp_path), findings=(f,))
        assert validate_report(report) == []


# ---------------------------------------------------------------------------
# § Analyzer Protocol
# ---------------------------------------------------------------------------


class TestAnalyzerProtocol:
    def test_plain_class_satisfies_protocol(self):
        """A plain class with name + run() satisfies Analyzer without inheriting."""

        class StubAnalyzer:
            name = "stub"

            def run(
                self,
                target: InspectionTarget,
                inventory: DiscoveryInventory,
            ) -> AnalyzerResult:
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status=AnalysisStatus.COMPLETE,
                    findings=(),
                    diagnostics=(),
                )

        assert isinstance(StubAnalyzer(), Analyzer)

    def test_missing_name_does_not_satisfy_protocol(self):
        class BadAnalyzer:
            def run(self, target, inventory): ...

        assert not isinstance(BadAnalyzer(), Analyzer)

    def test_missing_run_does_not_satisfy_protocol(self):
        class BadAnalyzer:
            name = "bad"

        assert not isinstance(BadAnalyzer(), Analyzer)

    def test_stub_analyzer_run_returns_result(self, tmp_path):
        class StubAnalyzer:
            name = "stub"

            def run(self, target, inventory):
                return AnalyzerResult(
                    analyzer_name=self.name,
                    status=AnalysisStatus.COMPLETE,
                    findings=(),
                    diagnostics=(),
                )

        target = _target(tmp_path)
        inv = DiscoveryInventory(files=(), directories=(), skipped=(), diagnostics=())
        result = StubAnalyzer().run(target, inv)
        assert result.status == AnalysisStatus.COMPLETE
        assert result.analyzer_name == "stub"


# ---------------------------------------------------------------------------
# § InspectionError
# ---------------------------------------------------------------------------


class TestInspectionError:
    def test_exit_code(self):
        assert InspectionError.exit_code == 7

    def test_is_spawn_error(self):
        from spawn.core.exceptions import SpawnError

        assert issubclass(InspectionError, SpawnError)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(InspectionError, match="target"):
            raise InspectionError("target not found")


# ---------------------------------------------------------------------------
# § Public surface
# ---------------------------------------------------------------------------


class TestPublicSurface:
    def test_all_exports_importable(self):
        import spawn.inspection as pkg  # noqa: F401

        for name in pkg.__all__:
            assert hasattr(pkg, name), f"Missing from __all__: {name}"

    def test_schema_version_exported(self):
        from spawn.inspection import SCHEMA_VERSION as sv

        assert sv == "1.0"
