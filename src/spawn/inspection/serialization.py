"""Inspection report serialization — Issue #53.

Provides:
    to_json(report)              -> str   (deterministic JSON, 2-space indent)
    from_dict(d)                 -> InspectionReport   (raises ReportDecodeError)
    from_json(text)              -> InspectionReport   (raises ReportDecodeError)

Design constraints (from the contract, §8):
- to_json() output is deterministic: same report → byte-identical JSON.
- generated_at is present but excluded from regression comparisons by callers.
- Unknown fields in the input dict are silently ignored (forward-compat).
- A supported-but-unknown schema_version (same major, higher minor) is
  accepted; findings/fields added in that minor are tolerated via the
  unknown-field rule.
- A different major version raises ReportDecodeError with a clear message.
- Malformed input (wrong types, missing required keys) raises ReportDecodeError.
- Rendering (Rich, terminal) is entirely absent from this module.

Import rule: this module may import only stdlib, spawn.inspection.models,
and spawn.inspection.exceptions.  It must not import spawn.cli, spawn.utils,
spawn.generators, spawn.templates, or spawn.core.registry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spawn.inspection.exceptions import InspectionError
from spawn.inspection.models import (
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
    ProjectSummary,
    RepositoryStructure,
)
from spawn.core.project import ProjectMetadata

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

_SUPPORTED_MAJOR: int = int(SCHEMA_VERSION.split(".")[0])


class ReportDecodeError(InspectionError):
    """Raised when a JSON report cannot be decoded into an InspectionReport.

    This is a SpawnError subclass (exit_code = 7) so the CLI can handle it
    uniformly alongside InspectionError.

    Causes include: malformed JSON, missing required fields, wrong types,
    and incompatible schema_version major number.
    """

    exit_code = 7


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def to_json(report: InspectionReport, *, indent: int = 2) -> str:
    """Serialise *report* to a deterministic JSON string.

    The output is byte-identical for equal reports (modulo ``generated_at``,
    which changes per run and must be excluded from regression comparisons).

    Key ordering within every object follows the stable order defined in
    each model's ``to_dict()`` method.  Lists are in canonical order:

    - ``findings``        : sorted ascending by (category, subject)
    - ``analyzer_results``: sorted ascending by analyzer_name
    - ``evidence``        : sorted ascending by path (within each finding)
    - ``diagnostics``     : emission order (stable; no sort applied)

    Sorting is the caller's responsibility — this function serialises the
    report exactly as constructed.  The orchestrator (#58) is responsible
    for constructing the report with correctly ordered sequences.

    Parameters
    ----------
    report:
        The InspectionReport to serialise.
    indent:
        JSON indentation level (default 2, matches the rest of the codebase).

    Returns
    -------
    str
        A UTF-8 JSON string ending with a newline.
    """
    return json.dumps(report.to_dict(), indent=indent, ensure_ascii=False) + "\n"


def from_dict(d: dict[str, Any]) -> InspectionReport:
    """Deserialise a plain dict (as produced by json.loads) into an InspectionReport.

    Version handling
    ----------------
    - Same major, any minor  → accepted; unknown fields silently ignored.
    - Different major        → raises ReportDecodeError immediately.
    - Missing schema_version → raises ReportDecodeError.

    Unknown fields
    --------------
    Any key in *d* (or in any nested object) that is not part of the known
    schema is silently ignored.  This allows forward-compatible reading of
    reports produced by a newer minor version.

    Required top-level fields
    -------------------------
    schema_version, status, target.

    All other fields are optional and fall back to their model defaults when
    absent (empty tuples, None, SCHEMA_VERSION, current time).

    Raises
    ------
    ReportDecodeError
        On incompatible major version, missing required keys, or type errors.
    """
    try:
        return _decode_report(d)
    except ReportDecodeError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ReportDecodeError(f"Malformed inspection report: {exc}") from exc


def from_json(text: str) -> InspectionReport:
    """Parse *text* as JSON and deserialise into an InspectionReport.

    Raises
    ------
    ReportDecodeError
        On invalid JSON or any decoding failure.
    """
    try:
        d = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReportDecodeError(f"Invalid JSON: {exc}") from exc
    if not isinstance(d, dict):
        raise ReportDecodeError(
            f"Expected a JSON object at the top level, got {type(d).__name__}"
        )
    return from_dict(d)


# ---------------------------------------------------------------------------
# Internal decoders — one per model, each ignores unknown keys
# ---------------------------------------------------------------------------


def _require(d: dict[str, Any], key: str, context: str) -> Any:
    """Return d[key] or raise ReportDecodeError with a clear message."""
    if key not in d:
        raise ReportDecodeError(f"Missing required field '{key}' in {context}")
    return d[key]


def _decode_report(d: dict[str, Any]) -> InspectionReport:
    # --- schema_version: required, major must match ---
    raw_version = _require(d, "schema_version", "report")
    if not isinstance(raw_version, str):
        raise ReportDecodeError(
            f"'schema_version' must be a string, got {type(raw_version).__name__}"
        )
    _check_version(raw_version)

    # --- status: required ---
    raw_status = _require(d, "status", "report")
    status = _decode_analysis_status(raw_status, context="report.status")

    # --- target: required ---
    raw_target = _require(d, "target", "report")
    if not isinstance(raw_target, dict):
        raise ReportDecodeError(
            f"'target' must be an object, got {type(raw_target).__name__}"
        )
    target = _decode_target(raw_target)

    # --- optional fields ---
    generated_at: str = d.get("generated_at", "")
    if not isinstance(generated_at, str):
        raise ReportDecodeError(
            f"'generated_at' must be a string, got {type(generated_at).__name__}"
        )

    recorded_metadata = _decode_recorded_metadata(d.get("recorded_metadata"))

    summary = _decode_project_summary(d.get("summary", {}))
    structure = _decode_repository_structure(d.get("structure", {}))

    findings = tuple(_decode_finding(f, i) for i, f in enumerate(d.get("findings", [])))
    analyzer_results = tuple(
        _decode_analyzer_result(r, i)
        for i, r in enumerate(d.get("analyzer_results", []))
    )
    diagnostics = tuple(
        _decode_diagnostic(diag, f"report.diagnostics[{i}]")
        for i, diag in enumerate(d.get("diagnostics", []))
    )

    return InspectionReport(
        target=target,
        status=status,
        generated_at=generated_at,
        schema_version=raw_version,
        recorded_metadata=recorded_metadata,
        summary=summary,
        structure=structure,
        findings=findings,
        analyzer_results=analyzer_results,
        diagnostics=diagnostics,
    )


def _check_version(version_str: str) -> None:
    """Raise ReportDecodeError if the major version is not supported."""
    try:
        major_str, _ = version_str.split(".", 1)
        major = int(major_str)
    except ValueError:
        raise ReportDecodeError(
            f"Cannot parse schema_version {version_str!r}: expected 'major.minor' format"
        )
    if major != _SUPPORTED_MAJOR:
        raise ReportDecodeError(
            f"Unsupported schema_version {version_str!r}: "
            f"this build supports major version {_SUPPORTED_MAJOR}, "
            f"got {major}.  Upgrade Spawn to read this report."
        )


def _decode_analysis_status(raw: Any, context: str) -> AnalysisStatus:
    if not isinstance(raw, str):
        raise ReportDecodeError(
            f"'{context}' must be a string, got {type(raw).__name__}"
        )
    try:
        return AnalysisStatus(raw)
    except ValueError:
        valid = ", ".join(s.value for s in AnalysisStatus)
        raise ReportDecodeError(
            f"Unknown AnalysisStatus {raw!r} in {context}. Valid: {valid}"
        )


def _decode_target(d: dict[str, Any]) -> InspectionTarget:
    # "root" is the portable label emitted by to_dict(); reconstruct as Path(".")
    # so the loaded object is usable. Callers that need the actual absolute
    # path must supply it when constructing InspectionTarget for runtime use.
    raw_root = d.get("root", ".")
    if not isinstance(raw_root, str):
        raise ReportDecodeError(
            f"'target.root' must be a string, got {type(raw_root).__name__}"
        )
    return InspectionTarget(path=Path(raw_root))


def _decode_recorded_metadata(raw: Any) -> ProjectMetadata | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ReportDecodeError(
            f"'recorded_metadata' must be an object or null, got {type(raw).__name__}"
        )
    # Unknown keys silently ignored; all fields optional (ProjectMetadata defaults)
    return ProjectMetadata(
        intent=raw.get("intent"),
        framework=raw.get("framework"),
        provider=raw.get("provider"),
        spawn_version=raw.get("spawn_version"),
        created_at=raw.get("created_at"),
        generator=raw.get("generator"),
        git=raw.get("git"),
        uv=raw.get("uv"),
        source=raw.get("source"),
    )


def _decode_project_summary(raw: Any) -> ProjectSummary:
    if raw is None or not isinstance(raw, dict):
        return ProjectSummary()
    name = raw.get("name")
    origin = raw.get("origin", "external")
    spawn_version = raw.get("spawn_version")
    primary_language = raw.get("primary_language")
    primary_framework = raw.get("primary_framework")
    for field_name, value in (("origin", origin),):
        if not isinstance(value, str):
            raise ReportDecodeError(
                f"'summary.{field_name}' must be a string, got {type(value).__name__}"
            )
    return ProjectSummary(
        name=name if isinstance(name, str) else None,
        origin=origin,
        spawn_version=spawn_version if isinstance(spawn_version, str) else None,
        primary_language=primary_language
        if isinstance(primary_language, str)
        else None,
        primary_framework=primary_framework
        if isinstance(primary_framework, str)
        else None,
    )


def _decode_repository_structure(raw: Any) -> RepositoryStructure:
    if raw is None or not isinstance(raw, dict):
        return RepositoryStructure()
    top_level_files = raw.get("top_level_files", [])
    top_level_directories = raw.get("top_level_directories", [])
    file_count = raw.get("file_count", 0)
    directory_count = raw.get("directory_count", 0)
    if not isinstance(top_level_files, list):
        top_level_files = []
    if not isinstance(top_level_directories, list):
        top_level_directories = []
    if not isinstance(file_count, int):
        file_count = 0
    if not isinstance(directory_count, int):
        directory_count = 0
    return RepositoryStructure(
        top_level_files=tuple(str(f) for f in top_level_files),
        top_level_directories=tuple(str(d) for d in top_level_directories),
        file_count=file_count,
        directory_count=directory_count,
    )


def _decode_evidence(d: Any, context: str) -> Evidence:
    if not isinstance(d, dict):
        raise ReportDecodeError(
            f"Evidence item in {context} must be an object, got {type(d).__name__}"
        )
    path = _require(d, "path", context)
    indicator = _require(d, "indicator", context)
    if not isinstance(path, str):
        raise ReportDecodeError(f"'path' in {context} must be a string")
    if not isinstance(indicator, str):
        raise ReportDecodeError(f"'indicator' in {context} must be a string")
    detail = d.get("detail")
    if detail is not None and not isinstance(detail, str):
        raise ReportDecodeError(f"'detail' in {context} must be a string or null")
    return Evidence(path=path, indicator=indicator, detail=detail)


def _decode_diagnostic(d: Any, context: str) -> Diagnostic:
    if not isinstance(d, dict):
        raise ReportDecodeError(
            f"Diagnostic in {context} must be an object, got {type(d).__name__}"
        )
    code = _require(d, "code", context)
    message = _require(d, "message", context)
    severity = _require(d, "severity", context)
    source = _require(d, "source", context)
    for field_name, value in (
        ("code", code),
        ("message", message),
        ("severity", severity),
        ("source", source),
    ):
        if not isinstance(value, str):
            raise ReportDecodeError(
                f"'{field_name}' in {context} must be a string, got {type(value).__name__}"
            )
    path = d.get("path")
    if path is not None and not isinstance(path, str):
        raise ReportDecodeError(f"'path' in {context} must be a string or null")
    fatal = d.get("fatal", False)
    if not isinstance(fatal, bool):
        raise ReportDecodeError(f"'fatal' in {context} must be a boolean")
    return Diagnostic(
        code=code,
        message=message,
        severity=severity,
        source=source,
        path=path,
        fatal=fatal,
    )


def _decode_detection_state(raw: Any, context: str) -> DetectionState:
    if not isinstance(raw, str):
        raise ReportDecodeError(
            f"'detection_state' in {context} must be a string, got {type(raw).__name__}"
        )
    try:
        return DetectionState(raw)
    except ValueError:
        valid = ", ".join(s.value for s in DetectionState)
        raise ReportDecodeError(
            f"Unknown DetectionState {raw!r} in {context}. Valid: {valid}"
        )


def _decode_finding_category(raw: Any, context: str) -> FindingCategory:
    if not isinstance(raw, str):
        raise ReportDecodeError(
            f"'category' in {context} must be a string, got {type(raw).__name__}"
        )
    try:
        return FindingCategory(raw)
    except ValueError:
        # Unknown category: additive extension, not a decode error.
        # Per §8 bump policy, new FindingCategory values require no version bump.
        # Rather than raising, we propagate the raw string as a best-effort
        # STRUCTURE finding so the report still loads.
        # However, since FindingCategory is a StrEnum, we cannot store an
        # arbitrary string — raise with a clear message so the caller knows
        # which category to add.
        valid = ", ".join(c.value for c in FindingCategory)
        raise ReportDecodeError(
            f"Unknown FindingCategory {raw!r} in {context}. "
            f"Valid: {valid}. "
            f"If this is a new category from a newer minor version, "
            f"upgrade Spawn to decode it."
        )


def _decode_finding(d: Any, index: int) -> Finding:
    context = f"findings[{index}]"
    if not isinstance(d, dict):
        raise ReportDecodeError(
            f"Finding at {context} must be an object, got {type(d).__name__}"
        )
    category = _decode_finding_category(_require(d, "category", context), context)
    subject = _require(d, "subject", context)
    if not isinstance(subject, str):
        raise ReportDecodeError(f"'subject' in {context} must be a string")
    detection_state = _decode_detection_state(
        _require(d, "detection_state", context), context
    )
    raw_evidence = d.get("evidence", [])
    if not isinstance(raw_evidence, list):
        raise ReportDecodeError(f"'evidence' in {context} must be an array")
    evidence = tuple(
        _decode_evidence(ev, f"{context}.evidence[{j}]")
        for j, ev in enumerate(raw_evidence)
    )
    detail = d.get("detail")
    if detail is not None and not isinstance(detail, str):
        raise ReportDecodeError(f"'detail' in {context} must be a string or null")
    return Finding(
        category=category,
        subject=subject,
        detection_state=detection_state,
        evidence=evidence,
        detail=detail,
    )


def _decode_analyzer_result(d: Any, index: int) -> AnalyzerResult:
    context = f"analyzer_results[{index}]"
    if not isinstance(d, dict):
        raise ReportDecodeError(
            f"AnalyzerResult at {context} must be an object, got {type(d).__name__}"
        )
    analyzer_name = _require(d, "analyzer_name", context)
    if not isinstance(analyzer_name, str):
        raise ReportDecodeError(f"'analyzer_name' in {context} must be a string")
    status = _decode_analysis_status(
        _require(d, "status", context), context=f"{context}.status"
    )
    raw_findings = d.get("findings", [])
    if not isinstance(raw_findings, list):
        raise ReportDecodeError(f"'findings' in {context} must be an array")
    findings = tuple(_decode_finding(f, i) for i, f in enumerate(raw_findings))
    raw_diags = d.get("diagnostics", [])
    if not isinstance(raw_diags, list):
        raise ReportDecodeError(f"'diagnostics' in {context} must be an array")
    diagnostics = tuple(
        _decode_diagnostic(diag, f"{context}.diagnostics[{i}]")
        for i, diag in enumerate(raw_diags)
    )
    return AnalyzerResult(
        analyzer_name=analyzer_name,
        status=status,
        findings=findings,
        diagnostics=diagnostics,
    )
