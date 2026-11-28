"""Terminal report for the repository diagnose command."""

import os
import sys
from pathlib import Path

from rich.console import Console
from rich.rule import Rule
from rich.text import Text

from spawn.diagnostics.models import (
    Coverage,
    DiagnosticsReport,
    Evidence,
    Outcome,
    ReportStatus,
    Severity,
    safe_evidence_path,
)
from spawn.utils.theme import ACCENT_COLOR, BORDER_COLOR, ERROR_COLOR, WARNING_COLOR

_BRAND = f"bold {BORDER_COLOR}"
_HEADING = f"bold {ACCENT_COLOR}"
_GROUPS = {
    Severity.ERROR: ("ERRORS", ERROR_COLOR),
    Severity.WARNING: ("WARNINGS", WARNING_COLOR),
    Severity.INFO: ("INFORMATION", ACCENT_COLOR),
}
_COVERAGE = {
    Coverage.INVENTORY_INCOMPLETE: "Repository inventory is incomplete.",
    Coverage.INSPECTION_INCOMPLETE: "Inspection evidence is incomplete.",
    Coverage.LIMIT_REACHED: "An analysis limit was reached.",
}


def diagnose_console(no_color: bool) -> Console:
    plain = no_color or "NO_COLOR" in os.environ or not sys.stdout.isatty()
    return Console(file=sys.stdout, force_terminal=False if plain else None)


def _display(console: Console, value: str) -> str:
    # Preserve printable Unicode when supported by the destination stream.
    return value.encode(console.encoding, "backslashreplace").decode(console.encoding)


def _name(path: str) -> str:
    name = Path.cwd().name if path == "." else Path(path).name
    return name if len(name) <= 100 and safe_evidence_path(name) else "Repository"


def _reference(console: Console, item: Evidence, indent: str) -> None:
    location = item.path
    if item.line is not None:
        location += f":{item.line}"
    if item.key is not None:
        location += f" [{item.key}]"
    # A terminal can wrap long references without inserting breaks into paths.
    console.print(Text(indent + _display(console, location)), soft_wrap=True)


def _detail(console: Console, value: str) -> None:
    text = Text(_display(console, value))
    for line in text.wrap(console, max(1, console.width - 4), overflow="fold"):
        line.rstrip()
        console.print(Text("    ").append_text(line))


def render_diagnose(
    report: DiagnosticsReport, path: str, console: Console, *, verbose: bool = False
) -> None:
    """Render findings and coverage using literal Rich Text."""
    counts = report.outcome_counts
    evaluated = counts[Outcome.PASS] + counts[Outcome.FINDING]
    findings = report.findings
    partial = report.status is ReportStatus.PARTIAL
    ascii_only = console.options.ascii_only or console.width <= 60
    console.print(Text(("SPAWN" if ascii_only else "⚡ SPAWN") + " / DIAGNOSE", _BRAND))
    console.print()
    console.print(Text(_display(console, _name(path)), style="bold"))
    findings_label = "finding" if len(findings) == 1 else "findings"
    checks_label = "check" if evaluated == 1 else "checks"
    console.print(
        Text(f"{len(findings)} {findings_label} | {evaluated} {checks_label} evaluated")
    )
    if partial:
        console.print(Text("PARTIAL ANALYSIS", style=f"bold {WARNING_COLOR}"))
    console.print(Rule(characters="-" if ascii_only else "━", style=BORDER_COLOR))

    heading = None
    for issue in findings:
        description = issue.description
        label, style = _GROUPS[description.severity]
        if label != heading:
            console.print(Text(label, _HEADING))
            heading = label
        console.print(
            Text("  " + _display(console, description.title), f"bold {style}")
        )
        if verbose:
            console.print(Text(f"    Rule: {issue.rule_id}", style="dim"))
        for item in issue.evidence:
            _reference(console, item, "    ")
        _detail(console, "Why: " + description.problem)
        _detail(console, "Next: " + description.recommendation)
        console.print()

    console.print(Text("COVERAGE", _HEADING))
    console.print(
        Text(
            f"  {evaluated} evaluated | {counts[Outcome.NOT_APPLICABLE]} not applicable"
        )
    )
    console.print(
        Text(
            f"  {counts[Outcome.UNKNOWN]} unknown | {counts[Outcome.FAILED]} failed"
            f" | {counts[Outcome.NOT_CHECKED]} not checked"
        )
    )
    if report.coverage in _COVERAGE:
        console.print(Text("  " + _COVERAGE[report.coverage], WARNING_COLOR))
    if not evaluated:
        console.print(
            Text(
                "  No checks could be evaluated."
                if partial
                else "  No applicable checks were evaluated."
            )
        )
    if verbose:
        for row in report.outcomes:
            status = row.outcome.value.replace("_", " ")
            reason = row.reason.value.replace("_", " ")
            console.print(Text(f"  {row.rule_id}: {status} ({reason})"))
            for item in row.scope_evidence:
                _reference(console, item, "    ")
    elif len(report.outcomes) > evaluated:
        console.print(Text("  Use --verbose for rule details.", style="dim"))
    console.print(Rule(characters="-" if ascii_only else "━", style=BORDER_COLOR))
    console.print(
        Text(
            ("Analysis incomplete." if partial else "Analysis complete.")
            + " No files changed.",
            WARNING_COLOR if partial else "",
        )
    )
