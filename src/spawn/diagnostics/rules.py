"""Explicit registry and bounded inputs for internal rules."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from spawn.inspection import _reading
from spawn.inspection.discovery import DEFAULT_EXCLUDED_DIRECTORIES
from spawn.inspection.models import (
    AnalysisStatus,
    DetectionState,
    FindingCategory,
    InspectionReport,
)

from .models import (
    IssueDescription,
    Reason,
    RuleOutcome,
    _identifier,
    safe_evidence_path,
)


@dataclass(frozen=True, slots=True)
class WorkLimits:
    files: int
    bytes: int
    work: int

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 1
            for value in (self.files, self.bytes, self.work)
        ):
            raise ValueError("Invalid diagnostics work limits")


class _LimitReached(OSError):
    """Budget signal also handled by the existing inspection readers."""


class _Budget:
    def __init__(self, limits: WorkLimits):
        self.files = limits.files
        self.bytes = limits.bytes
        self.work = limits.work
        self.exhausted = False

    def charge(self, *, files: int = 0, size: int = 0, work: int = 1) -> None:
        if (
            self.exhausted
            or files > self.files
            or size > self.bytes
            or work > self.work
        ):
            self.exhausted = True
            raise _LimitReached("Diagnostics work limit reached")
        self.files -= files
        self.bytes -= size
        self.work -= work


@dataclass(frozen=True, slots=True)
class _Inputs:
    root: Path
    files: tuple[str, ...]
    members: frozenset[str]
    directories: frozenset[str]
    folded_paths: frozenset[str]
    skipped: tuple[str, ...]
    gaps: tuple[str | None, ...]
    inspection: InspectionReport


class RuleContext:
    """Trusted rules use this interface for reads and coverage checks."""

    def __init__(self, inputs: _Inputs, limits: WorkLimits, aggregate: _Budget):
        self._inputs = inputs
        self._budget = _Budget(limits)
        self._aggregate = aggregate
        self._gap: Reason | None = None
        self._checked = False

    def spend(self, units: int = 1) -> None:
        """Charge custom bounded work, such as iteration over parsed records."""
        if type(units) is not int or units < 1:
            raise ValueError("Invalid diagnostics work charge")
        self._budget.charge(work=units)
        self._aggregate.charge(work=units)

    @property
    def files(self) -> tuple[str, ...]:
        """List available inventory members. Use inventory_covers for absence."""
        self.spend(1 + len(self._inputs.files))
        return self._inputs.files

    def inventory_covers(self, prefix: str | None = None) -> bool:
        """Check discovery coverage for one file/subtree or the inventory scope."""
        if prefix is not None and not safe_evidence_path(prefix):
            raise ValueError("Invalid diagnostics coverage scope")
        self.spend(1 + len(self._inputs.gaps) + len(self._inputs.skipped))
        if prefix is not None:
            prefix = prefix.casefold()

        def overlaps(path: str | None) -> bool:
            if path is None or prefix is None:
                return True
            path = path.casefold()
            return (
                path == prefix
                or path.startswith(prefix + "/")
                or prefix.startswith(path + "/")
            )

        covered = not any(overlaps(path) for path in self._inputs.gaps)
        if prefix is not None:
            covered = covered and not any(
                prefix == path.casefold() or prefix.startswith(path.casefold() + "/")
                for path in self._inputs.skipped
            )
        self._checked |= covered
        if not covered:
            self._gap = Reason.COVERAGE_INCOMPLETE
        return covered

    def path_kind(self, path: str) -> str | None:
        """Return file, directory, or covered absence. Unclear paths return None."""
        self.spend()
        if not safe_evidence_path(path) or any(
            part.casefold() in DEFAULT_EXCLUDED_DIRECTORIES for part in path.split("/")
        ):
            return None
        if path in self._inputs.members:
            return "file"
        if path in self._inputs.directories:
            return "directory"
        # A different spelling is ambiguous across filesystem case semantics,
        # including when only an ancestor has a different spelling.
        prefix = path
        while prefix:
            self.spend()
            if (
                prefix.casefold() in self._inputs.folded_paths
                and prefix not in self._inputs.directories
                and prefix not in self._inputs.members
            ):
                return None
            prefix = prefix.rpartition("/")[0]
        return "missing" if self.inventory_covers(path) else None

    def read_text(
        self, path: str, *, limit: int = _reading.MAX_FILE_SIZE
    ) -> str | None:
        """Read a safe inventory member, with no content on incomplete reads."""
        if type(limit) is not int or not 1 <= limit <= _reading.MAX_FILE_SIZE:
            raise ValueError("Invalid diagnostics file size limit")
        self.spend()
        self._budget.charge(files=1, size=limit + 1, work=0)
        # The active repository reader reserves the aggregate budget once.
        if not safe_evidence_path(path) or path not in self._inputs.members:
            self._gap = Reason.EVIDENCE_MISSING
            return None
        try:
            # Reuse the inspection composition's active handle and bounded
            # cache instead of opening an independent repository reader.
            text = _reading.read_inventory_text(self._inputs.root, path, limit)
        except _LimitReached:
            raise
        except (OSError, UnicodeError):
            text = None
        if text is None:
            self._gap = Reason.EVIDENCE_MISSING
        else:
            self._checked = True
        return text

    def has_inspection_fact(self, category: FindingCategory, subject: str) -> bool:
        """Query a detected static fact. Absence requires complete inspection."""
        inspection = self._inputs.inspection
        self.spend(1 + len(inspection.findings))
        found = any(
            item.category is category
            and item.subject == subject
            and item.detection_state is DetectionState.DETECTED
            for item in inspection.findings
        )
        if not found and inspection.status is not AnalysisStatus.COMPLETE:
            self._gap = Reason.COVERAGE_INCOMPLETE
        # A missed detection does not prove absence of the underlying condition.
        return found


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    category: str
    evaluate: Callable[[RuleContext], RuleOutcome]
    descriptions: tuple[IssueDescription, ...] = ()
    evidence_keys: tuple[str, ...] = ()
    limits: WorkLimits = WorkLimits(files=32, bytes=8_000_008, work=25_000)

    def __post_init__(self) -> None:
        _identifier(self.rule_id)
        _identifier(self.category)
        if not callable(self.evaluate) or type(self.limits) is not WorkLimits:
            raise ValueError("Invalid diagnostics rule")
        if type(self.descriptions) is not tuple or any(
            type(item) is not IssueDescription for item in self.descriptions
        ):
            raise ValueError("Invalid diagnostics descriptions")
        if len({item.kind for item in self.descriptions}) != len(self.descriptions):
            raise ValueError("Duplicate diagnostics issue kind")
        if type(self.evidence_keys) is not tuple:
            raise ValueError("Invalid diagnostics evidence keys")
        for key in self.evidence_keys:
            _identifier(key)


def _validate_registry(rules: tuple[Rule, ...]) -> tuple[Rule, ...]:
    if type(rules) is not tuple or any(type(rule) is not Rule for rule in rules):
        raise ValueError("Invalid diagnostics registry")
    if len({rule.rule_id for rule in rules}) != len(rules):
        raise ValueError("Duplicate diagnostics rule ID")
    return tuple(sorted(rules, key=lambda rule: rule.rule_id))
