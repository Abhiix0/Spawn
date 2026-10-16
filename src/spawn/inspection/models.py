"""Inspection contract models — Issue #53.

All types in this module are pure data.  They import only stdlib and
``core.exceptions`` / ``core.project``; they never import from
``generators``, ``templates``, ``utils``, or ``cli``.

The public surface (re-exported from ``inspection/__init__.py``) is:

    SCHEMA_VERSION
    DetectionState, AnalysisStatus, FindingCategory
    Evidence, Diagnostic, Finding
    AnalyzerResult
    InspectionTarget, DiscoveryInventory
    ProjectSummary, RepositoryStructure
    InspectionReport
    validate_report
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from spawn.core.project import ProjectMetadata

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "1.0"
"""Bump policy (see docs/inspection/inspection-contract.md §9):
- Adding a new optional field   → no bump
- Adding a new required field   → minor bump  ("1.0" → "1.1")
- Renaming or removing a field  → major bump  ("1.0" → "2.0")
- Adding a FindingCategory value → no bump
- Changing a FindingCategory string → major bump
"""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DetectionState(StrEnum):
    """Confidence level of a Finding.

    Constraints (enforced by validate_report):
    - DETECTED and INFERRED require len(evidence) >= 1.
    - NOT_CHECKED requires len(evidence) == 0.
    - INFERRED requires a non-empty ``detail`` field.
    - NOT_DETECTED should have ``detail`` naming what was checked.
    """

    DETECTED = "detected"
    """Direct, unambiguous file evidence confirms presence.
    Example: ``[tool.pytest.ini_options]`` found in pyproject.toml."""

    INFERRED = "inferred"
    """Probable conclusion from indirect evidence.
    Example: ``fastapi`` in requirements.txt, but no pyproject.toml framework section."""

    UNKNOWN = "unknown"
    """Analyzer ran, found relevant files, but could not determine presence or absence.
    Example: ``install_requires`` is a dynamic expression the parser cannot evaluate."""

    NOT_DETECTED = "not_detected"
    """Active negative: the analyzer checked and found no evidence.
    Example: no pytest.ini, no [tool.pytest], no pytest dependency anywhere."""

    NOT_CHECKED = "not_checked"
    """The analyzer did not attempt this finding.
    Example: dependency analyzer skipped because pyproject.toml was unreadable."""


class AnalysisStatus(StrEnum):
    """Completion status of an analyzer run or the overall report."""

    COMPLETE = "complete"
    """Ran fully; zero diagnostics with fatal=True."""

    PARTIAL = "partial"
    """Ran, but ≥1 non-fatal diagnostic; findings may be incomplete."""

    FAILED = "failed"
    """≥1 fatal diagnostic or unhandled exception; output is best-effort."""

    SKIPPED = "skipped"
    """Never attempted (not registered, or a required dependency was missing)."""


class FindingCategory(StrEnum):
    """Broad category discriminating what a Finding is about.

    New values may be added in future minor versions without a schema bump.
    Consumers must handle unknown category values gracefully.
    """

    LANGUAGE = "language"
    """Programming language detected in the repository."""

    FRAMEWORK = "framework"
    """Application-level framework (e.g. FastAPI, Django, Express).
    Testing frameworks (pytest, jest) belong in TOOL."""

    PACKAGE_MANAGER = "package_manager"
    """Package manager evidence (e.g. uv, poetry, pip, npm, cargo)."""

    DEPENDENCY = "dependency"
    """A single declared package or library (one finding per package)."""

    TOOL = "tool"
    """Engineering tool: linter, formatter, type-checker, test runner,
    VCS (git), pre-commit, etc."""

    CI = "ci"
    """CI/CD system evidence (e.g. github-actions, gitlab-ci)."""

    CONTAINER = "container"
    """Container or orchestration config (e.g. docker, docker-compose)."""

    DATABASE = "database"
    """Database or cache indicator (e.g. postgres, redis, sqlite)."""

    STRUCTURE = "structure"
    """Structural observation about the repository layout
    (e.g. has-tests-directory, src-layout, spawn-generated)."""


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Evidence:
    """A single supporting file reference for a Finding.

    Path rules:
    - Always relative to the inspection root (InspectionTarget.path).
    - Always forward slashes, regardless of OS.
    - Never starts with '/' or a drive letter.
    - Never contains '..' segments.
    - Examples: "pyproject.toml", ".github/workflows/ci.yml"
    """

    path: str
    """Repository-relative posix path of the file that contains the evidence."""

    indicator: str
    """Short human-readable description of what was found at ``path``.
    Not machine-parsed; used for display and traceability.
    Examples: "[tool.pytest.ini_options] section", "import fastapi",
              "Dockerfile FROM python:3.12".
    """

    detail: str | None = None
    """Optional context: a line number, a matched version string, a specific
    key or declaration.  Plain string only; no structured sub-fields."""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "indicator": self.indicator,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# Diagnostic
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Diagnostic:
    """A recoverable problem encountered during analysis.

    Diagnostics are about the *analysis process* (parse errors, unreadable
    files, etc.).  They are NOT findings about the project itself.
    A ``not_checked`` Finding and the Diagnostic that caused it are both
    present in the output; neither replaces the other.

    Code scheme: ``<source_slug>.<snake_case_reason>``
    Each analyzer defines and documents its own codes.
    Examples: "discovery.unreadable_file", "dependency.malformed_manifest".
    """

    code: str
    """Stable dot-separated code, e.g. "discovery.unreadable_file"."""

    message: str
    """Human-readable description of the problem."""

    severity: str
    """One of: "error", "warning", "info"."""

    source: str
    """Analyzer slug or "discovery" or "orchestrator" — identifies the emitter."""

    path: str | None = None
    """Repository-relative posix path involved, if applicable."""

    fatal: bool = False
    """If True, the emitting source cannot continue.  The orchestrator uses
    this to set that analyzer's AnalysisStatus to FAILED.  A fatal=True
    Diagnostic from discovery sets the entire report status to FAILED."""

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "source": self.source,
            "path": self.path,
            "fatal": self.fatal,
        }


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One claimed observation about the project.

    Identity (for deduplication by #58 orchestrator):
        identity = (category, subject)

    ``detection_state`` is NOT part of identity.  When two findings share
    the same (category, subject), the orchestrator keeps the higher-confidence
    state (DETECTED > INFERRED > UNKNOWN > NOT_DETECTED > NOT_CHECKED)
    and merges evidence (union by path, preserving first-seen order).

    Subject format: lowercase, hyphen-separated.
    Examples: "python", "fastapi", "pytest", "uv", "postgres", "tests-directory".
    Each analyzer documents the exact subject strings it emits.

    Ordering (canonical, used in InspectionReport.findings):
        sorted ascending by (category.value, subject)
    """

    category: FindingCategory
    subject: str
    detection_state: DetectionState
    evidence: tuple[Evidence, ...]
    detail: str | None = None

    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "subject": self.subject,
            "detection_state": self.detection_state.value,
            "evidence": [e.to_dict() for e in self.evidence],
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# AnalyzerResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalyzerResult:
    """Output bundle from a single analyzer run.

    Status rules:
    - COMPLETE  : ran, zero diagnostics
    - PARTIAL   : ran, ≥1 non-fatal diagnostic
    - FAILED    : ≥1 fatal diagnostic, or unhandled exception caught by orchestrator
    - SKIPPED   : never attempted
    """

    analyzer_name: str
    status: AnalysisStatus
    findings: tuple[Finding, ...]
    diagnostics: tuple[Diagnostic, ...]

    def to_dict(self) -> dict:
        return {
            "analyzer_name": self.analyzer_name,
            "status": self.status.value,
            "findings": [f.to_dict() for f in self.findings],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


# ---------------------------------------------------------------------------
# InspectionTarget
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InspectionTarget:
    """A validated, resolved inspection root path.

    Separates "the caller supplied a path" from "we confirmed it is a readable
    directory".  Constructed by the orchestrator (#58) after validating the
    path; not constructed directly by analyzers.

    Serialisation note: ``to_dict()`` emits ``"root": "."`` — a stable,
    portable label that does not expose the absolute filesystem path in JSON.
    The absolute ``path`` is for runtime filesystem operations only.  When
    loading a report with ``from_dict()`` / ``from_json()``, ``path`` is
    reconstructed as ``Path(".")``; callers that need the original absolute
    path must supply it separately.
    """

    path: Path
    """Resolved, absolute Path confirmed to be a readable directory."""

    def to_dict(self) -> dict:
        # Emit "." as a portable root label rather than the absolute path.
        # This keeps JSON output byte-identical across machines inspecting
        # the same repository from different mount points.
        return {"root": "."}


# ---------------------------------------------------------------------------
# DiscoveryInventory
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiscoveryInventory:
    """The file/directory listing produced by the #54 discovery module.

    Defined here so #55–#58 can compile against a stable interface before
    #54 is implemented.  #54 must produce an object satisfying this shape.

    All path strings are:
    - Repository-relative
    - Forward-slash separated
    - Never absolute; never start with '/' or a drive letter
    - Sorted lexicographically (deterministic traversal)
    """

    files: tuple[str, ...]
    """Sorted relative posix paths of all discovered files."""

    directories: tuple[str, ...]
    """Sorted relative posix paths of all discovered directories."""

    skipped: tuple[str, ...]
    """Paths not traversed (excluded dirs, symlinks, permission errors).
    Reasons are recorded in ``diagnostics``; each skipped entry here is
    a plain path string."""

    diagnostics: tuple[Diagnostic, ...]
    """Recoverable errors encountered during discovery."""

    def to_dict(self) -> dict:
        return {
            "files": list(self.files),
            "directories": list(self.directories),
            "skipped": list(self.skipped),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


# ---------------------------------------------------------------------------
# ProjectSummary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectSummary:
    """Concise, human-readable facts about the inspected project.

    Derived by the orchestrator (#58) from the aggregated findings and
    ``recorded_metadata``.  It is NOT a separate analysis pass — it is a
    projection of information already present in the report, computed once
    after all analyzers have run.

    Fields
    ------
    name:
        Best-effort project name.  Derived in order of preference:
        1. ``pyproject.toml`` ``[project] name`` (from a dependency finding
           or structure analyzer).
        2. The repository's top-level directory name.
        3. ``None`` if no name can be determined.
    origin:
        ``"spawn"`` when a ``structure / spawn-generated`` finding is
        ``detected``; ``"external"`` otherwise.
    spawn_version:
        The ``spawn_version`` field from ``recorded_metadata`` when
        ``origin == "spawn"``; ``None`` otherwise.
    primary_language:
        The ``subject`` of the highest-confidence ``language`` finding, or
        ``None`` if no language finding exists.
    primary_framework:
        The ``subject`` of the highest-confidence ``framework`` finding, or
        ``None`` if no framework finding exists.
    """

    name: str | None = None
    origin: str = "external"  # "spawn" | "external"
    spawn_version: str | None = None
    primary_language: str | None = None
    primary_framework: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "origin": self.origin,
            "spawn_version": self.spawn_version,
            "primary_language": self.primary_language,
            "primary_framework": self.primary_framework,
        }


# ---------------------------------------------------------------------------
# RepositoryStructure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RepositoryStructure:
    """Overview of the repository's top-level layout.

    Derived by the orchestrator (#58) from the ``DiscoveryInventory`` and
    aggregated findings.  Like ``ProjectSummary``, this is a projection —
    not a separate analysis pass.

    Fields
    ------
    top_level_files:
        Sorted list of files at the repository root (not in subdirectories).
        Derived from ``DiscoveryInventory.files`` filtered to entries with
        no ``/`` separator.
    top_level_directories:
        Sorted list of directories at the repository root.
        Derived from ``DiscoveryInventory.directories`` filtered to entries
        with no ``/`` separator.
    file_count:
        Total number of files in ``DiscoveryInventory.files``.
    directory_count:
        Total number of directories in ``DiscoveryInventory.directories``.
    """

    top_level_files: tuple[str, ...] = ()
    top_level_directories: tuple[str, ...] = ()
    file_count: int = 0
    directory_count: int = 0

    def to_dict(self) -> dict:
        return {
            "top_level_files": list(self.top_level_files),
            "top_level_directories": list(self.top_level_directories),
            "file_count": self.file_count,
            "directory_count": self.directory_count,
        }


# ---------------------------------------------------------------------------
# InspectionReport
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InspectionReport:
    """The root result of running the inspection pipeline on a target.

    Produced by the #58 orchestrator; serialised by #59 CLI.

    Field ordering in to_dict() output is stable and documented here.
    Tests in #60 must pop ``generated_at`` before comparing two serialised
    reports (it changes per run; all other fields are deterministic).

    ``recorded_metadata`` is populated from ``.spawn/meta.json`` if present.
    It is untrusted and possibly stale — the repository may have changed
    since Spawn wrote it.  Analyzers must not use it as a primary signal for
    a DETECTED finding; at most INFERRED.  If reading it raises ConfigError,
    the orchestrator emits a Diagnostic and leaves this field None.
    """

    target: InspectionTarget
    status: AnalysisStatus = AnalysisStatus.COMPLETE
    generated_at: str = field(default_factory=lambda: _utc_now())
    schema_version: str = SCHEMA_VERSION
    recorded_metadata: ProjectMetadata | None = None
    summary: ProjectSummary = field(default_factory=ProjectSummary)
    structure: RepositoryStructure = field(default_factory=RepositoryStructure)
    findings: tuple[Finding, ...] = ()
    analyzer_results: tuple[AnalyzerResult, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def to_dict(self) -> dict:
        """Return a json.dumps-compatible dict.

        Field order is stable.  Path values are posix strings.
        StrEnum values serialise to their string value.
        generated_at is an ISO 8601 UTC string — exclude it from
        regression comparisons (it changes per run).
        """
        return {
            "schema_version": self.schema_version,
            "status": self.status.value,
            "generated_at": self.generated_at,
            "target": self.target.to_dict(),
            "recorded_metadata": (
                None
                if self.recorded_metadata is None
                else _metadata_to_dict(self.recorded_metadata)
            ),
            "summary": self.summary.to_dict(),
            "structure": self.structure.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "analyzer_results": [r.to_dict() for r in self.analyzer_results],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    """Return current UTC time as an ISO 8601 string."""
    return datetime.datetime.now(datetime.UTC).isoformat()


def _metadata_to_dict(m: ProjectMetadata) -> dict:
    """Serialise a ProjectMetadata to a plain dict.

    Does NOT call dataclasses.asdict() — keeps Path/None handling explicit
    and consistent with the rest of the codebase.
    """
    return {
        "intent": m.intent,
        "framework": m.framework,
        "provider": m.provider,
        "spawn_version": m.spawn_version,
        "created_at": m.created_at,
        "generator": m.generator,
        "git": m.git,
        "uv": m.uv,
        "source": m.source,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_DETECTION_STATE_PRECEDENCE: dict[DetectionState, int] = {
    DetectionState.DETECTED: 5,
    DetectionState.INFERRED: 4,
    DetectionState.UNKNOWN: 3,
    DetectionState.NOT_DETECTED: 2,
    DetectionState.NOT_CHECKED: 1,
}

_VALID_SEVERITIES: frozenset[str] = frozenset({"error", "warning", "info"})


def validate_report(report: InspectionReport) -> list[str]:
    """Validate an InspectionReport against the contract rules.

    Returns a list of violation messages.  An empty list means valid.
    This function is NOT called during normal inspection; it is the
    entry point for contract tests in #60 and for CI validation.
    """
    violations: list[str] = []

    for i, finding in enumerate(report.findings):
        prefix = f"findings[{i}] ({finding.category}/{finding.subject})"

        if finding.detection_state in (
            DetectionState.DETECTED,
            DetectionState.INFERRED,
        ):
            if len(finding.evidence) == 0:
                violations.append(
                    f"{prefix}: state={finding.detection_state} requires ≥1 evidence"
                )

        if finding.detection_state == DetectionState.NOT_CHECKED:
            if len(finding.evidence) != 0:
                violations.append(
                    f"{prefix}: state=not_checked must have empty evidence"
                )

        if finding.detection_state == DetectionState.INFERRED:
            if not finding.detail:
                violations.append(f"{prefix}: state=inferred requires non-empty detail")

        for j, ev in enumerate(finding.evidence):
            ep = f"{prefix} evidence[{j}]"
            if ev.path.startswith("/") or (len(ev.path) >= 2 and ev.path[1] == ":"):
                violations.append(f"{ep}: path must be relative, got {ev.path!r}")
            if ".." in ev.path.split("/"):
                violations.append(f"{ep}: path must not contain '..' segments")
            if "\\" in ev.path:
                violations.append(f"{ep}: path must use forward slashes")

    for i, diag in enumerate(report.diagnostics):
        if diag.severity not in _VALID_SEVERITIES:
            violations.append(f"diagnostics[{i}]: invalid severity {diag.severity!r}")

    for i, result in enumerate(report.analyzer_results):
        for j, diag in enumerate(result.diagnostics):
            if diag.severity not in _VALID_SEVERITIES:
                violations.append(
                    f"analyzer_results[{i}].diagnostics[{j}]: "
                    f"invalid severity {diag.severity!r}"
                )

    return violations
