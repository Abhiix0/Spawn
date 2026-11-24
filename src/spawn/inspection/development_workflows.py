"""Static Python workflow suggestions. All argv values are display data."""

from __future__ import annotations

import re
import tomllib
from collections import defaultdict
from configparser import ConfigParser, Error as IniError
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import PurePosixPath

from spawn.inspection._reading import read_inventory_text
from spawn.inspection.dependencies import parse_manifest
from spawn.inspection.entry_points import PythonEntryPoints
from spawn.inspection.models import (
    DetectionState,
    DiscoveryInventory,
    Evidence,
    InspectionTarget,
)


class CommandCategory(StrEnum):
    INSTALL = "install"
    START = "start"
    TEST = "test"
    LINT = "lint"
    FORMAT = "format"


class CommandStatus(StrEnum):
    EXPLICIT = "explicit"
    CANDIDATE = "candidate"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DevelopmentCommand:
    category: CommandCategory
    argv: tuple[str, ...] | None
    cwd: str
    status: CommandStatus
    evidence: tuple[Evidence, ...]
    note: str


@dataclass(frozen=True)
class DevelopmentWorkflows:
    commands: tuple[DevelopmentCommand, ...]
    skipped: tuple[str, ...]
    truncated: bool


C = CommandCategory
S = CommandStatus
_MAX_CONFIGS = 128
_LOCKS = {
    "uv.lock": ("uv", "sync", "--locked"),
    "poetry.lock": ("poetry", "install"),
    "Pipfile.lock": ("pipenv", "sync"),
}
_CONFIGS = {"pyproject.toml", "pytest.ini", "tox.ini", "Makefile"}
_REQUIREMENTS = re.compile(r"requirements[a-zA-Z0-9_.-]{0,96}\.txt")
_COMMAND_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}")
_TARGET = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*"
)
_ALIASES = {
    "install": C.INSTALL,
    "setup": C.INSTALL,
    "start": C.START,
    "run": C.START,
    "serve": C.START,
    "test": C.TEST,
    "tests": C.TEST,
    "lint": C.LINT,
    "format": C.FORMAT,
    "fmt": C.FORMAT,
}


def _table(value: object, *keys: str) -> dict:
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value if isinstance(value, dict) else {}


def _cwd(path: str) -> str:
    return PurePosixPath(path).parent.as_posix()


def _suggest(
    category: CommandCategory,
    argv: tuple[str, ...] | None,
    path: str,
    indicator: str,
    note: str,
    *,
    status: CommandStatus = S.CANDIDATE,
    line: int | None = None,
) -> DevelopmentCommand:
    return DevelopmentCommand(
        category,
        argv,
        _cwd(path),
        status,
        (Evidence(path, indicator, f"line {line}" if line is not None else None),),
        note,
    )


def _static_category(recipe: str, *, tox: bool = False) -> CommandCategory | None:
    """Recognize a few whole command shapes without interpreting shell syntax."""
    tokens = recipe.split()
    if tox and tokens[-1:] == ["{posargs}"]:
        tokens.pop()
    if tokens[:2] in (["uv", "run"], ["poetry", "run"]):
        tokens = tokens[2:]
    if tokens[:3] in (
        ["python", "-m", "pytest"],
        ["python", "-m", "pip"],
        ["python", "-m", "uvicorn"],
    ):
        tokens = tokens[2:]
    if tokens[:1] == ["pytest"] and tokens[1:] in (
        [],
        ["-q"],
        ["tests"],
        ["-q", "tests"],
    ):
        return C.TEST
    if tokens in (["ruff", "check", "."], ["ruff", "check"]):
        return C.LINT
    if tokens in (["ruff", "format", "."], ["ruff", "format", "--check", "."]):
        return C.FORMAT
    if tokens in (
        ["uv", "sync"],
        ["uv", "sync", "--locked"],
        ["poetry", "install"],
        ["pip", "install", "."],
    ):
        return C.INSTALL
    if tokens == ["python", "manage.py", "runserver"]:
        return C.START
    if len(tokens) == 2 and tokens[0] == "uvicorn" and _TARGET.fullmatch(tokens[1]):
        return C.START
    return None


def _wrapper(
    path: str,
    category: CommandCategory,
    argv: tuple[str, ...],
    indicator: str,
    static: bool,
    line: int | None = None,
) -> DevelopmentCommand:
    return _suggest(
        category,
        argv if static else None,
        path,
        indicator,
        "Repository declares this wrapper with a recognized static recipe."
        if static
        else "Recipe uses syntax outside the supported static subset.",
        status=S.EXPLICIT if static else S.UNKNOWN,
        line=line,
    )


def _make_targets(path: str, text: str):
    rules: dict[str, list[tuple[int, bool, list[str]]]] = defaultdict(list)
    current = None
    dynamic = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.rstrip().endswith("\\"):
            dynamic = True
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("\t"):
            if current is not None:
                current.append(line[1:].lstrip().removeprefix("@"))
            continue
        current = None
        if "$" in line or re.match(
            r"^\s*(?:-?include|sinclude|ifn?def|ifn?eq|else|endif|"
            r"(?:override\s+)?define|(?:(?:override|export)\s+)?"
            r"(?:SHELL|MAKEFLAGS|MAKEFILES|\.(?:RECIPEPREFIX|SHELLFLAGS|EXTRA_PREREQS)))\b",
            line,
        ):
            dynamic = True
        name, colon, rest = line.partition(":")
        name = name.rstrip()
        if colon and name in _ALIASES:
            current = []
            rules[name].append((number, not rest.partition("#")[0].strip(), current))
    for name, declarations in rules.items():
        line, standalone, recipes = declarations[0]
        category = _ALIASES[name]
        static = (
            not dynamic
            and len(declarations) == 1
            and standalone
            and bool(recipes)
            and all(_static_category(recipe) == category for recipe in recipes)
        )
        yield _wrapper(
            path,
            category,
            ("make", "-f", "Makefile", name),
            f"Make target {name}",
            static,
            line,
        )


def _tox_commands(path: str, ini: ConfigParser):
    for section in ini.sections():
        if section == "testenv":
            env = None
        elif section.startswith("testenv:") and re.fullmatch(
            r"(?:py[0-9]{0,3}|test|lint|format)", section.removeprefix("testenv:")
        ):
            env = section.removeprefix("testenv:")
        else:
            continue
        # ConfigParser has interpolation disabled. Tox placeholders stay inert.
        recipes = ini.get(section, "commands", raw=True, fallback="").strip()
        if not recipes:
            continue
        categories = {
            _static_category(line, tox=True)
            for line in recipes.splitlines()
            if line.strip()
        }
        recognized = categories - {None}
        argv = ("tox",) if env is None else ("tox", "-e", env)
        static = (
            None not in categories
            and not any(
                ini.has_option(section, option) or ini.has_option("testenv", option)
                for option in ("commands_pre", "commands_post")
            )
            and "commands" not in ini.defaults()
        )
        for category in sorted(recognized or {_ALIASES.get(env, C.TEST)}):
            item = _wrapper(path, category, argv, f"[{section}] commands", static)
            if static and env is None:
                item = replace(
                    item,
                    status=S.CANDIDATE,
                    note="Default testenv has recognized commands; tox may select other environments.",
                )
            yield item


def _manifest_commands(path: str, data: dict):
    build = _table(data, "build-system")
    project = _table(data, "project")
    if isinstance(build.get("build-backend"), str) or isinstance(
        project.get("name"), str
    ):
        indicator = (
            "[build-system] build-backend"
            if isinstance(build.get("build-backend"), str)
            else "[project] name"
        )
        yield _suggest(
            C.INSTALL,
            ("python", "-m", "pip", "install", "."),
            path,
            indicator,
            "Project metadata suggests a local package install.",
        )
    for tool, argv in (
        ("uv", ("uv", "sync")),
        ("poetry", ("poetry", "install")),
        ("hatch", ("hatch", "env", "create")),
    ):
        parts = ("tool", tool, "envs") if tool == "hatch" else ("tool", tool)
        parent = _table(data, *parts[:-1])
        if isinstance(parent.get(parts[-1]), dict):
            yield _suggest(
                C.INSTALL,
                argv,
                path,
                f"[{'.'.join(parts)}]",
                "Tool configuration suggests this environment setup.",
            )
    for name, recipes in _table(
        data, "tool", "hatch", "envs", "default", "scripts"
    ).items():
        if name not in _ALIASES:
            continue
        category = _ALIASES[name]
        lines = recipes if isinstance(recipes, list) else [recipes]
        static = bool(lines) and all(
            isinstance(line, str)
            and "\n" not in line
            and "\r" not in line
            and _static_category(line) == category
            for line in lines
        )
        yield _wrapper(
            path,
            category,
            ("hatch", "run", name),
            f"[tool.hatch.envs.default.scripts] {name}",
            static,
        )
    tool = _table(data, "tool")
    for name in ("pytest", "ruff"):
        if isinstance(tool.get(name), dict):
            yield from _tool_commands(name, path, f"[tool.{name}]")


def _tool_commands(name: str, path: str, indicator: str):
    if name == "pytest":
        yield _suggest(
            C.TEST,
            ("python", "-m", "pytest"),
            path,
            indicator,
            "pytest is configured or declared; an environment may be needed.",
        )
    if name == "ruff":
        for category, action in ((C.LINT, "check"), (C.FORMAT, "format")):
            yield _suggest(
                category,
                ("ruff", action, "."),
                path,
                indicator,
                "Ruff is configured or declared; an environment may be needed.",
            )


def _entry_commands(
    entry_points: PythonEntryPoints,
    projects: set[str],
    gunicorn_sources: dict[str, list[Evidence]],
):
    for entry in entry_points.entries:
        path = entry.evidence[0].path
        parent = PurePosixPath(path).parent
        cwd = next(
            (
                part.as_posix()
                for part in (parent, *parent.parents)
                if part.as_posix() in projects
            ),
            ".",
        )
        argv = None
        evidence = entry.evidence
        status = S.CANDIDATE
        note = "Source is consistent with this startup candidate."
        kind, target = entry.kind, entry.target
        if entry.state is DetectionState.DETECTED:
            if kind == "console_script":
                name = target.partition(" -> ")[0]
                if _COMMAND_NAME.fullmatch(name):
                    argv, status = (name,), S.EXPLICIT
                    note = "Declared console script; typically available after project installation."
            elif kind == "django_manage":
                argv, cwd = ("python", "manage.py", "runserver"), parent.as_posix()
            elif kind in {
                "asgi",
                "django_asgi",
                "django_wsgi",
                "flask_app",
                "flask_factory",
            } and _TARGET.fullmatch(target):
                if kind == "django_wsgi":
                    if cwd in gunicorn_sources:
                        argv = ("gunicorn", target)
                        evidence += tuple(gunicorn_sources[cwd])
                        note = (
                            "Django WSGI target and a Gunicorn dependency were found."
                        )
                elif kind.startswith("flask_"):
                    argv = ("python", "-m", "flask", "--app", target, "run")
                    note = "Flask target inferred from source; its module must be on the Python import path."
                else:
                    argv = ("python", "-m", "uvicorn", target)
                    if PurePosixPath(path).relative_to(cwd).parts[0] == "src":
                        argv += ("--app-dir", "src")
                    note = "ASGI target inferred from source; Uvicorn must be available in the environment."
            elif kind == "module" and target.startswith("-m "):
                module = target[3:]
                if _TARGET.fullmatch(module + ":main"):
                    if PurePosixPath(path).relative_to(cwd).parts[0] == "src":
                        cwd = (PurePosixPath(cwd) / "src").as_posix()
                    argv = ("python", "-m", module)
            elif kind == "module" and PurePosixPath(path).name == "__main__.py":
                argv, cwd = ("python", "."), parent.as_posix()
        if argv is None:
            status = S.UNKNOWN
            note = "Source evidence does not establish a supported startup command."
        yield DevelopmentCommand(C.START, argv, cwd, status, evidence, note)


def _merge(commands: list[DevelopmentCommand]) -> tuple[DevelopmentCommand, ...]:
    category_order = {category: index for index, category in enumerate(C)}
    status_order = {status: index for index, status in enumerate(S)}
    merged = {}
    for item in sorted(
        commands,
        key=lambda item: (
            category_order[item.category],
            status_order[item.status],
            item.cwd,
            item.argv or (),
            item.note,
        ),
    ):
        key = item.category, item.cwd, item.argv, item.note if item.argv is None else ""
        if key in merged:
            first = merged[key]
            evidence = set(first.evidence) | set(item.evidence)
            merged[key] = replace(
                first,
                evidence=tuple(
                    sorted(
                        evidence, key=lambda e: (e.path, e.indicator, e.detail or "")
                    )
                ),
            )
        else:
            merged[key] = item
    return tuple(merged.values())


def discover_development_workflows(
    target: InspectionTarget,
    inventory: DiscoveryInventory,
    entry_points: PythonEntryPoints,
) -> DevelopmentWorkflows:
    """Project likely commands from the existing inventory and entry-point records."""
    commands = []
    skipped = []
    projects = set()
    gunicorn_sources: dict[str, list[Evidence]] = defaultdict(list)
    lock_dirs = set()
    configs = []
    for path in sorted(set(inventory.files)):
        name = PurePosixPath(path).name
        if name in _LOCKS:
            commands.append(
                _suggest(
                    C.INSTALL,
                    _LOCKS[name],
                    path,
                    "Lockfile present",
                    "Lockfile suggests this package manager.",
                )
            )
            if name == "uv.lock":
                lock_dirs.add(_cwd(path))
        elif name in _CONFIGS or _REQUIREMENTS.fullmatch(name):
            configs.append((path, name))
            if name == "pyproject.toml":
                projects.add(_cwd(path))

    for path, name in configs[:_MAX_CONFIGS]:
        try:
            text = read_inventory_text(target.path, path)
            if text is None:
                skipped.append(path)
                continue
            if name == "pyproject.toml":
                data = tomllib.loads(text)
                commands.extend(_manifest_commands(path, data))
            elif name == "Makefile":
                commands.extend(_make_targets(path, text))
            elif name in {"pytest.ini", "tox.ini"}:
                ini = ConfigParser(interpolation=None)
                ini.read_string(text)
                if ini.has_section("pytest"):
                    commands.extend(_tool_commands("pytest", path, "[pytest]"))
                if name == "tox.ini":
                    commands.extend(_tox_commands(path, ini))
            else:
                commands.append(
                    _suggest(
                        C.INSTALL,
                        ("python", "-m", "pip", "install", "-r", name),
                        path,
                        "Requirements file",
                        "File name suggests a pip-compatible requirements input.",
                    )
                )
            if name == "pyproject.toml" or _REQUIREMENTS.fullmatch(name):
                dependencies = {
                    item.subject for item in parse_manifest(path, text).declarations
                }
                if "gunicorn" in dependencies:
                    gunicorn_sources[_cwd(path)].append(
                        Evidence(path, "Declared gunicorn dependency")
                    )
                for tool in sorted(dependencies & {"pytest", "ruff"}):
                    commands.extend(
                        _tool_commands(tool, path, f"Declared {tool} dependency")
                    )
        except (ValueError, OSError, IniError, RecursionError):
            skipped.append(path)

    commands = [
        replace(item, argv=("uv", "sync", "--locked"))
        if item.argv == ("uv", "sync") and item.cwd in lock_dirs
        else item
        for item in commands
    ]
    commands.extend(_entry_commands(entry_points, projects, gunicorn_sources))
    present = {item.category for item in commands}
    commands.extend(
        DevelopmentCommand(
            category, None, ".", S.UNKNOWN, (), "No supported evidence found."
        )
        for category in C
        if category not in present
    )
    return DevelopmentWorkflows(
        _merge(commands), tuple(sorted(skipped)), len(configs) > _MAX_CONFIGS
    )
