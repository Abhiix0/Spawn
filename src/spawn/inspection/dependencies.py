"""Static dependency and package-manager inspection (Issue #56).

Emits one DEPENDENCY finding per directly declared package and PACKAGE_MANAGER
findings (pip, uv, poetry, pipenv, npm, yarn, pnpm, bun). Files come only from
``DiscoveryInventory.files``; each is read in binary with a 1 MB bound.

Supported (everything else is omitted, never guessed):
- pyproject.toml: [project].dependencies, [project.optional-dependencies].*,
  [dependency-groups].* (strings only; include-group tables are skipped),
  [tool.poetry].dependencies / dev-dependencies / group.*.dependencies
  ("python" skipped), [tool.uv].dev-dependencies. A [project].dynamic entry
  "dependencies" yields ``dependency.dynamic_metadata`` and no guesses.
- requirements.txt and requirements-*.txt at any depth.
- package.json: dependencies, devDependencies, peerDependencies,
  optionalDependencies.

Not supported (no findings): Pipfile, setup.py, setup.cfg, any lockfile as a
dependency source, Cargo.toml, go.mod, Gemfile, composer.json, pom.xml, gradle.
Lockfiles and Pipfile are used for package-manager presence only and are never
read.

Subjects: Python names are PEP 503 normalized; npm names are lowercased with
the @scope/ prefix kept. Known limitation: a pip and an npm package with the
same name share one (category, subject) identity and merge into one finding.

Package managers: lockfiles / [tool.uv] / [tool.poetry] / package.json
"packageManager" are DETECTED; a requirements file only INFERS pip. Several
managers are all reported; none is declared the winner.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path, PurePosixPath
from typing import NamedTuple

from spawn.inspection._reading import MAX_FILE_SIZE, read_text_limited
from spawn.inspection.models import (
    AnalysisStatus,
    AnalyzerResult,
    DetectionState,
    Diagnostic,
    DiscoveryInventory,
    Evidence,
    Finding,
    FindingCategory,
    InspectionTarget,
)
from spawn.utils.redact import redact_url

MAX_MANIFESTS = 500
_MAX_DETAIL = 200
_MAX_CONTINUATIONS = 100

_LOCKFILE_MANAGERS = {
    "uv.lock": "uv",
    "poetry.lock": "poetry",
    "Pipfile": "pipenv",
    "Pipfile.lock": "pipenv",
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "pnpm-workspace.yaml": "pnpm",
    "bun.lock": "bun",
    "bun.lockb": "bun",
}
_JS_MANAGERS = frozenset({"npm", "yarn", "pnpm", "bun"})
_NPM_SECTIONS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
)

_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
_PEP508 = re.compile(rf"^({_NAME})\s*(?:\[[^\]]*\])?\s*(.*)$")
_EGG = re.compile(rf"[#&]egg=({_NAME})")
_EDITABLE = re.compile(r"(?:-e|--editable)[\s=]+(.*)")
_COMMENT = re.compile(r"(^|\s)#.*$")
_INLINE_OPTION = re.compile(r"\s--[A-Za-z]")


class Declaration(NamedTuple):
    subject: str
    section: str  # e.g. "[project.dependencies]", "package.json devDependencies"
    detail: str | None


class Problem(NamedTuple):
    code: str
    message: str


class Manifest(NamedTuple):
    declarations: list[Declaration]
    managers: list[tuple[str, str]]  # (manager, indicator)
    problems: list[Problem]


def _py_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _clean(spec: object) -> str | None:
    if not isinstance(spec, str) or not spec.strip():
        return None
    return redact_url(spec.strip())[:_MAX_DETAIL]


def _unsupported(count: int) -> Problem:
    return Problem(
        "dependency.unsupported_syntax",
        f"{count} entries use unsupported syntax; skipped.",
    )


def _malformed(message: str = "Could not parse manifest.") -> Problem:
    return Problem("dependency.malformed_manifest", message)


def _parse_requirement(text: str) -> tuple[str, str | None] | None:
    """Parse a PEP 508 string into (name, specifier-or-url); None if unparseable."""
    m = _PEP508.match(text.split(";", 1)[0].strip())
    if not m:
        return None
    name, rest = m.group(1), m.group(2).strip()
    if rest.startswith("@"):
        rest = rest[1:].strip()
    elif rest.startswith("(") and rest.endswith(")"):
        rest = rest[1:-1].strip()
    elif rest and rest[0] not in "<>=!~":
        return None
    return name, _clean(rest)


def parse_manifest(rel: str, text: str) -> Manifest:
    """Parse one manifest (pure, no I/O). ``rel`` is the inventory path."""
    base = PurePosixPath(rel).name
    out = Manifest([], [], [])
    if base == "pyproject.toml":
        _parse_pyproject(text, out)
    elif base == "package.json":
        _parse_package_json(text, out)
    else:
        _parse_requirements(base, text, out)
    return out


def _parse_pyproject(text: str, out: Manifest) -> None:
    if not text.strip():
        return
    try:
        data = tomllib.loads(text)
    except ValueError:
        out.problems.append(_malformed())
        return
    bad = 0

    def add_list(items: object, section: str) -> None:
        nonlocal bad
        if not isinstance(items, list):
            bad += items is not None
            return
        for item in items:
            if isinstance(item, dict):  # include-group tables carry no package
                continue
            parsed = _parse_requirement(item) if isinstance(item, str) else None
            if parsed:
                out.declarations.append(
                    Declaration(_py_name(parsed[0]), section, parsed[1])
                )
            else:
                bad += 1

    def add_poetry(deps: object, section: str) -> None:
        if not isinstance(deps, dict):
            return
        for name, spec in deps.items():
            if name.lower() == "python":
                continue
            if isinstance(spec, dict):
                spec = spec.get("version")
            out.declarations.append(Declaration(_py_name(name), section, _clean(spec)))

    project = data.get("project")
    project = project if isinstance(project, dict) else {}
    dynamic = project.get("dynamic")
    if isinstance(dynamic, list) and "dependencies" in dynamic:
        out.problems.append(
            Problem(
                "dependency.dynamic_metadata",
                "Dependencies are dynamic; not evaluated.",
            )
        )
    add_list(project.get("dependencies"), "[project.dependencies]")
    extras = project.get("optional-dependencies")
    for extra, items in (extras if isinstance(extras, dict) else {}).items():
        add_list(items, f"[project.optional-dependencies.{extra}]")
    groups = data.get("dependency-groups")
    for group, items in (groups if isinstance(groups, dict) else {}).items():
        add_list(items, f"[dependency-groups.{group}]")

    tool = data.get("tool")
    tool = tool if isinstance(tool, dict) else {}
    poetry, uv = tool.get("poetry"), tool.get("uv")
    if isinstance(poetry, dict):
        out.managers.append(("poetry", "[tool.poetry] section"))
        add_poetry(poetry.get("dependencies"), "[tool.poetry.dependencies]")
        add_poetry(poetry.get("dev-dependencies"), "[tool.poetry.dev-dependencies]")
        pgroups = poetry.get("group")
        for group, body in (pgroups if isinstance(pgroups, dict) else {}).items():
            if isinstance(body, dict):
                add_poetry(
                    body.get("dependencies"),
                    f"[tool.poetry.group.{group}.dependencies]",
                )
    if isinstance(uv, dict):
        out.managers.append(("uv", "[tool.uv] section"))
        add_list(uv.get("dev-dependencies"), "[tool.uv.dev-dependencies]")
    if bad:
        out.problems.append(_unsupported(bad))


def _parse_package_json(text: str, out: Manifest) -> None:
    if not text.strip():
        return
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if not isinstance(data, dict):
        out.problems.append(_malformed())
        return
    bad_section = False
    for key in _NPM_SECTIONS:
        if key not in data:
            continue
        deps = data[key]
        if not isinstance(deps, dict):
            bad_section = True
            continue
        for name, spec in deps.items():
            out.declarations.append(
                Declaration(name.lower(), f"package.json {key}", _clean(spec))
            )
    pm = data.get("packageManager")
    manager = pm.split("@", 1)[0] if isinstance(pm, str) else None
    if manager in _JS_MANAGERS:
        out.managers.append((manager, "package.json packageManager field"))
    if bad_section:
        out.problems.append(_malformed("A dependency section is not an object."))


def _parse_requirements(base: str, text: str, out: Manifest) -> None:
    out.managers.append(("pip", "pip-compatible requirements file"))
    lines: list[str] = []
    buf: list[str] = []
    for raw in text.splitlines():
        if raw.endswith("\\") and len(buf) < _MAX_CONTINUATIONS:
            buf.append(raw[:-1])
            continue
        lines.append("".join(buf) + raw)
        buf = []
    if buf:
        lines.append("".join(buf))
    bad = 0
    for line in lines:
        line = _COMMENT.sub("", line).strip()
        if not line:
            continue
        editable = _EDITABLE.match(line)
        if editable:
            target = editable.group(1)
        elif line.startswith("-"):
            continue  # -r, -c, --index-url, ... carry no package
        else:
            target = line
        target = _INLINE_OPTION.split(target)[0].strip()
        if target[:1] in (".", "/", "\\") or (editable and "://" not in target):
            continue  # local path
        egg = _EGG.search(target)
        if egg:
            parsed = (egg.group(1), _clean(target.split("#", 1)[0]))
        else:
            parsed = _parse_requirement(target)
        if parsed:
            out.declarations.append(Declaration(_py_name(parsed[0]), base, parsed[1]))
        else:
            bad += 1
    if bad:
        out.problems.append(_unsupported(bad))


def _is_manifest(rel: str) -> bool:
    name = PurePosixPath(rel).name
    return name in {"pyproject.toml", "package.json", "requirements.txt"} or (
        name.startswith("requirements-") and name.endswith(".txt")
    )


def _sorted_evidence(items: set[Evidence]) -> tuple[Evidence, ...]:
    return tuple(sorted(items, key=lambda e: (e.path, e.indicator, e.detail or "")))


class DependencyAnalyzer:
    """Declared-dependency and package-manager analyzer (see module docstring)."""

    name = "dependency"

    def run(
        self, target: InspectionTarget, inventory: DiscoveryInventory
    ) -> AnalyzerResult:
        deps: dict[str, set[Evidence]] = {}
        managers: dict[str, set[Evidence]] = {}
        diagnostics: list[Diagnostic] = []

        def warn(code: str, message: str, rel: str | None = None) -> None:
            diagnostics.append(Diagnostic(code, message, "warning", self.name, rel))

        try:
            files = sorted(set(inventory.files))
            for rel in files:
                filename = PurePosixPath(rel).name
                manager = _LOCKFILE_MANAGERS.get(filename)
                if manager:
                    managers.setdefault(manager, set()).add(
                        Evidence(rel, f"{filename} present")
                    )
            manifests = [rel for rel in files if _is_manifest(rel)]
            if len(manifests) > MAX_MANIFESTS:
                manifests = manifests[:MAX_MANIFESTS]
                warn(
                    "dependency.manifest_limit_reached",
                    f"More than {MAX_MANIFESTS} manifests; the rest were skipped.",
                )
            for rel in manifests:
                try:
                    text = read_text_limited(Path(target.path) / rel)
                except UnicodeDecodeError:
                    warn(
                        "dependency.undecodable_file",
                        "File is not valid UTF-8; skipped.",
                        rel,
                    )
                    continue
                except OSError:
                    warn(
                        "dependency.unreadable_file",
                        "File could not be read; skipped.",
                        rel,
                    )
                    continue
                if text is None:
                    warn(
                        "dependency.file_too_large",
                        f"File exceeds {MAX_FILE_SIZE} bytes; skipped.",
                        rel,
                    )
                    continue
                parsed = parse_manifest(rel, text)
                for d in parsed.declarations:
                    deps.setdefault(d.subject, set()).add(
                        Evidence(rel, f"{d.subject} in {d.section}", d.detail)
                    )
                for manager, indicator in parsed.managers:
                    managers.setdefault(manager, set()).add(Evidence(rel, indicator))
                for p in parsed.problems:
                    warn(p.code, p.message, rel)
        except Exception as exc:  # noqa: BLE001 - run() must never raise
            diagnostics.append(
                Diagnostic(
                    "dependency.internal_error",
                    f"Internal error ({type(exc).__name__}).",
                    "error",
                    self.name,
                    fatal=True,
                )
            )
        findings = [
            Finding(
                FindingCategory.DEPENDENCY,
                subject,
                DetectionState.DETECTED,
                _sorted_evidence(evidence),
            )
            for subject, evidence in deps.items()
        ]
        for subject, evidence in managers.items():
            inferred = subject == "pip"
            findings.append(
                Finding(
                    FindingCategory.PACKAGE_MANAGER,
                    subject,
                    DetectionState.INFERRED if inferred else DetectionState.DETECTED,
                    _sorted_evidence(evidence),
                    "pip-compatible requirements file; "
                    "the tool actually used is not confirmed"
                    if inferred
                    else None,
                )
            )
        findings.sort(key=lambda f: (f.category.value, f.subject))
        if any(d.fatal for d in diagnostics):
            status = AnalysisStatus.FAILED
        else:
            status = AnalysisStatus.PARTIAL if diagnostics else AnalysisStatus.COMPLETE
        return AnalyzerResult(self.name, status, tuple(findings), tuple(diagnostics))
