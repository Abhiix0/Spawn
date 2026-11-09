"""Evidence-based static framework detection; inspected code is never executed."""

from __future__ import annotations

import ast
import json
import re
import tomllib
import warnings
from pathlib import Path

from spawn.inspection.languages import read_text_bounded, table
from spawn.inspection.models import (
    AnalysisStatus,
    AnalyzerResult,
    DetectionState,
    Diagnostic,
    Evidence,
    Finding,
    FindingCategory,
    InspectionTarget,
    DiscoveryInventory,
)

PACKAGE_RULES = {
    "react": {"react"},
    "nextjs": {"next"},
    "vue": {"vue"},
    "nuxt": {"nuxt"},
    "angular": {"@angular/core"},
    "svelte": {"svelte"},
    "express": {"express"},
    "fastapi": {"fastapi"},
    "flask": {"flask"},
    "django": {"django"},
    "starlette": {"starlette"},
    "pydantic": {"pydantic"},
    "rails": {"rails"},
    "laravel": {"laravel/framework"},
}
MAX_CANDIDATE_LINE_LENGTH = 1000

IMPORTS = {
    "react": r"(?m)^[ \t]*import\s+(?>[^;'\r\n]*?\bfrom\s+)['\"]react(?:/[^'\"]*)?['\"]",
    "nextjs": r"(?m)^[ \t]*import\s+(?>[^;'\r\n]*?\bfrom\s+)['\"]next(?:/[^'\"]*)?['\"]",
    "vue": r"(?m)^[ \t]*import\s+(?>[^;'\r\n]*?\bfrom\s+)['\"]vue['\"]",
    "nuxt": r"(?m)^[ \t]*import\s+(?>[^;'\r\n]*?\bfrom\s+)['\"]nuxt(?:/[^'\"]*)?['\"]",
    "angular": r"(?m)^[ \t]*import\s+(?>[^;'\r\n]*?\bfrom\s+)['\"]@angular/",
    "svelte": r"(?m)^[ \t]*import\s+(?>[^;'\r\n]*?\bfrom\s+)['\"]svelte(?:/[^'\"]*)?['\"]",
    "express": r"(?m)^[ \t]*(?:import\s+(?>[^;'\r\n]*?\bfrom\s+)|const\s+(?>\w+\s*=\s*require\s*\()\s*)['\"]express['\"]",
}
PY_IMPORT_MODULES = frozenset({"django", "fastapi", "flask", "pydantic", "starlette"})
CONFIGS = {
    "nextjs": {"next.config.js", "next.config.mjs", "next.config.ts"},
    "nuxt": {"nuxt.config.js", "nuxt.config.ts"},
    "angular": {"angular.json"},
    "svelte": {"svelte.config.js"},
    "django": {"manage.py"},
}
MANIFESTS = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "Pipfile",
    "composer.json",
    "Gemfile",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}


def _python_imported_frameworks(text: str) -> set[str]:
    """Top-level framework modules really imported; strings and comments never count."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # inspected code may emit SyntaxWarning
        tree = ast.parse(text)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
    return {n.split(".", 1)[0] for n in names} & PY_IMPORT_MODULES


def _py_name(spec: str) -> str | None:
    """PEP 508 distribution name, PEP 503-normalized."""
    m = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", spec.strip())
    return re.sub(r"[-_.]+", "-", m.group()).lower() if m else None


def _py_names(specs: object) -> set[str]:
    items = specs if isinstance(specs, list) else list(specs)
    names = {_py_name(s) for s in items if isinstance(s, str)}
    return {n for n in names if n}


def _dependency_names(rel: str, text: str) -> set[str]:
    name = Path(rel).name
    if name == "package.json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("package.json root must be an object")
        return {
            str(pkg).lower()
            for section in (
                "dependencies",
                "devDependencies",
                "peerDependencies",
                "optionalDependencies",
            )
            for pkg in table(data, section)
        }
    if name == "pyproject.toml":
        data = tomllib.loads(text)
        project = table(data, "project")
        specs: list = []
        for dependencies in (
            project.get("dependencies"),
            *table(project, "optional-dependencies").values(),
            *table(data, "dependency-groups").values(),  # include-group dicts skipped
        ):
            if isinstance(dependencies, list):
                specs.extend(dependencies)
        names = _py_names(specs)
        poetry = table(table(data, "tool"), "poetry")
        tables = [table(poetry, s) for s in ("dependencies", "dev-dependencies")]
        tables += [table(g, "dependencies") for g in table(poetry, "group").values()]
        for deps in tables:
            names |= _py_names(k for k in deps if k != "python")
        return names
    if name == "Pipfile":
        data = tomllib.loads(text)
        return _py_names(
            k for s in ("packages", "dev-packages") for k in table(data, s)
        )
    if name in {"requirements.txt", "requirements-dev.txt"}:
        return _py_names(
            line
            for line in text.splitlines()
            if not line.lstrip().startswith(("#", "-", "\\"))
        )
    if name == "composer.json":
        data = json.loads(text)
        return {
            str(k).lower()
            for section in ("require", "require-dev")
            for k in table(data, section)
        }
    return set()


class FrameworkDetector:
    """Detect a bounded set of frameworks from declarations, imports and configs.

    Manifest-only evidence is inferred. Source imports and framework-specific
    config/entrypoint files are detected. Neither state asserts runtime health.
    """

    name = "framework"

    def run(
        self, target: InspectionTarget, inventory: DiscoveryInventory
    ) -> AnalyzerResult:
        found: dict[str, dict[str, Evidence]] = {}
        direct: set[str] = set()  # frameworks with import/config evidence
        diagnostics: list[Diagnostic] = []
        try:
            for rel in inventory.files:
                self._scan(target, rel, found, direct, diagnostics)
        except Exception as exc:  # noqa: BLE001 - run() must never raise
            diagnostics.append(
                Diagnostic(
                    "framework.internal_error",
                    f"Internal error ({type(exc).__name__}).",
                    "error",
                    self.name,
                    fatal=True,
                )
            )
        findings = tuple(
            Finding(
                FindingCategory.FRAMEWORK,
                framework,
                DetectionState.DETECTED
                if framework in direct
                else DetectionState.INFERRED,
                tuple(sorted(items.values(), key=lambda e: e.path)),
                None
                if framework in direct
                else "A framework dependency is declared, but no matching import or dedicated configuration was found.",
            )
            for framework, items in sorted(found.items())
        )
        if any(d.fatal for d in diagnostics):
            status = AnalysisStatus.FAILED
        else:
            status = AnalysisStatus.PARTIAL if diagnostics else AnalysisStatus.COMPLETE
        return AnalyzerResult(self.name, status, findings, tuple(diagnostics))

    def _scan(self, target, rel, found, direct, diagnostics) -> None:
        path = Path(rel)
        name = path.name
        is_source = path.suffix.lower() in SOURCE_SUFFIXES
        if (
            name not in MANIFESTS
            and not is_source
            and not any(name in names for names in CONFIGS.values())
        ):
            return
        try:
            text = read_text_bounded(target.path / rel)
        except (OSError, UnicodeError) as exc:
            diagnostics.append(
                Diagnostic(
                    "framework.unreadable_file",
                    f"Could not read file ({type(exc).__name__}).",
                    "warning",
                    self.name,
                    rel,
                )
            )
            return
        if text is None:
            diagnostics.append(
                Diagnostic(
                    "framework.file_too_large",
                    "File exceeds 1 MB limit; skipped.",
                    "warning",
                    self.name,
                    rel,
                )
            )
            return
        deps: set[str] = set()
        if name in MANIFESTS:
            try:
                deps = _dependency_names(rel, text)
            except ValueError as exc:  # JSON and TOML decode errors are ValueErrors
                diagnostics.append(
                    Diagnostic(
                        "framework.malformed_manifest",
                        f"Could not parse manifest ({type(exc).__name__}).",
                        "warning",
                        self.name,
                        rel,
                    )
                )
        for framework, packages in PACKAGE_RULES.items():
            if deps & packages:
                found.setdefault(framework, {})[rel] = Evidence(
                    rel, "framework dependency declared in manifest"
                )
        if path.suffix.lower() == ".py":
            try:
                imported = _python_imported_frameworks(text)
            except (SyntaxError, ValueError, RecursionError) as exc:
                diagnostics.append(
                    Diagnostic(
                        "framework.unparseable_source",
                        f"Could not parse Python source ({type(exc).__name__}); imports not analyzed.",
                        "warning",
                        self.name,
                        rel,
                    )
                )
                imported = set()
            for framework in sorted(imported):
                direct.add(framework)
                found.setdefault(framework, {})[rel] = Evidence(
                    rel, f"static import/declaration for {framework}"
                )
        elif is_source:
            for line in text.splitlines():
                if len(line) > MAX_CANDIDATE_LINE_LENGTH:
                    continue
                if "import" not in line and "require" not in line:
                    continue
                for framework, pattern in IMPORTS.items():
                    if framework in direct:
                        continue
                    if re.search(pattern, line):
                        direct.add(framework)
                        found.setdefault(framework, {})[rel] = Evidence(
                            rel, f"static import/declaration for {framework}"
                        )
        for framework, names in CONFIGS.items():
            if name in names:
                direct.add(framework)
                found.setdefault(framework, {})[rel] = Evidence(
                    rel, f"recognized {name} configuration/entry-point indicator"
                )
