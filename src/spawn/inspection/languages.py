"""Evidence-based static programming-language detection (Issue #55)."""
from __future__ import annotations

import json
import tomllib
from collections import defaultdict
from pathlib import Path

from spawn.inspection.models import (
    AnalysisStatus, AnalyzerResult, DetectionState, Diagnostic, Evidence,
    Finding, FindingCategory, InspectionTarget, DiscoveryInventory,
)

# Ambiguous extensions (.h, .m, .vue, .svelte) are intentionally excluded.
EXTENSIONS = {
    ".py": "python", ".pyi": "python", ".pyx": "cython",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".java": "java",
    ".kt": "kotlin", ".kts": "kotlin", ".go": "go", ".rs": "rust",
    ".c": "c", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp", ".hxx": "cpp",
    ".cs": "c-sharp", ".rb": "ruby", ".php": "php", ".swift": "swift",
    ".scala": "scala", ".sc": "scala", ".dart": "dart", ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang", ".hrl": "erlang", ".hs": "haskell", ".lhs": "haskell",
    ".lua": "lua", ".pl": "perl", ".pm": "perl", ".r": "r", ".jl": "julia",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".sql": "sql",
}
MANIFESTS = {
    "go.mod": ("go", "Go module manifest"), "Cargo.toml": ("rust", "Rust Cargo manifest"),
    "Gemfile": ("ruby", "Ruby Bundler manifest"), "composer.json": ("php", "PHP Composer manifest"),
    "Package.swift": ("swift", "Swift package manifest"), "pubspec.yaml": ("dart", "Dart pub manifest"),
    "mix.exs": ("elixir", "Elixir Mix manifest"), "pom.xml": ("java", "Maven project manifest"),
    "build.gradle": ("java", "Gradle build manifest"), "build.gradle.kts": ("kotlin", "Kotlin Gradle build manifest"),
}

class LanguageDetector:
    """Detect represented languages from source extensions and explicit manifests.

    This reports repository representation, not buildability or runtime use.
    The analyzer consumes inventory paths and never traverses the repository.
    """
    name = "language"

    def run(self, target: InspectionTarget, inventory: DiscoveryInventory) -> AnalyzerResult:
        found: dict[str, dict[str, Evidence]] = defaultdict(dict)
        diagnostics: list[Diagnostic] = []
        for rel in inventory.files:
            path = Path(rel)
            language = EXTENSIONS.get(path.suffix)
            if language:
                found[language][rel] = Evidence(rel, f"{path.suffix} source-file extension")
            manifest = MANIFESTS.get(path.name)
            if path.name.endswith(".csproj"):
                manifest = ("c-sharp", ".NET project manifest")
            if manifest:
                found[manifest[0]][rel] = Evidence(rel, manifest[1])
            if path.name not in {"pyproject.toml", "package.json"}:
                continue
            try:
                text = (target.path / rel).read_text(encoding="utf-8")
                if len(text) > 1_000_000:
                    diagnostics.append(Diagnostic("language.manifest_too_large", "Manifest exceeds 1 MB limit; skipped.", "warning", self.name, rel))
                    continue
                if path.name == "pyproject.toml":
                    data = tomllib.loads(text)
                    if isinstance(data.get("project"), dict) or isinstance(data.get("tool", {}).get("poetry"), dict):
                        found["python"][rel] = Evidence(rel, "Python project manifest")
                else:
                    data = json.loads(text)
                    if isinstance(data, dict) and any(k in data for k in ("dependencies", "devDependencies", "scripts", "type")):
                        found["javascript"][rel] = Evidence(rel, "Node.js package manifest")
            except (OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
                diagnostics.append(Diagnostic("language.malformed_manifest", f"Could not parse manifest: {exc}", "warning", self.name, rel))
        findings = tuple(
            Finding(FindingCategory.LANGUAGE, lang, DetectionState.DETECTED,
                    tuple(sorted(items.values(), key=lambda e: e.path)),
                    "Source file or recognized language manifest found.")
            for lang, items in sorted(found.items()) if items
        )
        return AnalyzerResult(self.name, AnalysisStatus.PARTIAL if diagnostics else AnalysisStatus.COMPLETE, findings, tuple(diagnostics))
