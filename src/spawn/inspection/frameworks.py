"""Evidence-based static framework detection; inspected code is never executed."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

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
IMPORTS = {
    "react": r"(?m)^\s*import\b.*?\bfrom\s*['\"]react(?:/[^'\"]*)?['\"]",
    "nextjs": r"(?m)^\s*import\b.*?\bfrom\s*['\"]next(?:/[^'\"]*)?['\"]",
    "vue": r"(?m)^\s*import\b.*?\bfrom\s*['\"]vue['\"]",
    "nuxt": r"(?m)^\s*import\b.*?\bfrom\s*['\"]nuxt(?:/[^'\"]*)?['\"]",
    "angular": r"(?m)^\s*import\b.*?\bfrom\s*['\"]@angular/",
    "svelte": r"(?m)^\s*import\b.*?\bfrom\s*['\"]svelte(?:/[^'\"]*)?['\"]",
    "express": r"(?m)^\s*(?:import\b.*?\bfrom\s*|const\s+\w+\s*=\s*require\s*\()\s*['\"]express['\"]",
    "fastapi": r"(?m)^\s*(?:from\s+fastapi\s+import\b|import\s+fastapi\b)",
    "flask": r"(?m)^\s*(?:from\s+flask\s+import\b|import\s+flask\b)",
    "django": r"(?m)^\s*(?:from\s+django\b|import\s+django\b)",
    "starlette": r"(?m)^\s*(?:from\s+starlette\b|import\s+starlette\b)",
    "pydantic": r"(?m)^\s*(?:from\s+pydantic\b|import\s+pydantic\b)",
}
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
MAX_FILE_SIZE = 1_000_000


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
            for pkg in (
                data.get(section, {}) if isinstance(data.get(section, {}), dict) else {}
            )
        }
    if name == "pyproject.toml":
        data = tomllib.loads(text)
        names: set[str] = set()
        project = data.get("project", {})
        if isinstance(project, dict) and isinstance(project.get("dependencies"), list):
            for dep in project["dependencies"]:
                if isinstance(dep, str):
                    names.add(
                        re.split(r"[<>=!~;\[]", dep, 1)[0]
                        .strip()
                        .lower()
                        .replace("_", "-")
                    )
        poetry = data.get("tool", {}).get("poetry", {})
        if isinstance(poetry, dict):
            for section in ("dependencies", "dev-dependencies"):
                vals = poetry.get(section, {})
                if isinstance(vals, dict):
                    names.update(
                        str(k).lower().replace("_", "-") for k in vals if k != "python"
                    )
        return names
    if name in {"requirements.txt", "requirements-dev.txt", "Pipfile"}:
        return {
            m.group(1).lower().replace("_", "-")
            for line in text.splitlines()
            if not line.lstrip().startswith(("#", "-", "\\"))
            for m in [re.match(r"\s*([A-Za-z0-9_.-]+)\s*(?:[<>=!~;\[]|$)", line)]
            if m
        }
    if name == "composer.json":
        data = json.loads(text)
        return {
            str(k).lower()
            for section in ("require", "require-dev")
            for k in (
                data.get(section, {})
                if isinstance(data, dict) and isinstance(data.get(section, {}), dict)
                else {}
            )
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
        diagnostics: list[Diagnostic] = []
        for rel in inventory.files:
            path = Path(rel)
            name = path.name
            if (
                name not in MANIFESTS
                and path.suffix.lower()
                not in {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
                and not any(name in names for names in CONFIGS.values())
            ):
                continue
            try:
                text = (target.path / rel).read_text(encoding="utf-8")
                if len(text) > MAX_FILE_SIZE:
                    diagnostics.append(
                        Diagnostic(
                            "framework.file_too_large",
                            "File exceeds 1 MB limit; skipped.",
                            "warning",
                            self.name,
                            rel,
                        )
                    )
                    continue
            except (OSError, UnicodeError) as exc:
                diagnostics.append(
                    Diagnostic(
                        "framework.unreadable_file",
                        f"Could not read file: {exc}",
                        "warning",
                        self.name,
                        rel,
                    )
                )
                continue
            try:
                deps = _dependency_names(rel, text) if name in MANIFESTS else set()
            except (
                OSError,
                UnicodeError,
                ValueError,
                TypeError,
                tomllib.TOMLDecodeError,
            ) as exc:
                diagnostics.append(
                    Diagnostic(
                        "framework.malformed_manifest",
                        f"Could not parse manifest: {exc}",
                        "warning",
                        self.name,
                        rel,
                    )
                )
                deps = set()
            for framework, packages in PACKAGE_RULES.items():
                if deps & packages:
                    found.setdefault(framework, {})[rel] = Evidence(
                        rel, "framework dependency declared in manifest"
                    )
            if path.suffix.lower() in {
                ".py",
                ".js",
                ".jsx",
                ".mjs",
                ".cjs",
                ".ts",
                ".tsx",
            }:
                for framework, pattern in IMPORTS.items():
                    if re.search(pattern, text):
                        found.setdefault(framework, {})[rel] = Evidence(
                            rel, f"static import/declaration for {framework}"
                        )
            for framework, names in CONFIGS.items():
                if name in names:
                    found.setdefault(framework, {})[rel] = Evidence(
                        rel, f"recognized {name} configuration/entry-point indicator"
                    )
        findings = []
        for framework, items in sorted(found.items()):
            direct = any(
                "static import/declaration" in e.indicator
                or "configuration/entry-point" in e.indicator
                for e in items.values()
            )
            state = DetectionState.DETECTED if direct else DetectionState.INFERRED
            detail = (
                None
                if direct
                else "A framework dependency is declared, but no matching import or dedicated configuration was found."
            )
            findings.append(
                Finding(
                    FindingCategory.FRAMEWORK,
                    framework,
                    state,
                    tuple(sorted(items.values(), key=lambda e: e.path)),
                    detail,
                )
            )
        return AnalyzerResult(
            self.name,
            AnalysisStatus.PARTIAL if diagnostics else AnalysisStatus.COMPLETE,
            tuple(findings),
            tuple(diagnostics),
        )
