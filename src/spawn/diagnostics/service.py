"""Read-only diagnostics composition over one bounded inspection inventory."""

import hashlib
import warnings
from pathlib import Path

from spawn.inspection._reading import repository_reads
from spawn.inspection.discovery import (
    DiscoveryLimitExceeded,
    discover_repository,
    validate_inspection_root,
)
from spawn.inspection.exceptions import InspectionError
from spawn.inspection.models import AnalysisStatus
from spawn.inspection.orchestrator import ANALYZERS, _inspect_inventory

from .models import (
    Coverage,
    DiagnosticsReport,
    Outcome,
    Reason,
    RepositoryIdentity,
    RuleOutcome,
    safe_evidence_path,
    sensitive_path,
)
from .rules import (
    RULES,
    Rule,
    RuleContext,
    WorkLimits,
    _Budget,
    _Inputs,
    _LimitReached,
    _validate_registry,
)

_MAX_ENTRIES = 10_000
_AGGREGATE = WorkLimits(files=512, bytes=128_000_128, work=100_000)


def _limited(rule: Rule, outcome: Outcome = Outcome.NOT_CHECKED) -> RuleOutcome:
    return RuleOutcome(rule.rule_id, rule.category, outcome, Reason.LIMIT_REACHED)


def _evaluate(rule: Rule, context: RuleContext, budget: _Budget) -> RuleOutcome:
    if budget.exhausted:
        return _limited(rule)
    try:
        context.spend()
        result = rule.evaluate(context)
    except _LimitReached:
        return _limited(rule, Outcome.UNKNOWN)
    except OSError as exc:
        # The active shared reader raises its private budget signal as an
        # OSError subclass. Keep generic rule I/O failures isolated.
        if type(exc).__name__ == "_LimitReached":
            return _limited(rule, Outcome.UNKNOWN)
        return RuleOutcome(
            rule.rule_id, rule.category, Outcome.FAILED, Reason.RULE_CRASHED
        )
    except Exception:
        return RuleOutcome(
            rule.rule_id, rule.category, Outcome.FAILED, Reason.RULE_CRASHED
        )

    try:
        if type(result) is not RuleOutcome or (result.rule_id, result.category) != (
            rule.rule_id,
            rule.category,
        ):
            raise ValueError("Result does not belong to rule")
        if context._budget.exhausted or budget.exhausted:
            return _limited(rule, Outcome.UNKNOWN)
        _validate_evidence(rule, context, result)
        if context._gap is not None and result.outcome in {
            Outcome.PASS,
            Outcome.FINDING,
            Outcome.NOT_APPLICABLE,
        }:
            return RuleOutcome(
                rule.rule_id, rule.category, Outcome.UNKNOWN, context._gap
            )
        if result.outcome is Outcome.PASS and not context._checked:
            return RuleOutcome(
                rule.rule_id, rule.category, Outcome.UNKNOWN, Reason.EVIDENCE_MISSING
            )
    except _LimitReached:
        return _limited(rule, Outcome.UNKNOWN)
    except Exception:
        return RuleOutcome(
            rule.rule_id, rule.category, Outcome.FAILED, Reason.INVALID_RESULT
        )
    return result


def _validate_evidence(rule: Rule, context: RuleContext, result: RuleOutcome) -> None:
    context.spend(1 + len(result.findings))
    evidence_groups = [result.scope_evidence]
    for issue in result.findings:
        if issue.description not in rule.descriptions:
            raise ValueError("Finding description is not authorized by the rule")
        evidence_groups.append(issue.evidence)
    for group in evidence_groups:
        context.spend(1 + len(group))
        if any(
            item.path not in context._inputs.members
            or (item.key is not None and item.key not in rule.evidence_keys)
            for item in group
        ):
            raise ValueError("Evidence is outside the rule's allowed inputs")


def run_diagnostics(path: str | Path) -> DiagnosticsReport:
    """Run the internal registry against a validated local checkout."""
    return _run(path, RULES)


def _run(
    path: str | Path,
    rules: tuple[Rule, ...],
    *,
    max_entries: int = _MAX_ENTRIES,
    limits: WorkLimits = _AGGREGATE,
) -> DiagnosticsReport:
    rules = _validate_registry(rules)
    try:
        target = validate_inspection_root(path)
    except InspectionError:
        return DiagnosticsReport(RepositoryIdentity(None), Coverage.ROOT_UNAVAILABLE)
    label = hashlib.sha256(
        target.path.name.encode("utf-8", "surrogatepass")
    ).hexdigest()
    repository = RepositoryIdentity(label)
    try:
        inventory = discover_repository(
            target, max_entries=max_entries, include_path=safe_evidence_path
        )
    except DiscoveryLimitExceeded:
        return DiagnosticsReport(
            repository, Coverage.LIMIT_REACHED, tuple(map(_limited, rules))
        )
    except InspectionError:
        return DiagnosticsReport(repository, Coverage.DISCOVERY_FAILED)
    if any(item.fatal for item in inventory.diagnostics):
        return DiagnosticsReport(repository, Coverage.DISCOVERY_FAILED)

    unsafe = tuple(
        path
        for path in inventory.skipped
        if not sensitive_path(path) and not safe_evidence_path(path)
    )
    members = frozenset(inventory.files)
    budget = _Budget(limits)

    def charge(relative: str, size: int) -> None:
        budget.charge(files=1, size=size)
        if relative not in members:
            raise OSError("Diagnostics read requires a safe inventory member")

    with repository_reads(target.path, charge=charge), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        inspection = _inspect_inventory(target, inventory, ANALYZERS)
        inputs = _Inputs(
            target.path,
            inventory.files,
            members,
            inventory.skipped,
            (*unsafe, *(item.path for item in inventory.diagnostics)),
            inspection,
        )
        outcomes = tuple(
            _evaluate(rule, RuleContext(inputs, rule.limits, budget), budget)
            for rule in rules
        )

    coverage = Coverage.COMPLETE
    if budget.exhausted:
        coverage = Coverage.LIMIT_REACHED
    elif unsafe or any(
        item.severity in {"warning", "error"} for item in inventory.diagnostics
    ):
        coverage = Coverage.INVENTORY_INCOMPLETE
    elif inspection.status is not AnalysisStatus.COMPLETE:
        coverage = Coverage.INSPECTION_INCOMPLETE
    return DiagnosticsReport(repository, coverage, outcomes)
