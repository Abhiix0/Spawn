"""Compact terminal rendering for the onboarding projection."""

from __future__ import annotations

import os
import sys

from rich.cells import cell_len
from rich.console import Console
from rich.text import Text

from spawn.onboarding import OnboardingReport, Technology
from spawn.utils.theme import ACCENT_COLOR, PROMPT_COLOR

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
_CATEGORIES = ("start", "install", "test", "lint", "format")
_LEAD = 14


def onboard_console(no_color: bool) -> Console:
    plain = no_color or "NO_COLOR" in os.environ or not sys.stdout.isatty()
    return Console(file=sys.stdout, force_terminal=False if plain else None)


def _name(technology: Technology) -> str:
    return _NAMES.get(technology.name, technology.name)


def _label(value: str) -> Text:
    return Text(f"  {value:<{_LEAD - 2}}", style=PROMPT_COLOR)


def _row(console: Console, label: str, value: str, *, truncate: bool = False) -> None:
    content = Text(value)
    if truncate:
        content.truncate(max(1, console.width - _LEAD), overflow="ellipsis")
    console.print(_label(label).append_text(content), overflow="fold")


def _section(console: Console, title: str) -> None:
    console.print()
    console.print(Text(title, style=f"bold {PROMPT_COLOR}"))


def _items(paths: tuple[str, ...], priorities: tuple[str, ...]) -> list[str]:
    rank = {name: index for index, name in enumerate(priorities)}
    return sorted(
        paths, key=lambda item: (rank.get(item, len(rank)), item.count("/"), item)
    )


def _reference(path: str, detail: str | None) -> str:
    return f"{path}:{detail[5:]}" if detail else path


def _evidence(console: Console, items, *, total: int | None = None) -> None:
    for item in items:
        _row(
            console,
            "Evidence",
            f"{_reference(item.path, item.detail)}  {item.indicator}",
        )
    if total is not None and total > len(items):
        _row(console, "Evidence", f"{total - len(items)} more matching files")


def render_onboarding(
    report: OnboardingReport, console: Console, *, verbose: bool = False
) -> None:
    """Show a short path through the repository, with optional evidence and alternatives."""
    header = Text("Spawn / Onboard", style=f"bold {ACCENT_COLOR}")
    header.append(f"  {report.name}", style="bold")
    header.truncate(console.width, overflow="ellipsis")
    console.print(header)

    _section(console, "Overview")
    for label, technologies in (
        ("Languages", report.languages),
        ("Frameworks", report.frameworks),
    ):
        shown = technologies if verbose else technologies[:3]
        descriptions = [
            f"{_name(item)} [{item.status}]"
            if label == "Frameworks" or item.status != "detected"
            else _name(item)
            for item in shown
        ]
        if len(shown) < len(technologies):
            descriptions.append(f"+{len(technologies) - len(shown)} more")
        _row(console, label, ", ".join(descriptions) or "unknown", truncate=not verbose)
        if verbose:
            for item in shown:
                _row(console, "Source", _name(item))
                _evidence(console, item.evidence, total=item.evidence_count)

    _section(console, "Start here")
    hidden = 0
    start_known = any(row.category == "start" and row.argv for row in report.commands)
    if not start_known:
        _row(console, "Start", "unknown. Check the README or project configuration.")
    for category in _CATEGORIES:
        rows = [row for row in report.commands if row.category == category]
        known = [row for row in rows if row.argv]
        if category == "install":
            known.sort(
                key=lambda row: (
                    row.status != "explicit",
                    not any(
                        item.indicator == "Lockfile present" for item in row.evidence
                    ),
                )
            )
        hidden += max(0, len(known) - 1)
        for row in rows if verbose else known[:1]:
            status = "detected" if row.status == "explicit" else row.status.value
            if row.argv is None:
                if start_known or category != "start":
                    _row(console, category.capitalize(), "unknown")
            else:
                command = " ".join(row.argv)
                label = category.capitalize()
                status_text = f"[{status}]"
                if (
                    _LEAD + cell_len(command) + cell_len(status_text) + 2
                    <= console.width
                ):
                    console.print(
                        _label(label)
                        .append(command)
                        .append(f"  {status_text}", style="dim")
                    )
                else:
                    _row(console, label, status_text)
                    # Preserve a long command as one copyable line; the terminal can wrap it.
                    console.print(Text(f"  {command}"), soft_wrap=True)
                if row.cwd != ".":
                    _row(console, "Run from", row.cwd, truncate=not verbose)
            if verbose:
                _row(console, "Why", row.note)
                _evidence(console, row.evidence)

    _section(console, "Explore")
    entries = report.entry_points if verbose else report.entry_points[:2]
    for entry in entries:
        ref = _reference(entry.evidence[0].path, entry.evidence[0].detail)
        _row(
            console,
            "Entry",
            f"{entry.target} [{entry.state.value}]  ({ref})",
            truncate=not verbose,
        )
        if verbose:
            _row(console, "Why", entry.reason)
            _evidence(console, entry.evidence)
    if not entries:
        _row(console, "Entry", "No supported entry point found.")
    directories = _items(
        report.directories, ("src", "app", "apps", "tests", "config", "docs")
    )
    configs = _items(
        report.config_files,
        ("README.md", "pyproject.toml", "uv.lock", "Makefile", "manage.py"),
    )
    for label, paths, suffix in (
        ("Folders", directories, "/"),
        ("Config", configs, ""),
    ):
        if not paths:
            continue
        if verbose:
            for item in paths:
                _row(console, label, item + suffix)
        else:
            _row(
                console,
                label,
                ", ".join(item + suffix for item in paths[:4]),
                truncate=True,
            )

    _section(console, "Notes")
    console.print(Text("  Review suggestions before running them."), overflow="fold")
    if report.status == "partial":
        console.print(
            Text("  Partial report. Some evidence could not be analyzed."),
            overflow="fold",
        )
    if not verbose:
        suffix = "" if hidden == 1 else "s"
        note = (
            f"{hidden} alternative{suffix}. Use --verbose for evidence."
            if hidden
            else "Use --verbose for evidence and details."
        )
        console.print(Text(f"  {note}"))
