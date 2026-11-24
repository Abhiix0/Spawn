"""Internal Python entry-point projection over an existing inspection inventory.

Detected records describe static declarations, not runnable or installed apps.
Unknown records retain evidence when a declaration cannot be resolved statically.
"""

from __future__ import annotations

import ast
import keyword
import re
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterator

from spawn.inspection._reading import MAX_FILE_SIZE, read_inventory_text
from spawn.inspection.models import (
    DetectionState,
    DiscoveryInventory,
    Evidence,
    InspectionTarget,
)

_MAX_FILES = 2_000
_MAX_TEXT = 32_000_000
_ASGI = {
    "fastapi.FastAPI",
    "fastapi.applications.FastAPI",
    "starlette.applications.Starlette",
}
_FLASK = {"flask.Flask", "flask.app.Flask"}
_DJANGO = {
    "asgi.py": ("django_asgi", "django.core.asgi.get_asgi_application"),
    "wsgi.py": ("django_wsgi", "django.core.wsgi.get_wsgi_application"),
}
_MANAGE = "django.core.management.execute_from_command_line"


@dataclass(frozen=True)
class PythonEntryPoint:
    kind: str
    target: str
    state: DetectionState
    evidence: tuple[Evidence, ...]
    reason: str


@dataclass(frozen=True)
class PythonEntryPoints:
    entries: tuple[PythonEntryPoint, ...]
    skipped: tuple[str, ...]
    truncated: bool


def _identifier(value: str) -> bool:
    return value.isidentifier() and not keyword.iskeyword(value)


def _dotted(value: str) -> bool:
    return len(value) <= 256 and all(map(_identifier, value.split(".")))


def _module(path: str, base: str) -> str | None:
    parts = path.removeprefix(base).removesuffix(".py").split("/")
    if len(parts) > 1 and parts[0] == "src":
        parts.pop(0)
    if parts[-1] in {"__init__", "__main__"}:
        parts.pop()
    return ".".join(parts) if parts and all(map(_identifier, parts)) else None


def _scope_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """Visit bindings in this scope without descending into nested definitions."""
    pending = [node]
    while pending:
        current = pending.pop()
        yield current
        if not isinstance(
            current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
        ):
            pending.extend(ast.iter_child_nodes(current))


def _bound(node: ast.AST) -> Iterator[str]:
    for child in _scope_nodes(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
            yield child.id
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield child.name
        elif isinstance(child, (ast.Import, ast.ImportFrom)):
            for alias in child.names:
                yield alias.asname or alias.name.split(".")[0]
        elif (
            isinstance(child, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar))
            and child.name
        ):
            yield child.name
        elif isinstance(child, ast.MatchMapping) and child.rest:
            yield child.rest


def _assign(node: ast.stmt) -> tuple[str, ast.expr] | None:
    if (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    ):
        return node.targets[0].id, node.value
    if (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.value is not None
    ):
        return node.target.id, node.value
    return None


def _imports(node: ast.stmt) -> Iterator[tuple[str, str]]:
    if isinstance(node, ast.Import):
        for alias in node.names:
            root = alias.name.split(".")[0]
            yield (alias.asname, alias.name) if alias.asname else (root, root)
    elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        for alias in node.names:
            if alias.name != "*":
                yield alias.asname or alias.name, f"{node.module}.{alias.name}"


def _qualified(node: ast.expr, aliases: dict[str, str]) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name) and node.id in aliases:
        return ".".join([aliases[node.id], *reversed(parts)])
    return ""


def _constructor(value: ast.expr, aliases: dict[str, str]) -> str:
    return _qualified(value.func, aliases) if isinstance(value, ast.Call) else ""


def _main_guard(node: ast.stmt) -> bool:
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    test = node.test
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    left, right = test.left, test.comparators[0]
    if isinstance(left, ast.Constant):
        left, right = right, left
    return (
        isinstance(left, ast.Name)
        and left.id == "__name__"
        and isinstance(right, ast.Constant)
        and right.value == "__main__"
    )


def _settings(body: list[ast.stmt], aliases: dict[str, str]) -> tuple[str, int] | None:
    refs = []
    for stmt in body:
        value = None
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if (
                _qualified(call.func, aliases) == "os.environ.setdefault"
                and len(call.args) == 2
                and isinstance(call.args[0], ast.Constant)
                and call.args[0].value == "DJANGO_SETTINGS_MODULE"
            ):
                value = call.args[1]
        elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            dest = stmt.targets[0]
            if (
                isinstance(dest, ast.Subscript)
                and _qualified(dest.value, aliases) == "os.environ"
                and isinstance(dest.slice, ast.Constant)
                and dest.slice.value == "DJANGO_SETTINGS_MODULE"
            ):
                value = stmt.value
        if value is not None:
            refs.append(
                (value.value if isinstance(value, ast.Constant) else None, stmt.lineno)
            )
    if len(refs) == 1 and isinstance(refs[0][0], str) and _dotted(refs[0][0]):
        return refs[0]
    return None


def _line(path: str, indicator: str, line: int) -> Evidence:
    return Evidence(path, indicator, f"line {line}")


def _flask_factory(
    node: ast.FunctionDef, aliases: dict[str, str]
) -> tuple[int, bool] | None:
    counts = Counter(name for stmt in node.body for name in _bound(stmt))
    counts.update(arg.arg for arg in ast.walk(node.args) if isinstance(arg, ast.arg))
    aliases = {name: value for name, value in aliases.items() if name not in counts}
    instances: dict[str, int] = {}
    evidence = None
    for stmt in node.body:
        aliases.update(
            (name, value) for name, value in _imports(stmt) if counts[name] == 1
        )
        assignment = _assign(stmt)
        if assignment and _constructor(assignment[1], aliases) in _FLASK:
            evidence = stmt.lineno
            if counts[assignment[0]] == 1:
                instances[assignment[0]] = evidence
        if isinstance(stmt, ast.Return) and stmt.value is not None:
            if _constructor(stmt.value, aliases) in _FLASK:
                evidence = stmt.lineno
            elif isinstance(stmt.value, ast.Name) and stmt.value.id in instances:
                evidence = instances[stmt.value.id]
            else:
                if any(
                    isinstance(item, ast.Call) and _constructor(item, aliases) in _FLASK
                    for item in ast.walk(stmt.value)
                ):
                    evidence = stmt.lineno
                return (evidence, False) if evidence is not None else None
            returns = sum(
                isinstance(child, ast.Return)
                for item in node.body
                for child in _scope_nodes(item)
            )
            return evidence, returns == 1 and not node.decorator_list
    return (evidence, False) if evidence is not None else None


def _module_entries(
    path: str, module: str | None, tree: ast.Module, bindings: Counter[str]
) -> tuple[
    list[PythonEntryPoint],
    list[tuple[str, str, tuple[Evidence, ...], tuple[str, int] | None]],
]:
    entries = []
    django = []
    filename = path.rsplit("/", 1)[-1]
    aliases: dict[str, str] = {}
    managers: dict[str, tuple[int, tuple[str, int] | None]] = {}
    guards = []

    for index, node in enumerate(tree.body):
        aliases.update(
            (name, value) for name, value in _imports(node) if bindings[name] == 1
        )
        assignment = _assign(node)
        if module is not None and assignment:
            name, value = assignment
            constructor = _constructor(value, aliases)
            framework = (
                "asgi"
                if constructor in _ASGI
                else "flask_app"
                if constructor in _FLASK
                else None
            )
            if framework is None:
                candidates = {
                    "asgi" if called in _ASGI else "flask_app"
                    for item in ast.walk(value)
                    if isinstance(item, ast.Call)
                    if (called := _constructor(item, aliases)) in _ASGI | _FLASK
                }
            else:
                candidates = {framework}
            for kind in sorted(candidates):
                direct = framework is not None and bindings[name] == 1
                entries.append(
                    PythonEntryPoint(
                        kind,
                        f"{module}:{name}",
                        DetectionState.DETECTED if direct else DetectionState.UNKNOWN,
                        (
                            _line(
                                path,
                                "Framework constructor in module assignment",
                                node.lineno,
                            ),
                        ),
                        "Direct constructor assignment"
                        if direct
                        else "Assignment value or binding is ambiguous",
                    )
                )
            if (
                filename in _DJANGO
                and name == "application"
                and constructor == _DJANGO[filename][1]
            ):
                kind, _ = _DJANGO[filename]
                settings = (
                    _settings(tree.body[:index], aliases)
                    if bindings[name] == 1
                    else None
                )
                django.append(
                    (
                        kind,
                        f"{module}:{name}",
                        (_line(path, "Django application constructor", node.lineno),),
                        settings,
                    )
                )
        if isinstance(node, ast.FunctionDef):
            if module is not None:
                factory = _flask_factory(node, aliases)
                if factory:
                    line, direct = factory
                    direct &= bindings[node.name] == 1
                    entries.append(
                        PythonEntryPoint(
                            "flask_factory",
                            f"{module}:{node.name}",
                            DetectionState.DETECTED
                            if direct
                            else DetectionState.UNKNOWN,
                            (_line(path, "Flask constructor in factory", line),),
                            "Factory directly returns a Flask instance"
                            if direct
                            else "Factory result is ambiguous",
                        )
                    )
            if filename == "manage.py" and bindings[node.name] == 1:
                local_counts = Counter(
                    name for stmt in node.body for name in _bound(stmt)
                )
                local_counts.update(
                    arg.arg for arg in ast.walk(node.args) if isinstance(arg, ast.arg)
                )
                local = {
                    name: value
                    for name, value in aliases.items()
                    if name not in local_counts
                }
                for position, stmt in enumerate(node.body):
                    imports = stmt.body if isinstance(stmt, ast.Try) else [stmt]
                    local.update(
                        (name, value)
                        for item in imports
                        for name, value in _imports(item)
                        if local_counts[name] == 1
                    )
                    if (
                        isinstance(stmt, ast.Expr)
                        and _constructor(stmt.value, local) == _MANAGE
                    ):
                        managers[node.name] = (
                            stmt.lineno,
                            _settings(node.body[:position], local),
                        )
        if (
            bindings["__name__"] == 0
            and _main_guard(node)
            and any(
                not isinstance(stmt, ast.Pass)
                and not (
                    isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)
                )
                for stmt in node.body
            )
        ):
            guard = _line(path, "__main__ guard", node.lineno)
            guards.append(guard)
            if filename != "manage.py":
                continue
            for position, stmt in enumerate(node.body):
                if not isinstance(stmt, ast.Expr) or not isinstance(
                    stmt.value, ast.Call
                ):
                    continue
                function = stmt.value.func
                if isinstance(function, ast.Name) and function.id in managers:
                    line, settings = managers[function.id]
                elif _constructor(stmt.value, aliases) == _MANAGE:
                    line = stmt.lineno
                    settings = _settings(
                        tree.body[:index] + node.body[:position], aliases
                    )
                else:
                    continue
                django.append(
                    (
                        "django_manage",
                        path,
                        (_line(path, "Django management command", line), guard),
                        settings,
                    )
                )

    if filename == "__main__.py" or guards:
        evidence = tuple(guards)
        if filename == "__main__.py":
            evidence = (Evidence(path, "Python __main__.py"), *evidence)
        entries.append(
            PythonEntryPoint(
                "module",
                f"-m {module}" if module else path,
                DetectionState.DETECTED,
                evidence,
                "Python module execution convention"
                if filename == "__main__.py"
                else "Explicit __main__ guard",
            )
        )
    return entries, django


def _paths(base: str, module: str) -> Iterator[str]:
    stem = module.replace(".", "/")
    for root in (base, base + "src/"):
        yield root + stem + ".py"
        yield root + stem + "/__init__.py"


def discover_python_entry_points(
    target: InspectionTarget,
    inventory: DiscoveryInventory,
) -> PythonEntryPoints:
    """Analyze only files in the supplied inventory, with no new discovery walk."""
    entries: list[PythonEntryPoint] = []
    skipped: list[str] = []
    manifests = {p for p in inventory.files if p.rsplit("/", 1)[-1] == "pyproject.toml"}
    source_paths = {p for p in inventory.files if p.endswith(".py")}
    ordered = sorted(manifests) + sorted(source_paths)
    projects: dict[str, dict] = {}
    definitions: dict[str, dict[str, int]] = {}
    django = []
    remaining = _MAX_TEXT
    truncated = len(ordered) > _MAX_FILES
    for path in ordered[:_MAX_FILES]:
        if remaining <= 0:
            truncated = True
            break
        try:
            content = read_inventory_text(target.path, path)
            if content is None:
                remaining -= MAX_FILE_SIZE
                skipped.append(path)
                continue
            remaining -= len(content)
            if remaining < 0:
                truncated = True
                break
            if path in manifests:
                project = tomllib.loads(content).get("project")
                scripts = project.get("scripts") if isinstance(project, dict) else None
                if isinstance(scripts, dict):
                    projects[path] = scripts
                continue
            tree = ast.parse(content)
        except UnicodeDecodeError:
            remaining -= MAX_FILE_SIZE
            skipped.append(path)
            continue
        except (OSError, ValueError, SyntaxError, RecursionError):
            skipped.append(path)
            continue
        parent = PurePosixPath(path).parent
        parents = (parent, *parent.parents)
        bases = [base.as_posix() + "/" if base.parts else "" for base in parents]
        base = next(
            (base for base in bases if base + "pyproject.toml" in manifests), ""
        )
        bindings = Counter(name for node in tree.body for name in _bound(node))
        definitions[path] = {
            node.name: node.lineno
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            and bindings[node.name] == 1
        }
        found, django_found = _module_entries(path, _module(path, base), tree, bindings)
        entries.extend(found)
        django.extend((bases, *item) for item in django_found)

    for manifest, scripts in projects.items():
        base = manifest.removesuffix("pyproject.toml")
        for name, reference in scripts.items():
            if not re.fullmatch(r"[\w.-]{1,128}", name):
                continue
            evidence = (Evidence(manifest, f"[project.scripts] {name}"),)
            module, _, attr = (
                reference.partition(":") if isinstance(reference, str) else ("", "", "")
            )
            valid = _dotted(module) and _dotted(attr)
            matches = (
                [path for path in _paths(base, module) if path in source_paths]
                if valid
                else []
            )
            line = (
                definitions.get(matches[0], {}).get(attr) if len(matches) == 1 else None
            )
            if line is not None:
                evidence += (_line(matches[0], "Top-level script object", line),)
            entries.append(
                PythonEntryPoint(
                    "console_script",
                    f"{name} -> {module}:{attr}" if valid else name,
                    DetectionState.DETECTED
                    if line is not None
                    else DetectionState.UNKNOWN,
                    evidence,
                    "Declared script with a local object"
                    if line is not None
                    else "Script target could not be confirmed locally",
                )
            )

    for bases, kind, display, evidence, settings in django:
        matches = []
        if settings is not None:
            module, line = settings
            evidence += (
                _line(evidence[0].path, "Literal DJANGO_SETTINGS_MODULE", line),
            )
            for base in bases:
                matches = [
                    path for path in _paths(base, module) if path in source_paths
                ]
                if matches:
                    break
        confirmed = len(matches) == 1 and matches[0] in definitions
        if confirmed:
            evidence += (Evidence(matches[0], "Referenced Django settings module"),)
        entries.append(
            PythonEntryPoint(
                kind,
                display,
                DetectionState.DETECTED if confirmed else DetectionState.UNKNOWN,
                evidence,
                "Django bootstrap references a local settings module"
                if confirmed
                else "Django settings could not be confirmed locally",
            )
        )

    # Keep separate origins when independent projects expose the same target.
    unique: dict[tuple[str, str, str], list[PythonEntryPoint]] = defaultdict(list)
    for entry in entries:
        unique[entry.kind, entry.target, entry.evidence[0].path].append(entry)
    result = []
    for _, group in sorted(unique.items()):
        entry = group[0]
        if len(group) > 1:
            evidence = tuple(
                dict.fromkeys(item for record in group for item in record.evidence)
            )
            entry = PythonEntryPoint(
                entry.kind,
                entry.target,
                DetectionState.UNKNOWN,
                evidence,
                "Multiple declarations for this target",
            )
        result.append(entry)
    return PythonEntryPoints(tuple(result), tuple(sorted(skipped)), truncated)
