"""Immutable values for the independent diagnostics report contract."""

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

SCHEMA_VERSION = "1.0"
_SLUG = re.compile(r"[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*", re.ASCII)
_SECRET = re.compile(
    r"(?i)(?:\b(?:gh[pousr]_|github_pat_|sk-|xox[baprs]-|AIza)[a-z0-9_-]{12,}"
    r"|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?:password|passwd|token|api[_-]?key|secret)\s*[:=]\s*\S"
    r"|://[^/\s]+:[^/\s]+@)"
)
_SENSITIVE_NAMES = {
    ".aws",
    ".azure",
    ".docker",
    ".git",
    ".gnupg",
    ".kube",
    ".ssh",
    ".git-credentials",
    ".netrc",
    ".npmrc",
    ".pgpass",
    ".pypirc",
    ".credentials",
    ".secrets",
    "_netrc",
    "credentials",
    "secrets",
    "id_rsa",
    "id_ed25519",
}
_DEVICES = re.compile(r"(?i)(?:con|prn|aux|nul|com[0-9¹²³]|lpt[0-9¹²³])")


def _identifier(value: str) -> None:
    if type(value) is not str or len(value) > 96 or not _SLUG.fullmatch(value):
        raise ValueError("Invalid diagnostics identifier")
    if _SECRET.search(value):
        raise ValueError("Unsafe diagnostics identifier")


def _safe_text(value: str, maximum: int) -> bool:
    return (
        type(value) is str
        and 0 < len(value) <= maximum
        and value == value.strip()
        and not any(char in "[]<>&" or char == chr(96) for char in value)
        and not any(
            unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
            for char in value
        )
        and not _SECRET.search(value)
    )


def sensitive_path(path: str) -> bool:
    for part in path.casefold().split("/"):
        if (
            part.startswith(".env")
            or part in _SENSITIVE_NAMES
            or part.split(".")[0] in _SENSITIVE_NAMES
            or part.endswith((".pem", ".key", ".p12", ".pfx", ".kdbx", ".jks"))
        ):
            return True
    return False


def safe_evidence_path(path: str) -> bool:
    """Allow only unambiguous, portable locations suitable for both surfaces."""
    if not _safe_text(path, 1024) or any(char in path for char in '\\:*?"|'):
        return False
    if sensitive_path(path):
        return False
    for part in path.casefold().split("/"):
        stem = part.split(".")[0]
        if (
            not part
            or part.endswith((".", " "))
            or part != part.strip()
            or _DEVICES.fullmatch(stem)
        ):
            return False
    return True


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Outcome(StrEnum):
    PASS = "pass"
    FINDING = "finding"
    UNKNOWN = "unknown"
    NOT_CHECKED = "not_checked"
    NOT_APPLICABLE = "not_applicable"
    FAILED = "failed"


class Reason(StrEnum):
    CONDITION_ABSENT = "condition_absent"
    CONDITION_PROVED = "condition_proved"
    SCOPE_UNCLEAR = "scope_unclear"
    EVIDENCE_MISSING = "evidence_missing"
    COVERAGE_INCOMPLETE = "coverage_incomplete"
    LIMIT_REACHED = "limit_reached"
    CHECK_SKIPPED = "check_skipped"
    OUTSIDE_SCOPE = "outside_scope"
    RULE_CRASHED = "rule_crashed"
    INVALID_RESULT = "invalid_result"


_REASONS = {
    Outcome.PASS: {Reason.CONDITION_ABSENT},
    Outcome.FINDING: {Reason.CONDITION_PROVED},
    Outcome.UNKNOWN: {
        Reason.SCOPE_UNCLEAR,
        Reason.EVIDENCE_MISSING,
        Reason.COVERAGE_INCOMPLETE,
        Reason.LIMIT_REACHED,
    },
    Outcome.NOT_CHECKED: {Reason.CHECK_SKIPPED, Reason.LIMIT_REACHED},
    Outcome.NOT_APPLICABLE: {Reason.OUTSIDE_SCOPE},
    Outcome.FAILED: {Reason.RULE_CRASHED, Reason.INVALID_RESULT},
}


class ReportStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class Coverage(StrEnum):
    COMPLETE = "complete"
    INVENTORY_INCOMPLETE = "inventory_incomplete"
    INSPECTION_INCOMPLETE = "inspection_incomplete"
    LIMIT_REACHED = "limit_reached"
    ROOT_UNAVAILABLE = "root_unavailable"
    DISCOVERY_FAILED = "discovery_failed"


@dataclass(frozen=True, slots=True)
class RepositoryIdentity:
    """An opaque label derived from the checkout basename, if known."""

    label: str | None

    def __post_init__(self) -> None:
        if self.label is not None and (
            type(self.label) is not str or not re.fullmatch(r"[a-f0-9]{64}", self.label)
        ):
            raise ValueError("Invalid repository label")


@dataclass(frozen=True, slots=True)
class Evidence:
    path: str
    line: int | None = None
    key: str | None = None

    def __post_init__(self) -> None:
        if not safe_evidence_path(self.path):
            raise ValueError("Unsafe diagnostics evidence path")
        if self.line is not None and (
            type(self.line) is not int or not 1 <= self.line <= 2**31 - 1
        ):
            raise ValueError("Invalid diagnostics line")
        if self.key is not None:
            _identifier(self.key)
            if self.line is not None:
                raise ValueError("Evidence accepts one location selector")

    def sort_key(self) -> tuple[str, int, str]:
        return self.path, self.line or 0, self.key or ""


def _evidence(items: tuple[Evidence, ...]) -> tuple[Evidence, ...]:
    if type(items) is not tuple or not all(type(item) is Evidence for item in items):
        raise ValueError("Invalid diagnostics evidence")
    return tuple(sorted(set(items), key=Evidence.sort_key))


@dataclass(frozen=True, slots=True)
class IssueDescription:
    """Fixed rule-authored text for one kind of static issue."""

    kind: str
    severity: Severity
    title: str
    problem: str
    recommendation: str

    def __post_init__(self) -> None:
        _identifier(self.kind)
        if type(self.severity) is not Severity:
            raise ValueError("Invalid diagnostics severity")
        if not (
            _safe_text(self.title, 120)
            and _safe_text(self.problem, 400)
            and _safe_text(self.recommendation, 400)
        ):
            raise ValueError("Unsafe diagnostics description")


@dataclass(frozen=True, slots=True)
class RepositoryIssue:
    rule_id: str
    category: str
    description: IssueDescription
    evidence: tuple[Evidence, ...]

    def __post_init__(self) -> None:
        _identifier(self.rule_id)
        _identifier(self.category)
        if type(self.description) is not IssueDescription or not self.evidence:
            raise ValueError("A repository issue requires a description and evidence")
        object.__setattr__(self, "evidence", _evidence(self.evidence))

    @property
    def occurrence_id(self) -> str:
        identity = (
            self.rule_id,
            self.description.kind,
            [e.sort_key() for e in self.evidence],
        )
        return hashlib.sha256(
            json.dumps(identity, separators=(",", ":")).encode("ascii")
        ).hexdigest()

    def sort_key(self) -> tuple:
        return (
            list(Severity).index(self.description.severity),
            self.rule_id,
            tuple(e.sort_key() for e in self.evidence),
            self.description.kind,
        )


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    rule_id: str
    category: str
    outcome: Outcome
    reason: Reason
    findings: tuple[RepositoryIssue, ...] = ()
    scope_evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.rule_id)
        _identifier(self.category)
        if (
            type(self.outcome) is not Outcome
            or type(self.reason) is not Reason
            or self.reason not in _REASONS[self.outcome]
        ):
            raise ValueError("Invalid diagnostics outcome or reason")
        if type(self.findings) is not tuple or bool(self.findings) != (
            self.outcome is Outcome.FINDING
        ):
            raise ValueError("Findings require a finding outcome")
        if bool(self.scope_evidence) != (self.outcome is Outcome.NOT_APPLICABLE):
            raise ValueError("Not applicable requires positive scope evidence")
        object.__setattr__(self, "scope_evidence", _evidence(self.scope_evidence))
        unique = {}
        for issue in self.findings:
            if type(issue) is not RepositoryIssue or (
                issue.rule_id,
                issue.category,
            ) != (self.rule_id, self.category):
                raise ValueError("Finding does not belong to rule")
            if unique.setdefault(issue.occurrence_id, issue) != issue:
                raise ValueError("Conflicting repository issue occurrence")
        object.__setattr__(
            self,
            "findings",
            tuple(sorted(unique.values(), key=RepositoryIssue.sort_key)),
        )


@dataclass(frozen=True, slots=True)
class DiagnosticsReport:
    repository: RepositoryIdentity
    coverage: Coverage
    outcomes: tuple[RuleOutcome, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            type(self.schema_version) is not str
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ValueError("Unsupported diagnostics schema version")
        if (
            type(self.repository) is not RepositoryIdentity
            or type(self.coverage) is not Coverage
        ):
            raise ValueError("Invalid diagnostics report header")
        if (self.coverage is Coverage.ROOT_UNAVAILABLE) != (
            self.repository.label is None
        ):
            raise ValueError("Repository label does not match root coverage")
        if type(self.outcomes) is not tuple or not all(
            type(item) is RuleOutcome for item in self.outcomes
        ):
            raise ValueError("Invalid report outcomes")
        if self.status is ReportStatus.FAILED and self.outcomes:
            raise ValueError("Fatal discovery prevents rule evaluation")
        if len({item.rule_id for item in self.outcomes}) != len(self.outcomes):
            raise ValueError("Duplicate rule outcome")
        object.__setattr__(
            self,
            "outcomes",
            tuple(sorted(self.outcomes, key=lambda item: item.rule_id)),
        )

    @property
    def status(self) -> ReportStatus:
        if self.coverage in {Coverage.ROOT_UNAVAILABLE, Coverage.DISCOVERY_FAILED}:
            return ReportStatus.FAILED
        if self.coverage is not Coverage.COMPLETE or any(
            item.outcome in {Outcome.UNKNOWN, Outcome.NOT_CHECKED, Outcome.FAILED}
            for item in self.outcomes
        ):
            return ReportStatus.PARTIAL
        return ReportStatus.COMPLETE

    @property
    def findings(self) -> tuple[RepositoryIssue, ...]:
        return tuple(
            sorted(
                (issue for item in self.outcomes for issue in item.findings),
                key=RepositoryIssue.sort_key,
            )
        )

    @property
    def outcome_counts(self) -> dict[Outcome, int]:
        counts = dict.fromkeys(Outcome, 0)
        for item in self.outcomes:
            counts[item.outcome] += 1
        return counts

    @property
    def severity_counts(self) -> dict[Severity, int]:
        counts = dict.fromkeys(Severity, 0)
        for issue in self.findings:
            counts[issue.description.severity] += 1
        return counts

    @property
    def is_clean(self) -> bool:
        return (
            self.status is ReportStatus.COMPLETE
            and bool(self.outcome_counts[Outcome.PASS])
            and not self.findings
        )
