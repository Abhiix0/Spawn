"""Public onboarding report projection and its independent JSON contract."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from spawn.inspection import (
    AnalysisStatus,
    DetectionState,
    Evidence,
    FindingCategory,
    InspectionError,
)
from spawn.inspection.development_workflows import DevelopmentCommand
from spawn.inspection.entry_points import PythonEntryPoint
from spawn.inspection.onboarding import inspect_python_onboarding

ONBOARD_SCHEMA_VERSION = "1.0"
_SEVERITIES = ("info", "warning", "error")
_KEY_FILES = {
    "pyproject.toml",
    "uv.lock",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "pytest.ini",
    "tox.ini",
    "ruff.toml",
    ".ruff.toml",
    "setup.cfg",
    "Makefile",
    "manage.py",
    "Dockerfile",
    "compose.yml",
    "compose.yaml",
    "docker-compose.yml",
    "docker-compose.yaml",
    "README.md",
}


@dataclass(frozen=True)
class Technology:
    name: str
    status: str
    evidence: tuple[Evidence, ...]
    evidence_count: int


@dataclass(frozen=True)
class OnboardingDiagnostic:
    code: str
    severity: str
    path: str | None = None


@dataclass(frozen=True)
class OnboardingReport:
    name: str
    generated_at: str
    status: AnalysisStatus
    file_count: int
    directory_count: int
    languages: tuple[Technology, ...]
    frameworks: tuple[Technology, ...]
    entry_points: tuple[PythonEntryPoint, ...]
    commands: tuple[DevelopmentCommand, ...]
    directories: tuple[str, ...]
    config_files: tuple[str, ...]
    diagnostics: tuple[OnboardingDiagnostic, ...]

    def diagnostic_counts(self) -> dict[str, int]:
        return {
            level: sum(item.severity == level for item in self.diagnostics)
            for level in _SEVERITIES
        }


def _printable(value: str) -> str:
    return "".join(
        "?" if unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"} else char
        for char in value
    )


def _relative(value: str | None) -> str | None:
    if value is None or "\\" in value or ":" in value or _printable(value) != value:
        return None
    if any(part in {"", ".", ".."} for part in value.split("/")):
        return None
    return value


def _evidence(items: tuple[Evidence, ...]) -> tuple[Evidence, ...]:
    # Inspection details are free text. Only keep a source line reference here.
    return tuple(
        Evidence(
            item.path,
            _printable(item.indicator),
            item.detail
            if item.detail and re.fullmatch(r"line [1-9][0-9]*", item.detail)
            else None,
        )
        for item in items
        if _relative(item.path) is not None
    )


def _key_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (
        name in _KEY_FILES
        or (name.startswith("requirements") and name.endswith(".txt"))
        or (path.startswith(".github/workflows/") and name.endswith((".yml", ".yaml")))
    )


def build_onboarding_report(path: str | Path) -> OnboardingReport:
    """Project bounded evidence and safe summaries from a single inventory."""
    result = inspect_python_onboarding(path)
    inspection = result.inspection
    if inspection.status is AnalysisStatus.FAILED:
        raise InspectionError("Onboarding discovery failed")

    technologies: dict[FindingCategory, list[Technology]] = {
        FindingCategory.LANGUAGE: [],
        FindingCategory.FRAMEWORK: [],
    }
    for finding in inspection.findings:
        if finding.category not in technologies or finding.detection_state not in (
            DetectionState.DETECTED,
            DetectionState.INFERRED,
        ):
            continue
        evidence = _evidence(finding.evidence)
        technologies[finding.category].append(
            Technology(
                _printable(finding.subject),
                "detected"
                if finding.detection_state is DetectionState.DETECTED
                else "candidate",
                evidence[:8],
                len(evidence),
            )
        )

    diagnostics = set()
    for item in (
        *inspection.diagnostics,
        *(d for r in inspection.analyzer_results for d in r.diagnostics),
    ):
        # Free-form diagnostic messages may include raw source, paths or secrets.
        code = (
            item.code
            if re.fullmatch(r"[a-z0-9_.-]{1,100}", item.code)
            else "inspection.diagnostic"
        )
        severity = item.severity if item.severity in _SEVERITIES else "warning"
        diagnostics.add(OnboardingDiagnostic(code, severity, _relative(item.path)))
    for source, projection in (
        ("entry_points", result.entry_points),
        ("workflows", result.workflows),
    ):
        diagnostics.update(
            OnboardingDiagnostic(
                f"onboard.{source}.file_skipped", "warning", _relative(name)
            )
            for name in projection.skipped
        )
        if projection.truncated:
            diagnostics.add(
                OnboardingDiagnostic(f"onboard.{source}.limit_reached", "warning")
            )

    entries = tuple(
        replace(row, target=_printable(row.target), evidence=evidence)
        for row in result.entry_points.entries
        if (evidence := _evidence(row.evidence))
    )
    commands = tuple(
        replace(row, evidence=_evidence(row.evidence))
        for row in result.workflows.commands
        if (row.cwd == "." or _relative(row.cwd) is not None)
        and (row.argv is None or all(_printable(arg) == arg for arg in row.argv))
    )
    return OnboardingReport(
        name=_printable(inspection.summary.name or "repository"),
        generated_at=inspection.generated_at,
        status=AnalysisStatus.PARTIAL
        if (
            inspection.status is AnalysisStatus.PARTIAL
            or any(item.severity != "info" for item in diagnostics)
        )
        else AnalysisStatus.COMPLETE,
        file_count=inspection.structure.file_count,
        directory_count=inspection.structure.directory_count,
        languages=tuple(technologies[FindingCategory.LANGUAGE]),
        frameworks=tuple(technologies[FindingCategory.FRAMEWORK]),
        entry_points=entries,
        commands=commands,
        directories=tuple(
            path
            for path in inspection.structure.top_level_directories
            if _relative(path) is not None
        ),
        config_files=tuple(
            path
            for path in result.inventory.files
            if _key_file(path) and _relative(path) is not None
        ),
        diagnostics=tuple(
            sorted(
                diagnostics,
                key=lambda item: (item.severity, item.code, item.path or ""),
            )
        ),
    )


def onboarding_to_json(report: OnboardingReport) -> str:
    """Serialize one report. Diagnostic details belong on stderr."""
    data = {
        "schema_version": ONBOARD_SCHEMA_VERSION,
        "generated_at": report.generated_at,
        "status": report.status.value,
        "repository": {
            "name": report.name,
            "file_count": report.file_count,
            "directory_count": report.directory_count,
        },
        "languages": [asdict(item) for item in report.languages],
        "frameworks": [asdict(item) for item in report.frameworks],
        "entry_points": [asdict(item) for item in report.entry_points],
        "commands": [asdict(item) for item in report.commands],
        "structure": {
            "directories": report.directories,
            "config_files": report.config_files,
        },
        "diagnostic_counts": report.diagnostic_counts(),
    }
    return json.dumps(data, indent=2) + "\n"
