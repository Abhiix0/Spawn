"""Human-readable rendering of an InspectionReport for `spawn inspect`."""

import re

from rich.markup import escape

from spawn.inspection import (
    DetectionState,
    Diagnostic,
    Evidence,
    Finding,
    FindingCategory,
    InspectionReport,
)
from spawn.utils.console import console

MAX_LISTED = 20
MAX_EVIDENCE = 3

_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")

_SECTIONS: tuple[tuple[str, tuple[FindingCategory, ...]], ...] = (
    ("Languages and frameworks", (FindingCategory.LANGUAGE, FindingCategory.FRAMEWORK)),
    ("Package managers", (FindingCategory.PACKAGE_MANAGER,)),
    (
        "Tooling, CI, containers, databases",
        (
            FindingCategory.TOOL,
            FindingCategory.CI,
            FindingCategory.CONTAINER,
            FindingCategory.DATABASE,
        ),
    ),
)

_STATE_STYLE = {
    DetectionState.DETECTED: "green",
    DetectionState.INFERRED: "yellow",
    DetectionState.UNKNOWN: "yellow",
    DetectionState.NOT_DETECTED: "dim",
    DetectionState.NOT_CHECKED: "dim",
}


def safe(text: object) -> str:
    """Make repo-derived text printable: no control chars, no Rich markup."""
    s = str(text).encode("utf-8", "replace").decode("utf-8")
    return escape(_CONTROL.sub("?", s))


def _marker(state: DetectionState) -> str:
    return f"[{_STATE_STYLE[state]}]{escape(f'[{state.value.replace("_", " ")}]')}[/]"


def _evidence(items: tuple[Evidence, ...]) -> str:
    paths = [safe(e.path) for e in items[:MAX_EVIDENCE]]
    more = len(items) - MAX_EVIDENCE
    if more > 0:
        paths.append(f"+{more} more")
    return f" [dim]({', '.join(paths)})[/dim]" if paths else ""


def _row(f: Finding) -> str:
    line = f"  {_marker(f.detection_state)} {safe(f.subject)}{_evidence(f.evidence)}"
    if f.detail and f.detection_state in (
        DetectionState.INFERRED,
        DetectionState.UNKNOWN,
    ):
        line += f" - {safe(f.detail)}"
    return line


def _diag(d: Diagnostic) -> str:
    where = f" ({safe(d.path)})" if d.path else ""
    return f"  {safe(d.severity)} {safe(d.code)}: {safe(d.message)}{where}"


def _line(text: str = "") -> None:
    console.print(text, soft_wrap=True, highlight=False)


def render_report(report: InspectionReport, path_arg: str) -> None:
    s = report.summary
    framework = s.primary_framework
    if framework and any(
        f.category == FindingCategory.FRAMEWORK
        and f.subject == framework
        and f.detection_state == DetectionState.INFERRED
        for f in report.findings
    ):
        framework += " (inferred)"
    none = "[dim]none[/dim]"

    _line(f"[bold]Inspecting[/bold] {safe(path_arg)}")
    _line("\n[bold]Summary[/bold]")
    _line(f"  Name:              {safe(s.name) if s.name else none}")
    _line(f"  Origin:            {safe(s.origin)}")
    if s.spawn_version:
        _line(f"  Spawn version:     {safe(s.spawn_version)}")
    _line(
        f"  Primary language:  {safe(s.primary_language) if s.primary_language else none}"
    )
    _line(f"  Primary framework: {safe(framework) if framework else none}")

    for title, cats in _SECTIONS:
        _line(f"\n[bold]{title}[/bold]")
        rows = [f for f in report.findings if f.category in cats]
        for f in rows:
            _line(_row(f))
        if not rows:
            _line(f"  {none}")
        if title == "Package managers":
            deps = [
                f for f in report.findings if f.category == FindingCategory.DEPENDENCY
            ]
            _line(f"\n[bold]Dependencies[/bold] ({len(deps)})")
            names = ", ".join(safe(f.subject) for f in deps[:MAX_LISTED])
            if names:
                _line(f"  {names}")
            if len(deps) > MAX_LISTED:
                _line(
                    f"  [dim]... and {len(deps) - MAX_LISTED} more (see --json)[/dim]"
                )

    st = report.structure
    _line("\n[bold]Repository structure[/bold]")
    _line(f"  {st.file_count} files, {st.directory_count} directories")
    for label, items in (
        ("Top-level directories", st.top_level_directories),
        ("Top-level files", st.top_level_files),
    ):
        if items:
            shown = ", ".join(safe(i) for i in items[:MAX_LISTED])
            more = len(items) - MAX_LISTED
            _line(f"  {label}: {shown}" + (f", +{more} more" if more > 0 else ""))
    for f in report.findings:
        if f.category == FindingCategory.STRUCTURE:
            _line(_row(f))

    _line("\n[bold]Warnings and diagnostics[/bold]")
    printed = False
    for d in report.diagnostics:
        _line(_diag(d))
        printed = True
    for r in report.analyzer_results:
        if r.diagnostics:
            _line(f"  [dim]{safe(r.analyzer_name)} ({r.status.value})[/dim]")
            for d in r.diagnostics:
                _line(f"  {_diag(d)}")
            printed = True
    if not printed:
        _line(f"  {none}")

    _line(f"\n[bold]Status:[/bold] {report.status.value}")
