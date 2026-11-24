"""Compact terminal rendering for the onboarding projection."""

from __future__ import annotations

import os
import sys

from rich.cells import cell_len
from rich.console import Console
from rich.text import Text

from spawn.inspection.development_workflows import DevelopmentCommand
from spawn.inspection.models import Evidence
from spawn.onboarding import OnboardingReport, Technology
from spawn.utils.theme import ACCENT_COLOR, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR

_NAMES = {
    "python": "Python",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "starlette": "Starlette",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "nextjs": "Next.js",
    "nodejs": "Node.js",
}
_CATEGORIES = (
    ("start", "Run"),
    ("install", "Install"),
    ("test", "Test"),
    ("lint", "Lint"),
    ("format", "Format"),
)
_ENTRY_LABELS = {
    "console_script": "CLI",
    "module": "Module",
    "asgi": "ASGI",
    "flask_app": "Flask",
    "flask_factory": "Flask factory",
    "django_manage": "Django",
    "django_asgi": "ASGI",
    "django_wsgi": "WSGI",
}
_MARKER_STYLE = {"+": SUCCESS_COLOR, "~": WARNING_COLOR, "?": WARNING_COLOR}
_LEAD = 19


def onboard_console(no_color: bool) -> Console:
    plain = no_color or "NO_COLOR" in os.environ or not sys.stdout.isatty()
    return Console(file=sys.stdout, force_terminal=False if plain else None)


def _name(technology: Technology) -> str:
    return _NAMES.get(technology.name, technology.name)


def _row(
    console: Console,
    label: str,
    value: str | Text,
    *,
    marker: str = "",
    command: bool = False,
) -> None:
    content = Text(value) if isinstance(value, str) else value
    prefix = Text("  ").append(f"{marker or ' '} ", style=_MARKER_STYLE.get(marker))
    prefix.append(f"{label:<{_LEAD - 4}}")
    width = max(1, console.width - _LEAD)
    if command and cell_len(content.plain) > width:
        prefix.rstrip()
        console.print(prefix, highlight=False)
        # The terminal can soft-wrap a long command without changing copied argv.
        console.print(
            Text("    ").append_text(content), soft_wrap=True, highlight=False
        )
        return
    for index, line in enumerate(content.wrap(console, width, overflow="fold")):
        line.rstrip()
        lead = prefix if index == 0 else Text(" " * _LEAD)
        console.print(lead.append_text(line), highlight=False)


def _section(console: Console, title: str) -> None:
    console.print()
    console.print(Text(title.upper(), style=f"bold {ACCENT_COLOR}"))


def _items(paths: tuple[str, ...], priorities: tuple[str, ...]) -> list[str]:
    rank = {name: index for index, name in enumerate(priorities)}
    return sorted(
        paths, key=lambda item: (rank.get(item, len(rank)), item.count("/"), item)
    )


def _reference(path: str, detail: str | None) -> str:
    return f"{path}:{detail[5:]}" if detail else path


def _evidence(
    console: Console, items: tuple[Evidence, ...], *, total: int | None = None
) -> None:
    for item in items:
        _row(
            console,
            "Evidence",
            Text(
                f"{_reference(item.path, item.detail)}  {item.indicator}", style="dim"
            ),
        )
    if total is not None and total > len(items):
        _row(console, "Evidence", f"{total - len(items)} more matching files")


def _overview(console: Console, report: OnboardingReport, verbose: bool) -> int:
    _section(console, "Project overview")
    hidden = 0
    for label, technologies in (
        ("Languages", report.languages),
        ("Frameworks", report.frameworks),
    ):
        shown = technologies if verbose else technologies[:3]
        hidden += len(technologies) - len(shown)
        descriptions = Text(", ").join(
            Text(_name(item), style=SUCCESS_COLOR)
            if item.status == "detected"
            else Text(f"{_name(item)} (candidate)", style=WARNING_COLOR)
            for item in shown
        )
        _row(
            console, label, descriptions if shown else Text("Not detected", style="dim")
        )
        if verbose:
            for item in shown:
                _row(console, "Source", _name(item))
                _evidence(console, item.evidence, total=item.evidence_count)
    return hidden


def _prefer_django_server(commands: list[DevelopmentCommand]) -> None:
    """Keep a manage.py module invocation behind its server command."""
    if not commands:
        return
    first = commands[0]
    if not first.argv or len(first.argv) != 3 or first.argv[:2] != ("python", "-m"):
        return
    paths = {item.path for item in first.evidence}
    for index, row in enumerate(commands[1:], 1):
        if (
            row.argv == ("python", "manage.py", "runserver")
            and row.status == first.status
            and any(item.path in paths for item in row.evidence)
        ):
            commands.insert(0, commands.pop(index))
            break


def _commands(
    console: Console, report: OnboardingReport, verbose: bool
) -> tuple[int, int, int]:
    _section(console, "Start here")
    hidden = 0
    candidates = 0
    declared = 0
    any_command = any(row.argv for row in report.commands)
    start_known = any(row.category == "start" and row.argv for row in report.commands)
    if not any_command:
        message = "No supported commands found."
        if "README.md" in report.config_files:
            message += " See README.md."
        console.print(Text(f"  {message}", style="dim"))
    elif not start_known:
        _row(console, "Run", Text("Not detected", style="dim"))
    for category, label in _CATEGORIES:
        rows = [row for row in report.commands if row.category == category]
        known = [row for row in rows if row.argv]
        if category == "start":
            _prefer_django_server(known)
        elif category == "install":
            known.sort(
                key=lambda row: (
                    row.status != "explicit",
                    not any(
                        item.indicator == "Lockfile present" for item in row.evidence
                    ),
                )
            )
        shown = rows if verbose else known[:1]
        if not verbose:
            hidden += max(0, len(known) - 1) + sum(
                row.argv is None and bool(row.evidence) for row in rows
            )
        for index, row in enumerate(shown):
            purpose = label if index == 0 else ""
            if row.argv is None:
                if start_known or category != "start":
                    _row(console, purpose, "Not resolved", marker="?")
            else:
                explicit = row.status == "explicit"
                declared += explicit
                candidates += not explicit
                _row(
                    console,
                    purpose,
                    Text(" ".join(row.argv), style="bold"),
                    marker="+" if explicit else "~",
                    command=True,
                )
                if row.cwd != ".":
                    _row(console, "", Text(f"From {row.cwd}", style="dim"))
            if verbose:
                _row(console, "Why", Text(row.note, style="dim"))
                _evidence(console, row.evidence)
    return hidden, candidates, declared


def _entry_points(console: Console, report: OnboardingReport, verbose: bool) -> int:
    _section(console, "Entry points")
    entries = report.entry_points if verbose else report.entry_points[:2]
    for entry in entries:
        detected = entry.state == "detected"
        _row(
            console,
            _ENTRY_LABELS.get(entry.kind, "Entry"),
            entry.target if detected else f"{entry.target} (unresolved)",
            marker="+" if detected else "?",
        )
        if verbose:
            _row(console, "Why", Text(entry.reason, style="dim"))
            _evidence(console, entry.evidence)
        elif entry.evidence:
            first = entry.evidence[0]
            _row(console, "", Text(_reference(first.path, first.detail), style="dim"))
    if not entries:
        console.print(Text("  No supported entry point found.", style="dim"))
    return len(report.entry_points) - len(entries)


def _structure(console: Console, report: OnboardingReport, verbose: bool) -> int:
    directories = _items(
        report.directories, ("src", "app", "apps", "tests", "config", "docs")
    )
    configs = _items(
        report.config_files,
        ("README.md", "pyproject.toml", "uv.lock", "Makefile", "manage.py"),
    )
    if directories or configs:
        _section(console, "Project structure")
    hidden = 0
    for label, paths, suffix in (
        ("Directories", directories, "/"),
        ("Configuration", configs, ""),
    ):
        shown = paths if verbose else paths[:4]
        hidden += len(paths) - len(shown)
        if shown:
            _row(console, label, "  ".join(path + suffix for path in shown))
    return hidden


def _footer(console: Console, status: str) -> None:
    marker, color, message = {
        "complete": ("+", SUCCESS_COLOR, "Repository onboarding complete"),
        "partial": ("~", WARNING_COLOR, "Repository onboarding partial"),
        "failed": ("!", ERROR_COLOR, "Repository onboarding failed"),
    }[status]
    console.print()
    console.print(Text(f"  {marker} {message}", style=color))


def render_onboarding(
    report: OnboardingReport, console: Console, *, verbose: bool = False
) -> None:
    """Render the onboarding projection without changing discovery order."""
    console.print(Text("SPAWN / ONBOARD", style=f"bold {ACCENT_COLOR}"))
    console.print(Text(report.name, style="bold", overflow="fold"), highlight=False)
    hidden = _overview(console, report, verbose)
    hidden_commands, candidates, declared = _commands(console, report, verbose)
    hidden += hidden_commands + _entry_points(console, report, verbose)
    hidden += _structure(console, report, verbose)

    if candidates or declared or hidden or report.status == "partial":
        _section(console, "Notes")
        if declared:
            console.print(
                Text("  + Declared commands. Runtime not checked.", style="dim")
            )
        if candidates:
            description = "command requires" if candidates == 1 else "commands require"
            console.print(
                Text(
                    f"  ~ {candidates} candidate {description} verification.",
                    style=WARNING_COLOR,
                )
            )
        if hidden:
            noun = "result" if hidden == 1 else "results"
            console.print(Text(f"  {hidden} more {noun} with --verbose.", style="dim"))
        if report.status == "partial":
            console.print(
                Text(
                    "  Some evidence could not be analyzed. See diagnostics.",
                    style="dim",
                )
            )
    _footer(console, report.status)
