"""Documentation consistency checks."""

import re
from pathlib import Path

from spawn.cli.errors import UNEXPECTED_EXIT_CODE
from spawn.core import exceptions

ROOT = Path(__file__).resolve().parent.parent
COMMANDS = ROOT / "docs" / "commands.md"


def _documented_codes() -> set[int]:
    text = COMMANDS.read_text(encoding="utf-8")
    section = text.split("## Exit codes", 1)[1]
    section = re.split(r"\n## ", section, maxsplit=1)[0]
    return {int(m) for m in re.findall(r"^\|\s*(\d+)\s*\|", section, re.MULTILINE)}


def test_exit_codes_table_matches_code():
    expected = {
        cls.exit_code
        for cls in vars(exceptions).values()
        if isinstance(cls, type) and issubclass(cls, exceptions.SpawnError)
    }
    expected |= {0, 2, 130, UNEXPECTED_EXIT_CODE}
    assert _documented_codes() == expected


def test_no_stale_exit_code_text():
    assert "0 (error printed)" not in COMMANDS.read_text(encoding="utf-8")


def test_no_load_project_references():
    files = [*(ROOT / "docs").rglob("*.md")]
    files += [ROOT / n for n in ("README.md", "CLAUDE.md", "CONTRIBUTING.md")]
    offenders = [
        str(f.relative_to(ROOT))
        for f in files
        if "load_project" in f.read_text(encoding="utf-8")
    ]
    assert offenders == []
