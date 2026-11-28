"""Canonical JSON for diagnostics schema 1.0."""

import json
from dataclasses import asdict

from .models import (
    SCHEMA_VERSION,
    Coverage,
    DiagnosticsReport,
    Evidence,
    IssueDescription,
    Outcome,
    Reason,
    ReportStatus,
    RepositoryIdentity,
    RepositoryIssue,
    RuleOutcome,
    Severity,
)


class ReportDecodeError(ValueError):
    """A payload does not satisfy the diagnostics schema."""


def to_dict(report: DiagnosticsReport) -> dict:
    outcomes = []
    for outcome in report.outcomes:
        findings = []
        for issue in outcome.findings:
            description = asdict(issue.description)
            description["severity"] = issue.description.severity.value
            findings.append(
                {
                    "rule_id": issue.rule_id,
                    "category": issue.category,
                    "occurrence_id": issue.occurrence_id,
                    **description,
                    "evidence": [asdict(item) for item in issue.evidence],
                }
            )
        outcomes.append(
            {
                "rule_id": outcome.rule_id,
                "category": outcome.category,
                "outcome": outcome.outcome.value,
                "reason": outcome.reason.value,
                "findings": findings,
                "scope_evidence": [asdict(item) for item in outcome.scope_evidence],
            }
        )
    return {
        "schema_version": report.schema_version,
        "repository": asdict(report.repository),
        "status": report.status.value,
        "coverage": report.coverage.value,
        "is_clean": report.is_clean,
        "outcome_counts": {
            key.value: count for key, count in report.outcome_counts.items()
        },
        "severity_counts": {
            key.value: count for key, count in report.severity_counts.items()
        },
        "outcomes": outcomes,
    }


def to_json(report: DiagnosticsReport) -> str:
    return json.dumps(to_dict(report), ensure_ascii=False, indent=2) + "\n"


def _fields(raw: object, *names: str) -> dict:
    if type(raw) is not dict or raw.keys() != set(names):
        raise ValueError("Invalid diagnostics fields")
    return raw


def _array(raw: object) -> list:
    if type(raw) is not list:
        raise ValueError("Expected diagnostics array")
    return raw


def _decode_evidence(raw: object) -> tuple[Evidence, ...]:
    return tuple(
        Evidence(**_fields(item, "path", "line", "key")) for item in _array(raw)
    )


def _decode_issue(raw: object) -> RepositoryIssue:
    data = _fields(
        raw,
        "rule_id",
        "category",
        "occurrence_id",
        "kind",
        "severity",
        "title",
        "problem",
        "recommendation",
        "evidence",
    )
    description = IssueDescription(
        data["kind"],
        Severity(data["severity"]),
        data["title"],
        data["problem"],
        data["recommendation"],
    )
    issue = RepositoryIssue(
        data["rule_id"],
        data["category"],
        description,
        _decode_evidence(data["evidence"]),
    )
    if (
        type(data["occurrence_id"]) is not str
        or data["occurrence_id"] != issue.occurrence_id
    ):
        raise ValueError("Invalid diagnostics occurrence ID")
    return issue


def _decode_outcome(raw: object) -> RuleOutcome:
    data = _fields(
        raw, "rule_id", "category", "outcome", "reason", "findings", "scope_evidence"
    )
    return RuleOutcome(
        data["rule_id"],
        data["category"],
        Outcome(data["outcome"]),
        Reason(data["reason"]),
        tuple(_decode_issue(item) for item in _array(data["findings"])),
        _decode_evidence(data["scope_evidence"]),
    )


def _check_counts(raw: object, expected: dict) -> None:
    counts = _fields(raw, *(key.value for key in expected))
    if any(
        type(counts[key.value]) is not int or counts[key.value] != value
        for key, value in expected.items()
    ):
        raise ValueError("Invalid diagnostics counts")


def from_dict(raw: object) -> DiagnosticsReport:
    try:
        data = _fields(
            raw,
            "schema_version",
            "repository",
            "status",
            "coverage",
            "is_clean",
            "outcome_counts",
            "severity_counts",
            "outcomes",
        )
        version = data["schema_version"]
        if type(version) is not str or version != SCHEMA_VERSION:
            raise ReportDecodeError("Unsupported diagnostics schema version")
        report = DiagnosticsReport(
            RepositoryIdentity(**_fields(data["repository"], "label")),
            Coverage(data["coverage"]),
            tuple(_decode_outcome(item) for item in _array(data["outcomes"])),
            version,
        )
        if (
            ReportStatus(data["status"]) is not report.status
            or data["is_clean"] is not report.is_clean
        ):
            raise ValueError("Invalid diagnostics status")
        _check_counts(data["outcome_counts"], report.outcome_counts)
        _check_counts(data["severity_counts"], report.severity_counts)
    except ReportDecodeError:
        raise
    except (TypeError, ValueError, RecursionError):
        raise ReportDecodeError("Invalid diagnostics report") from None
    return report


def _unique_fields(pairs: list[tuple[str, object]]) -> dict:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate diagnostics field")
    return result


def from_json(text: str | bytes) -> DiagnosticsReport:
    try:
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        data = json.loads(text, object_pairs_hook=_unique_fields)
    except (TypeError, ValueError, RecursionError):
        raise ReportDecodeError("Invalid diagnostics JSON") from None
    return from_dict(data)
