"""Human-readable rendering of an InspectionReport for `spawn inspect`."""

import re

from rich.console import Group, RenderableType
from rich.markup import escape
from rich.padding import Padding
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from spawn.inspection import (
    AnalysisStatus,
    DetectionState,
    Diagnostic,
    Evidence,
    Finding,
    FindingCategory,
    InspectionReport,
)
from spawn.utils.console import console

MAX_LISTED = 20  # top-level names shown by default; --verbose shows all
MAX_DEPS = 8  # dependency names previewed by default; --verbose shows all

_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")

# SideRays palette, kept in one place.
BRAND = "bold #2D5E8E"
HEADING = "bold #5B8FC4"
OK = "green"
WARN = "yellow"
ERROR = "red"
MUTED = "dim"

_TOOLING = (
    FindingCategory.TOOL,
    FindingCategory.CI,
    FindingCategory.CONTAINER,
    FindingCategory.DATABASE,
)

# state -> (unicode symbol, ascii symbol, style, label)
_STATE = {
    DetectionState.DETECTED: ("✓", "+", OK, "detected"),
    DetectionState.INFERRED: ("~", "~", WARN, "inferred"),
    DetectionState.UNKNOWN: ("?", "?", WARN, "unknown"),
    DetectionState.NOT_DETECTED: ("○", "-", MUTED, "not detected"),
    DetectionState.NOT_CHECKED: ("○", "-", MUTED, "not checked"),
}


def _clean(text: object) -> str:
    s = str(text).encode("utf-8", "replace").decode("utf-8")
    return _CONTROL.sub("?", s)


def safe(text: object) -> str:
    """Make repo-derived text printable: no control chars, no Rich markup."""
    return escape(_clean(text))


def _sym(unicode_: str, ascii_: str) -> str:
    return ascii_ if console.options.ascii_only else unicode_


def _label(text: str) -> Text:
    return Text(text, style=HEADING)


def _grid() -> Table:
    g = Table.grid(padding=(0, 2), pad_edge=False)
    g.add_column(no_wrap=True)
    g.add_column(overflow="fold", ratio=1)
    return g


def _section(title: str, body: RenderableType) -> RenderableType:
    return Group(
        Text(""), Text(title.upper(), style=HEADING), Padding(body, (1, 0, 0, 2))
    )


def _qualified(name: str, state: DetectionState) -> Text:
    """Name, suffixed with its confidence unless it is plainly detected."""
    t = Text(_clean(name))
    if state != DetectionState.DETECTED:
        t.append(f" · {_STATE[state][3]}", style=_STATE[state][2])
    return t


def _joined(findings: list[Finding]) -> Text:
    return Text(", ").join(_qualified(f.subject, f.detection_state) for f in findings)


def _evidence(items: tuple[Evidence, ...]) -> str:
    return ", ".join(_clean(e.path) for e in items)


def _status_rows(findings: list[Finding], verbose: bool) -> Table:
    g = Table.grid(padding=(0, 1), pad_edge=False)
    g.add_column(no_wrap=True)
    g.add_column(no_wrap=True)
    g.add_column(overflow="fold", ratio=1)
    width = max(len(_clean(f.subject)) for f in findings)
    for f in findings:
        uni, asc, style, label = _STATE[f.detection_state]
        note = Text(
            label,
            style=MUTED if f.detection_state == DetectionState.DETECTED else style,
        )
        if f.detail and f.detection_state in (
            DetectionState.INFERRED,
            DetectionState.UNKNOWN,
        ):
            note.append(f" - {_clean(f.detail)}", style=MUTED)
        if verbose and f.evidence:
            note.append(f" ({_evidence(f.evidence)})", style=MUTED)
        g.add_row(
            Text(_sym(uni, asc), style=style),
            Text(_clean(f.subject).ljust(width)),
            note,
        )
    return g


def _header(report: InspectionReport, path_arg: str) -> RenderableType:
    s, st = report.summary, report.structure
    facts = [f"{_clean(s.primary_language)} project"] if s.primary_language else []
    facts += [f"{st.file_count} files", f"{st.directory_count} directories"]
    return Group(
        Text(f"{_sym('⚡ ', '')}SPAWN / INSPECT", style=BRAND),
        Text(""),
        Text(_clean(s.name or path_arg), style="bold"),
        Text(" · ".join(facts)),
        Text(_clean(path_arg), style=MUTED),
    )


def _overview(report: InspectionReport) -> RenderableType:
    s = report.summary
    not_detected = Text("Not detected", style=MUTED)
    g = _grid()
    g.add_row(
        _label("Primary language"),
        Text(_clean(s.primary_language)) if s.primary_language else not_detected,
    )
    fw = not_detected
    if s.primary_framework:
        match = next(
            (
                f
                for f in report.findings
                if f.category == FindingCategory.FRAMEWORK
                and f.subject == s.primary_framework
            ),
            None,
        )
        fw = _qualified(
            s.primary_framework,
            match.detection_state if match else DetectionState.DETECTED,
        )
        if match and match.detail and match.detection_state != DetectionState.DETECTED:
            fw.append(f" - {_clean(match.detail)}", style=MUTED)
    g.add_row(_label("Framework"), fw)
    pms = [
        f
        for f in report.findings
        if f.category == FindingCategory.PACKAGE_MANAGER
        and f.detection_state != DetectionState.NOT_DETECTED
    ]
    g.add_row(_label("Package manager"), _joined(pms) if pms else not_detected)
    g.add_row(_label("Origin"), Text(_clean(s.origin)))
    if s.spawn_version:
        g.add_row(_label("Spawn version"), Text(_clean(s.spawn_version)))
    return _section("Project overview", g)


def _technology(report: InspectionReport, verbose: bool) -> RenderableType:
    s = report.summary
    langs = [f for f in report.findings if f.category == FindingCategory.LANGUAGE]
    deps = [f for f in report.findings if f.category == FindingCategory.DEPENDENCY]
    other_fw = [
        f
        for f in report.findings
        if f.category == FindingCategory.FRAMEWORK and f.subject != s.primary_framework
    ]
    g = _grid()
    # A lone language equal to the primary one would repeat the overview.
    if langs and not (len(langs) == 1 and langs[0].subject == s.primary_language):
        g.add_row(_label("Languages"), _joined(langs))
    if other_fw:
        g.add_row(_label("Other frameworks"), _joined(other_fw))
    if deps:
        n_inf = sum(f.detection_state != DetectionState.DETECTED for f in deps)
        count = f"{len(deps) - n_inf} detected" + (
            f", {n_inf} inferred" if n_inf else ""
        )
        g.add_row(_label("Dependencies"), Text(count))
        shown = deps if verbose else deps[:MAX_DEPS]
        names = _joined(shown)
        if len(deps) > len(shown):
            names.append(f", +{len(deps) - len(shown)} more (--verbose)", style=MUTED)
        g.add_row("", names)
    else:
        g.add_row(_label("Dependencies"), Text("None detected", style=MUTED))
    return _section("Technology", g)


def _structure(report: InspectionReport, verbose: bool) -> RenderableType:
    st = report.structure
    g = _grid()
    g.add_row(_label("Files"), Text(str(st.file_count)))
    g.add_row(_label("Directories"), Text(str(st.directory_count)))
    for label, items in (
        ("Top-level dirs", st.top_level_directories),
        ("Top-level files", st.top_level_files),
    ):
        if not items:
            continue
        shown = items if verbose else items[:MAX_LISTED]
        t = Text(", ".join(_clean(i) for i in shown))
        if len(items) > len(shown):
            t.append(f", +{len(items) - len(shown)} more (--verbose)", style=MUTED)
        g.add_row(_label(label), t)
    parts: list[RenderableType] = [g]
    marks = [f for f in report.findings if f.category == FindingCategory.STRUCTURE]
    if marks:
        parts += [Text(""), _status_rows(marks, verbose)]
    return _section("Repository structure", Group(*parts))


def _diag(d: Diagnostic, indent: str = "") -> Text:
    is_error = d.severity == "error"
    t = Text(indent)
    t.append(
        f"{_sym('✗', '!') if is_error else '!'} {_clean(d.severity)} ",
        style=ERROR if is_error else WARN,
    )
    t.append(f"{_clean(d.code)}: {_clean(d.message)}")
    if d.path:
        t.append(f" ({_clean(d.path)})", style=MUTED)
    return t


def _diagnostics(report: InspectionReport) -> RenderableType:
    lines = [_diag(d) for d in report.diagnostics]
    for r in report.analyzer_results:
        if r.diagnostics:
            lines.append(
                Text(f"{_clean(r.analyzer_name)} ({r.status.value})", style=MUTED)
            )
            lines += [_diag(d, "  ") for d in r.diagnostics]
    if not lines:
        lines = [Text(f"{_sym('✓', '+')} No warnings detected", style=OK)]
    return _section("Diagnostics", Group(*lines))


def _footer(report: InspectionReport) -> RenderableType:
    if report.status == AnalysisStatus.FAILED:
        msg = Text(f"{_sym('✗', '!')} Inspection failed", style=ERROR)
    elif report.status == AnalysisStatus.COMPLETE:
        msg = Text(f"{_sym('✓', '+')} Inspection complete", style=OK)
    else:
        msg = Text(
            f"~ Inspection {report.status.value}: findings may be incomplete",
            style=WARN,
        )
    return Group(Text(""), Rule(characters=_sym("━", "-"), style=BRAND), msg)


def render_report(
    report: InspectionReport, path_arg: str, verbose: bool = False
) -> None:
    tooling = [f for f in report.findings if f.category in _TOOLING]
    parts: list[RenderableType | None] = [
        _header(report, path_arg),
        Text(""),
        Rule(characters=_sym("━", "-"), style=BRAND),
        _overview(report),
        _technology(report, verbose),
        _section("Tooling", _status_rows(tooling, verbose)) if tooling else None,
        _structure(report, verbose),
        _diagnostics(report),
        _footer(report),
    ]
    console.print(Group(*[p for p in parts if p is not None]), highlight=False)
