"""Shared inputs and outcome construction for the built-in checks."""

import re
import tomllib
from collections.abc import Callable

from ..models import (
    Evidence,
    IssueDescription,
    Outcome,
    Reason,
    RepositoryIssue,
    RuleOutcome,
    Severity,
    safe_evidence_path,
)
from ..rules import Rule, RuleContext

_LITERAL = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", re.ASCII)
_PROJECT_MARKERS = {"pyproject.toml", "setup.py", "setup.cfg", "Pipfile"}
_TEXT_LIMIT = 64 * 1024


class Unclear(Exception):
    def __init__(self, reason: Reason = Reason.SCOPE_UNCLEAR):
        self.reason = reason


def table(value: object) -> dict:
    if not isinstance(value, dict):
        raise Unclear(Reason.EVIDENCE_MISSING)
    return value


def read(context: RuleContext, path: str) -> str:
    text = context.read_text(path, limit=_TEXT_LIMIT)
    if text is None:
        raise Unclear(Reason.EVIDENCE_MISSING)
    return text


def kind(context: RuleContext, path: str) -> str:
    if value := context.path_kind(path):
        return value
    raise Unclear(Reason.COVERAGE_INCOMPLETE)


def literal(value: object) -> str:
    if (
        not isinstance(value, str)
        or value.startswith("-")
        or not safe_evidence_path(value)
        or not _LITERAL.fullmatch(value)
    ):
        raise Unclear()
    return value


def project(context: RuleContext) -> dict:
    if not context.inventory_covers() or kind(context, "pyproject.toml") != "file":
        raise Unclear()
    if any(
        "/" in path and path.rsplit("/", 1)[1].casefold() in _PROJECT_MARKERS
        for path in context.files
    ):
        raise Unclear()
    doc = tomllib.loads(read(context, "pyproject.toml"))
    if "project" not in doc or not isinstance(table(doc["project"]).get("name"), str):
        raise Unclear()
    tools = table(doc.get("tool", {}))
    if "workspace" in table(tools.get("uv", {})):
        raise Unclear()
    return doc


def check(
    rule_id: str,
    category: str,
    title: str,
    problem: str,
    recommendation: str,
    evaluate: Callable[[RuleContext, dict], tuple[tuple[Evidence, ...], ...]],
    *,
    keys: tuple[str, ...] = (),
) -> Rule:
    description = IssueDescription(
        "configuration", Severity.WARNING, title, problem, recommendation
    )

    def run(context: RuleContext) -> RuleOutcome:
        try:
            groups = evaluate(context, project(context))
        except Unclear as exc:
            return RuleOutcome(rule_id, category, Outcome.UNKNOWN, exc.reason)
        except (tomllib.TOMLDecodeError, SyntaxError, RecursionError):
            return RuleOutcome(
                rule_id, category, Outcome.UNKNOWN, Reason.EVIDENCE_MISSING
            )
        if groups == ():
            return RuleOutcome(rule_id, category, Outcome.PASS, Reason.CONDITION_ABSENT)
        if groups == ((),):
            return RuleOutcome(
                rule_id,
                category,
                Outcome.NOT_APPLICABLE,
                Reason.OUTSIDE_SCOPE,
                scope_evidence=(Evidence("pyproject.toml"),),
            )
        return RuleOutcome(
            rule_id,
            category,
            Outcome.FINDING,
            Reason.CONDITION_PROVED,
            tuple(
                RepositoryIssue(rule_id, category, description, group)
                for group in groups
            ),
        )

    return Rule(rule_id, category, run, (description,), keys)


OUTSIDE_SCOPE: tuple[tuple[Evidence, ...], ...] = ((),)
