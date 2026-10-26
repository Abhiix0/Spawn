"""Sample-report contract tests — Issue #53, Stage C step 3.

These tests:

1.  Load tests/fixtures/static/sample_report.json and deserialise it through
    the live models (from_json).  If the file drifts from the models this fails.

2.  Re-serialise and compare bytes: from_json(raw) → to_json() must reproduce
    the file byte-for-byte.  Any model change that alters to_dict() output is
    immediately caught.

3.  Verify every required property of the sample:
    - all five detection states present (detected, inferred, unknown,
      not_detected, not_checked)
    - the inferred finding carries an explicit basis in its detail field
    - the not_detected finding names the locations checked in its detail field
    - inferred findings have evidence; not_checked findings have none
    - the recoverable diagnostic: non-fatal, source=dependency, partial status
    - per-analyzer status: dependency=partial, language=complete, tooling=complete
    - overall status: partial
    - evidence path rules: relative, forward-slash, no '..'
    - recorded_metadata present, fields match the factory

4.  Validate the report through validate_report(); any violation is a failure.

5.  Verify the factory module itself: build() returns an InspectionReport whose
    to_json() output matches the file on disk.  This is the canonical drift check.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spawn.inspection import (
    SCHEMA_VERSION,
    AnalysisStatus,
    DetectionState,
    FindingCategory,
    InspectionReport,
    from_json,
    to_json,
    validate_report,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "static"
SAMPLE_PATH = _FIXTURE_DIR / "sample_report.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def raw_text() -> str:
    """Raw UTF-8 text of the sample file."""
    return SAMPLE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report(raw_text: str) -> InspectionReport:
    """Deserialised InspectionReport from the sample file."""
    return from_json(raw_text)


@pytest.fixture(scope="module")
def findings_by_state(report: InspectionReport) -> dict[str, list]:
    """Map detection_state.value → list of findings in that state."""
    result: dict[str, list] = {}
    for f in report.findings:
        result.setdefault(f.detection_state.value, []).append(f)
    return result


@pytest.fixture(scope="module")
def analyzer_results_by_name(report: InspectionReport) -> dict:
    return {r.analyzer_name: r for r in report.analyzer_results}


# ---------------------------------------------------------------------------
# § Drift prevention: file ↔ factory ↔ models are all in sync
# ---------------------------------------------------------------------------


class TestDriftPrevention:
    def test_file_deserialises_without_error(self, report):
        """from_json(file) must not raise — tests model ↔ file compatibility."""
        assert isinstance(report, InspectionReport)

    def test_factory_matches_file_bytes(self, raw_text):
        """build() → to_json() must reproduce the file byte-for-byte.

        This is the canonical drift check: any change to the factory or the
        models that alters serialised output will break this test, forcing an
        explicit regeneration of the file.
        """
        import importlib.util
        import sys

        factory_path = Path(__file__).parent / "fixtures" / "make_sample_report.py"
        spec = importlib.util.spec_from_file_location(
            "make_sample_report", factory_path
        )
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        sys.modules.setdefault("make_sample_report", module)
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        factory_json = to_json(module.build())
        assert factory_json == raw_text, (
            "sample_report.json is out of sync with make_sample_report.build().\n"
            "Regenerate it with:\n"
            "  uv run python tests/fixtures/make_sample_report.py"
        )

    def test_round_trip_byte_identical(self, raw_text, report):
        """Deserialise the file then re-serialise; result must match the file."""
        assert to_json(report) == raw_text

    def test_validate_report_clean(self, report):
        """validate_report() must return no violations."""
        violations = validate_report(report)
        assert violations == [], f"Contract violations: {violations}"

    def test_file_is_valid_json(self, raw_text):
        parsed = json.loads(raw_text)
        assert isinstance(parsed, dict)

    def test_schema_version_matches_current(self, report):
        assert report.schema_version == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# § All five detection states present
# ---------------------------------------------------------------------------


class TestDetectionStateCoverage:
    def test_detected_present(self, findings_by_state):
        assert "detected" in findings_by_state, "Sample must contain a detected finding"

    def test_inferred_present(self, findings_by_state):
        assert "inferred" in findings_by_state, (
            "Sample must contain an inferred finding"
        )

    def test_unknown_present(self, findings_by_state):
        assert "unknown" in findings_by_state, "Sample must contain an unknown finding"

    def test_not_detected_present(self, findings_by_state):
        assert "not_detected" in findings_by_state, (
            "Sample must contain a not_detected finding"
        )

    def test_not_checked_present(self, findings_by_state):
        assert "not_checked" in findings_by_state, (
            "Sample must contain a not_checked finding"
        )

    def test_all_five_states_covered(self, findings_by_state):
        assert set(findings_by_state.keys()) == {
            "detected",
            "inferred",
            "unknown",
            "not_detected",
            "not_checked",
        }


# ---------------------------------------------------------------------------
# § Inferred finding rules
# ---------------------------------------------------------------------------


class TestInferredFinding:
    def test_inferred_has_evidence(self, findings_by_state):
        for f in findings_by_state["inferred"]:
            assert len(f.evidence) >= 1, (
                f"Inferred finding {f.subject} must carry evidence"
            )

    def test_inferred_has_detail_basis(self, findings_by_state):
        """Every inferred finding must have a non-empty detail explaining the basis."""
        for f in findings_by_state["inferred"]:
            assert f.detail and len(f.detail) > 0, (
                f"Inferred finding {f.subject} must have detail explaining the basis"
            )

    def test_inferred_detail_describes_source(self, findings_by_state):
        """The inferred finding's detail must reference its evidence source."""
        uv_findings = [f for f in findings_by_state["inferred"] if f.subject == "uv"]
        assert uv_findings, "Sample must include an inferred uv finding"
        f = uv_findings[0]
        # The detail should mention the evidence file or the nature of the inference
        assert any(
            keyword in f.detail.lower()
            for keyword in ("uv.lock", "lockfile", "no [tool.uv]", "pyproject")
        ), f"Inferred detail should describe the basis, got: {f.detail!r}"

    def test_inferred_category_and_subject(self, findings_by_state):
        uv_findings = [f for f in findings_by_state["inferred"] if f.subject == "uv"]
        assert uv_findings
        f = uv_findings[0]
        assert f.category == FindingCategory.PACKAGE_MANAGER
        assert f.detection_state == DetectionState.INFERRED


# ---------------------------------------------------------------------------
# § Not-detected finding rules
# ---------------------------------------------------------------------------


class TestNotDetectedFinding:
    def test_not_detected_has_detail_with_checked_locations(self, findings_by_state):
        """Not-detected findings must name what was checked."""
        for f in findings_by_state["not_detected"]:
            assert f.detail and len(f.detail) > 0, (
                f"not_detected finding {f.subject} must have detail naming checked locations"
            )

    def test_not_detected_detail_mentions_paths(self, findings_by_state):
        """The not_detected detail should reference at least one checked path."""
        for f in findings_by_state["not_detected"]:
            assert any(c in f.detail for c in ("/", ".", "*")), (
                f"not_detected detail should mention checked paths, got: {f.detail!r}"
            )

    def test_not_detected_github_actions(self, findings_by_state):
        gh_findings = [
            f
            for f in findings_by_state["not_detected"]
            if f.subject == "github-actions"
        ]
        assert gh_findings, "Sample must include a not_detected github-actions finding"
        f = gh_findings[0]
        assert f.category == FindingCategory.CI
        assert ".github/workflows" in f.detail


# ---------------------------------------------------------------------------
# § Not-checked finding rules
# ---------------------------------------------------------------------------


class TestNotCheckedFinding:
    def test_not_checked_has_no_evidence(self, findings_by_state):
        for f in findings_by_state["not_checked"]:
            assert len(f.evidence) == 0, (
                f"not_checked finding {f.subject} must have empty evidence"
            )

    def test_not_checked_docker(self, findings_by_state):
        docker = [f for f in findings_by_state["not_checked"] if f.subject == "docker"]
        assert docker, "Sample must include a not_checked docker finding"
        assert docker[0].category == FindingCategory.CONTAINER


# ---------------------------------------------------------------------------
# § Evidence path rules
# ---------------------------------------------------------------------------


class TestEvidencePathRules:
    def test_all_evidence_paths_are_relative(self, report):
        for f in report.findings:
            for ev in f.evidence:
                assert not ev.path.startswith("/"), (
                    f"Evidence path must be relative, got {ev.path!r} "
                    f"in finding {f.subject}"
                )
                assert not (len(ev.path) >= 2 and ev.path[1] == ":"), (
                    f"Evidence path must not be a drive-letter path, got {ev.path!r}"
                )

    def test_all_evidence_paths_use_forward_slashes(self, report):
        for f in report.findings:
            for ev in f.evidence:
                assert "\\" not in ev.path, (
                    f"Evidence path must use forward slashes, got {ev.path!r}"
                )

    def test_no_dotdot_in_evidence_paths(self, report):
        for f in report.findings:
            for ev in f.evidence:
                assert ".." not in ev.path.split("/"), (
                    f"Evidence path must not contain '..', got {ev.path!r}"
                )

    def test_detected_findings_have_evidence(self, findings_by_state):
        for f in findings_by_state["detected"]:
            assert len(f.evidence) >= 1, (
                f"detected finding {f.subject} must carry evidence"
            )

    def test_evidence_indicator_non_empty(self, report):
        for f in report.findings:
            for ev in f.evidence:
                assert ev.indicator and len(ev.indicator) > 0, (
                    f"Evidence indicator must not be empty in finding {f.subject}"
                )


# ---------------------------------------------------------------------------
# § Recoverable diagnostic and partial results
# ---------------------------------------------------------------------------


class TestRecoverableDiagnostic:
    def test_dependency_analyzer_is_partial(self, analyzer_results_by_name):
        dep = analyzer_results_by_name.get("dependency")
        assert dep is not None, "Sample must include a dependency analyzer result"
        assert dep.status == AnalysisStatus.PARTIAL

    def test_dependency_has_exactly_one_diagnostic(self, analyzer_results_by_name):
        dep = analyzer_results_by_name["dependency"]
        assert len(dep.diagnostics) == 1

    def test_diagnostic_is_non_fatal(self, analyzer_results_by_name):
        diag = analyzer_results_by_name["dependency"].diagnostics[0]
        assert diag.fatal is False

    def test_diagnostic_code_format(self, analyzer_results_by_name):
        diag = analyzer_results_by_name["dependency"].diagnostics[0]
        assert "." in diag.code, "Diagnostic code must be dot-separated"
        assert diag.code == diag.code.lower(), "Diagnostic code must be lowercase"

    def test_diagnostic_source_matches_analyzer(self, analyzer_results_by_name):
        dep = analyzer_results_by_name["dependency"]
        diag = dep.diagnostics[0]
        assert diag.source == dep.analyzer_name

    def test_diagnostic_severity_is_warning(self, analyzer_results_by_name):
        diag = analyzer_results_by_name["dependency"].diagnostics[0]
        assert diag.severity == "warning"

    def test_diagnostic_references_file(self, analyzer_results_by_name):
        diag = analyzer_results_by_name["dependency"].diagnostics[0]
        assert diag.path == "requirements.txt"

    def test_diagnostic_path_is_relative(self, analyzer_results_by_name):
        diag = analyzer_results_by_name["dependency"].diagnostics[0]
        assert diag.path is not None
        assert not diag.path.startswith("/")
        assert "\\" not in diag.path

    def test_non_fatal_diagnostic_preserves_findings(
        self, report, analyzer_results_by_name
    ):
        """A partial analyzer must not eliminate the report's aggregated findings."""
        # The report has findings even though dependency is partial —
        # the other analyzers' findings are preserved.
        assert len(report.findings) > 0

    def test_malformed_file_finding_still_possible(self, findings_by_state):
        """The sample shows sqlalchemy as unknown because of the malformed setup.cfg."""
        unk = [
            f for f in findings_by_state.get("unknown", []) if f.subject == "sqlalchemy"
        ]
        assert unk, (
            "Sample must include an unknown sqlalchemy finding from malformed file"
        )


# ---------------------------------------------------------------------------
# § Per-analyzer status semantics
# ---------------------------------------------------------------------------


class TestPerAnalyzerStatus:
    def test_four_analyzers_present(self, analyzer_results_by_name):
        assert set(analyzer_results_by_name.keys()) == {
            "dependency",
            "framework",
            "language",
            "tooling",
        }

    def test_language_is_complete(self, analyzer_results_by_name):
        assert analyzer_results_by_name["language"].status == AnalysisStatus.COMPLETE

    def test_tooling_is_complete(self, analyzer_results_by_name):
        assert analyzer_results_by_name["tooling"].status == AnalysisStatus.COMPLETE

    def test_dependency_is_partial(self, analyzer_results_by_name):
        assert analyzer_results_by_name["dependency"].status == AnalysisStatus.PARTIAL

    def test_complete_analyzers_have_no_diagnostics(self, analyzer_results_by_name):
        for name in ("language", "tooling"):
            r = analyzer_results_by_name[name]
            assert r.diagnostics == (), (
                f"Complete analyzer {name!r} must have no diagnostics"
            )


# ---------------------------------------------------------------------------
# § Overall report status
# ---------------------------------------------------------------------------


class TestOverallStatus:
    def test_overall_status_is_partial(self, report):
        assert report.status == AnalysisStatus.PARTIAL

    def test_no_report_level_diagnostics(self, report):
        """Sample has no report-level diagnostics; all diagnostics are per-analyzer."""
        assert report.diagnostics == ()

    def test_report_has_findings(self, report):
        assert len(report.findings) > 0

    def test_report_has_analyzer_results(self, report):
        assert len(report.analyzer_results) > 0


# ---------------------------------------------------------------------------
# § Recorded metadata
# ---------------------------------------------------------------------------


class TestRecordedMetadata:
    def test_recorded_metadata_present(self, report):
        assert report.recorded_metadata is not None

    def test_intent_is_backend_api(self, report):
        assert report.recorded_metadata.intent == "backend-api"

    def test_framework_is_fastapi(self, report):
        assert report.recorded_metadata.framework == "fastapi"

    def test_generator_is_blueprint(self, report):
        assert report.recorded_metadata.generator == "blueprint"

    def test_git_and_uv_true(self, report):
        assert report.recorded_metadata.git is True
        assert report.recorded_metadata.uv is True

    def test_provider_is_none(self, report):
        assert report.recorded_metadata.provider is None


# ---------------------------------------------------------------------------
# § Finding ordering
# ---------------------------------------------------------------------------


class TestFindingOrdering:
    def test_findings_sorted_by_category_then_subject(self, report):
        """Canonical order: ascending by (category.value, subject)."""
        pairs = [(f.category.value, f.subject) for f in report.findings]
        assert pairs == sorted(pairs), (
            f"Findings are not in canonical order. Got: {pairs}"
        )

    def test_analyzer_results_sorted_by_name(self, report):
        names = [r.analyzer_name for r in report.analyzer_results]
        assert names == sorted(names), (
            f"Analyzer results are not sorted by name. Got: {names}"
        )


# ---------------------------------------------------------------------------
# § Category coverage
# ---------------------------------------------------------------------------


class TestCategoryCoverage:
    def test_categories_present(self, report):
        categories = {f.category for f in report.findings}
        required = {
            FindingCategory.CI,
            FindingCategory.CONTAINER,
            FindingCategory.DEPENDENCY,
            FindingCategory.FRAMEWORK,
            FindingCategory.LANGUAGE,
            FindingCategory.PACKAGE_MANAGER,
            FindingCategory.STRUCTURE,
            FindingCategory.TOOL,
        }
        missing = required - categories
        assert not missing, f"Sample is missing findings for categories: {missing}"
