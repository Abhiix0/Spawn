"""Inspection orchestrator and report assembly (#58).

``run_inspection(path)`` validates the root, discovers the repository once,
runs the analyzers, and assembles one ``InspectionReport``.  It never writes
to the target and never touches the filesystem after discovery, except for
one ``stat`` and one bounded read of ``.spawn/meta.json``.

Semantics (contract sections 3, 4, 6, 7, 10, 11):

* Root: ``validate_inspection_root`` runs outside any ``try``.  A bad root
  raises ``InspectionError``; it never yields an empty successful report.
* Discovery runs exactly once.  If it raises ``InspectionError`` after a valid
  root, the result is a FAILED report: no findings, every analyzer SKIPPED, one
  fatal ``discovery.root_scan_failed`` diagnostic (fixed message, no paths).
* Metadata: read only when ``.spawn/meta.json`` is in ``inventory.files``
  (symlinks are never listed) and is at most 1_000_000 bytes.  Unreadable,
  malformed or oversized metadata gives ``recorded_metadata=None`` and a
  warning ``orchestrator.meta_unreadable`` with fixed text (never ``str(exc)``).
* Execution order is fixed: language, framework, dependency, tooling.  Output
  order differs: ``analyzer_results`` are sorted by ``analyzer_name``.  Every
  analyzer receives the same immutable inventory.
* Isolation: a raising analyzer becomes a FAILED result with a fatal
  ``orchestrator.analyzer_crashed`` diagnostic.  A non-``AnalyzerResult`` return
  or an ``analyzer_name`` that differs from ``analyzer.name`` becomes FAILED with
  ``orchestrator.invalid_analyzer_result``.  Other analyzers are unaffected and
  findings of a valid FAILED result are preserved.
* Status per analyzer is recomputed from its diagnostics: FAILED if any is
  fatal; PARTIAL if any non-fatal one is warning/error; else COMPLETE.  Info
  diagnostics never change status.  SKIPPED stays SKIPPED.  Report status is
  FAILED iff discovery failed; else PARTIAL if any analyzer is PARTIAL/FAILED or
  any report-level diagnostic is warning/error; else COMPLETE.
* Findings: each is checked with ``validate_report`` on a throwaway one-finding
  report; violators are dropped from the aggregate (kept in their analyzer's
  result) with warning ``orchestrator.invalid_finding``.  The rest are grouped
  by ``(category, subject)``: highest detection state wins; evidence is the
  union sorted by ``(path, indicator, detail)``; ``detail`` is the smallest
  non-empty detail among the winning-state findings.  Sorted by
  ``(category.value, subject)``.
* Report diagnostics are discovery + orchestrator diagnostics, sorted by
  ``(path, source, code, severity, message)``.  Analyzer diagnostics stay in
  their ``AnalyzerResult`` in emission order and are not repeated.
* ``summary.name`` is the root directory basename only (``None`` when empty,
  e.g. ``/``).  ``primary_language`` / ``primary_framework`` pick the best
  DETECTED finding, else the best INFERRED one, ranked by evidence count then
  subject.  Evidence count approximates representation, not importance, and
  ``primary_framework`` may be inferred: the CLI must label it.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from spawn.core.exceptions import ConfigError
from spawn.core.project import read_project_metadata
from spawn.inspection.base import Analyzer
from spawn.inspection.dependencies import DependencyAnalyzer
from spawn.inspection.discovery import discover_repository, validate_inspection_root
from spawn.inspection.exceptions import InspectionError
from spawn.inspection.frameworks import FrameworkDetector
from spawn.inspection.languages import LanguageDetector
from spawn.inspection.models import (
    _DETECTION_STATE_PRECEDENCE,
    AnalysisStatus,
    AnalyzerResult,
    DetectionState,
    Diagnostic,
    DiscoveryInventory,
    Finding,
    FindingCategory,
    InspectionReport,
    InspectionTarget,
    ProjectSummary,
    RepositoryStructure,
    validate_report,
)
from spawn.inspection.tooling import ToolingAnalyzer

ANALYZERS: tuple[Analyzer, ...] = (
    LanguageDetector(),
    FrameworkDetector(),
    DependencyAnalyzer(),
    ToolingAnalyzer(),
)

_META_PATH = ".spawn/meta.json"
_MAX_META_BYTES = 1_000_000


def _diag(code: str, message: str, severity: str, path=None, fatal=False):
    return Diagnostic(code, message, severity, "orchestrator", path, fatal)


def _failed(name: str, code: str, message: str) -> AnalyzerResult:
    return AnalyzerResult(
        name, AnalysisStatus.FAILED, (), (_diag(code, message, "error", fatal=True),)
    )


def run_inspection(path: str | Path) -> InspectionReport:
    """Inspect ``path`` read-only and return the assembled report."""
    return _inspect(path, ANALYZERS)


def _inspect(path: str | Path, analyzers: Sequence[Analyzer]) -> InspectionReport:
    target = validate_inspection_root(path)
    name = target.path.name or None
    try:
        inventory = discover_repository(target)
    except InspectionError:
        skipped = tuple(
            sorted(
                (
                    AnalyzerResult(a.name, AnalysisStatus.SKIPPED, (), ())
                    for a in analyzers
                ),
                key=lambda r: r.analyzer_name,
            )
        )
        failure = Diagnostic(
            "discovery.root_scan_failed",
            "Repository root could not be scanned",
            "error",
            "discovery",
            fatal=True,
        )
        return InspectionReport(
            target=target,
            status=AnalysisStatus.FAILED,
            summary=ProjectSummary(name=name),
            analyzer_results=skipped,
            diagnostics=(failure,),
        )

    diagnostics = list(inventory.diagnostics)
    metadata = None
    if _META_PATH in inventory.files:
        try:
            if os.stat(target.path / _META_PATH).st_size > _MAX_META_BYTES:
                raise ConfigError("oversized")
            metadata = read_project_metadata(target.path)
        except (ConfigError, OSError):
            diagnostics.append(
                _diag(
                    "orchestrator.meta_unreadable",
                    "Recorded project metadata could not be read",
                    "warning",
                    _META_PATH,
                )
            )

    results = [_run_one(a, target, inventory) for a in analyzers]

    valid: list[Finding] = []
    for result in results:
        for finding in result.findings:
            probe = InspectionReport(target=target, findings=(finding,))
            if validate_report(probe):
                diagnostics.append(
                    _diag(
                        "orchestrator.invalid_finding",
                        f"Dropped invalid finding {finding.category}/{finding.subject}"
                        f" from {result.analyzer_name}",
                        "warning",
                    )
                )
            else:
                valid.append(finding)
    findings = _aggregate(valid)

    diagnostics.sort(
        key=lambda d: (d.path or "", d.source, d.code, d.severity, d.message)
    )
    degraded = any(
        r.status in (AnalysisStatus.PARTIAL, AnalysisStatus.FAILED) for r in results
    ) or any(d.severity in ("warning", "error") for d in diagnostics)

    return InspectionReport(
        target=target,
        status=AnalysisStatus.PARTIAL if degraded else AnalysisStatus.COMPLETE,
        recorded_metadata=metadata,
        summary=_summary(name, findings, metadata),
        structure=RepositoryStructure(
            top_level_files=tuple(f for f in inventory.files if "/" not in f),
            top_level_directories=tuple(
                d for d in inventory.directories if "/" not in d
            ),
            file_count=len(inventory.files),
            directory_count=len(inventory.directories),
        ),
        findings=findings,
        analyzer_results=tuple(sorted(results, key=lambda r: r.analyzer_name)),
        diagnostics=tuple(diagnostics),
    )


def _run_one(
    analyzer: Analyzer, target: InspectionTarget, inventory: DiscoveryInventory
) -> AnalyzerResult:
    try:
        result = analyzer.run(target, inventory)
    except Exception as exc:  # noqa: BLE001 - one bad analyzer must not sink the report
        return _failed(
            analyzer.name,
            "orchestrator.analyzer_crashed",
            f"{type(analyzer).__name__} raised {type(exc).__name__}",
        )
    if (
        not isinstance(result, AnalyzerResult)
        or result.analyzer_name != analyzer.name
        or not all(isinstance(f, Finding) for f in result.findings)
        or not all(isinstance(d, Diagnostic) for d in result.diagnostics)
    ):
        return _failed(
            analyzer.name,
            "orchestrator.invalid_analyzer_result",
            f"{type(analyzer).__name__} returned an invalid result",
        )
    if result.status == AnalysisStatus.SKIPPED:
        status = AnalysisStatus.SKIPPED
    elif any(d.fatal for d in result.diagnostics):
        status = AnalysisStatus.FAILED
    elif any(d.severity in ("warning", "error") for d in result.diagnostics):
        status = AnalysisStatus.PARTIAL
    else:
        status = AnalysisStatus.COMPLETE
    return AnalyzerResult(
        result.analyzer_name, status, result.findings, result.diagnostics
    )


def _aggregate(findings: Sequence[Finding]) -> tuple[Finding, ...]:
    groups: dict[tuple[FindingCategory, str], list[Finding]] = {}
    for f in findings:
        groups.setdefault((f.category, f.subject), []).append(f)
    merged: list[Finding] = []
    for (category, subject), group in groups.items():
        best = max(_DETECTION_STATE_PRECEDENCE[f.detection_state] for f in group)
        winners = [
            f for f in group if _DETECTION_STATE_PRECEDENCE[f.detection_state] == best
        ]
        evidence = {e for f in group for e in f.evidence}
        details = [f.detail for f in winners if f.detail]
        merged.append(
            Finding(
                category,
                subject,
                winners[0].detection_state,
                tuple(
                    sorted(
                        evidence, key=lambda e: (e.path, e.indicator, e.detail or "")
                    )
                ),
                min(details) if details else None,
            )
        )
    return tuple(sorted(merged, key=lambda f: (f.category.value, f.subject)))


def _primary(findings: Sequence[Finding], category: FindingCategory) -> str | None:
    pool = [
        f
        for f in findings
        if f.category == category
        and f.detection_state in (DetectionState.DETECTED, DetectionState.INFERRED)
    ]
    if not pool:
        return None
    return min(
        pool,
        key=lambda f: (
            -_DETECTION_STATE_PRECEDENCE[f.detection_state],
            -len(f.evidence),
            f.subject,
        ),
    ).subject


def _summary(name, findings, metadata) -> ProjectSummary:
    spawn = any(
        f.category == FindingCategory.STRUCTURE
        and f.subject == "spawn-generated"
        and f.detection_state == DetectionState.DETECTED
        for f in findings
    )
    version = metadata.spawn_version if spawn and metadata else None
    return ProjectSummary(
        name=name,
        origin="spawn" if spawn else "external",
        spawn_version=version if isinstance(version, str) else None,
        primary_language=_primary(findings, FindingCategory.LANGUAGE),
        primary_framework=_primary(findings, FindingCategory.FRAMEWORK),
    )
