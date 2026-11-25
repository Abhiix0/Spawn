"""Literal path checks for pytest configuration and pip requirements."""

import re

from spawn.inspection.dependencies import parse_manifest

from ..models import Evidence, Reason
from ..rules import RuleContext
from ._common import OUTSIDE_SCOPE, Unclear, check, kind, literal, read, table

_TESTPATHS_KEY = "tool.pytest.ini-options.testpaths"
_PYTEST_COMMAND = re.compile(
    r"\t@?(?:pytest|python -m pytest) (?:-c |--config-file[ =])([^ \t]+)"
)
_INCLUDE = re.compile(r"(?:-r[ \t]+|--requirement(?:[ \t]+|=))([^ \t]+)")


def _testpaths(context: RuleContext, doc: dict):
    if any(
        kind(context, name) != "missing"
        for name in (
            "pytest.toml",
            ".pytest.toml",
            "pytest.ini",
            ".pytest.ini",
            "tox.ini",
            "setup.cfg",
        )
    ):
        raise Unclear()
    pytest = table(table(doc.get("tool", {})).get("pytest", {}))
    if set(pytest) - {"ini_options"}:
        raise Unclear()
    config = table(pytest.get("ini_options", {}))
    if "testpaths" not in config:
        return OUTSIDE_SCOPE
    entries = config["testpaths"]
    if not isinstance(entries, list):
        raise Unclear(Reason.EVIDENCE_MISSING)
    if not entries:
        return OUTSIDE_SCOPE
    missing = False
    for entry in entries:
        context.spend()
        missing |= kind(context, literal(entry)) == "missing"
    return ((Evidence("pyproject.toml", key=_TESTPATHS_KEY),),) if missing else ()


def _make_config(context: RuleContext, doc: dict):
    if kind(context, "Makefile") == "missing":
        return OUTSIDE_SCOPE
    lines = []
    for number, line in enumerate(read(context, "Makefile").split("\n"), 1):
        context.spend()
        line = line.removesuffix("\r")
        if line.rstrip(" \t").endswith("\\"):
            raise Unclear()
        if line.strip() and not line.lstrip().startswith("#"):
            lines.append((number, line.rstrip(" \t")))
    if lines and lines[0][1] == ".PHONY: test":
        lines.pop(0)
    if len(lines) != 2 or lines[0][1] != "test:":
        raise Unclear()
    number, recipe = lines[1]
    if recipe in {"\tpytest", "\t@pytest", "\tpython -m pytest", "\t@python -m pytest"}:
        return OUTSIDE_SCOPE
    match = _PYTEST_COMMAND.fullmatch(recipe)
    if not match:
        raise Unclear()
    target = kind(context, literal(match[1]))
    if target == "directory":
        raise Unclear()
    return ((Evidence("Makefile", line=number),),) if target == "missing" else ()


def _requirements(context: RuleContext, doc: dict):
    path = "requirements.txt"
    if kind(context, path) == "missing":
        return OUTSIDE_SCOPE
    lines = read(context, path).split("\n")
    findings = []
    applicable = False
    for number, raw in enumerate(lines, 1):
        context.spend()
        line = raw.removesuffix("\r").strip(" \t")
        if not line or line.startswith("#"):
            # A continued comment can consume the next physical line.
            if line.endswith("\\"):
                raise Unclear()
            continue
        match = _INCLUDE.fullmatch(line)
        if match:
            applicable = True
            target = kind(context, literal(match[1]))
            if target == "missing":
                findings.append((Evidence(path, line=number),))
            elif target != "file":
                raise Unclear()
        elif line.startswith("-") or any(char in line for char in "\\$#\x00"):
            raise Unclear()
        else:
            manifest = parse_manifest(path, line)
            if manifest.problems or not manifest.declarations:
                raise Unclear(Reason.EVIDENCE_MISSING)
    return tuple(findings) if applicable else OUTSIDE_SCOPE


PYTEST_PATHS = check(
    "py-test-001",
    "testing",
    "Pytest testpaths entry is missing",
    "At least one literal testpaths entry in this configuration names no file or directory.",
    "Check the testpaths list and point each entry at an existing path or remove the stale entry.",
    _testpaths,
    keys=(_TESTPATHS_KEY,),
)
MAKE_CONFIG = check(
    "py-test-002",
    "testing",
    "Make recipe names a missing pytest config",
    "The standalone test recipe names a local pytest configuration file absent from the checkout.",
    "Restore the configuration file or correct the pytest config option in the test recipe.",
    _make_config,
)
REQUIREMENTS = check(
    "py-deps-001",
    "dependencies",
    "Requirements include is missing",
    "This requirements include names a local file absent from the checkout.",
    "Restore the included requirements file or correct the include path.",
    _requirements,
)
