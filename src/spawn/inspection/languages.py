"""Evidence-based static programming-language detection (Issue #55)."""

from __future__ import annotations

import json
import tomllib
from collections import defaultdict
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

MAX_FILE_SIZE = 1_000_000

# Ambiguous extensions (.h, .m, .vue, .svelte) are intentionally excluded.
EXTENSIONS = {
    ".py": "python",
    ".pyi": "python",
    ".pyx": "cython",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".hxx": "cpp",
    ".cs": "c-sharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".sc": "scala",
    ".dart": "dart",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hrl": "erlang",
    ".hs": "haskell",
    ".lhs": "haskell",
    ".lua": "lua",
    ".pl": "perl",
    ".pm": "perl",
    ".r": "r",
    ".jl": "julia",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
}
MANIFESTS = {
    "go.mod": ("go", "Go module manifest"),
    "Cargo.toml": ("rust", "Rust Cargo manifest"),
    "Gemfile": ("ruby", "Ruby Bundler manifest"),
    "composer.json": ("php", "PHP Composer manifest"),
    "Package.swift": ("swift", "Swift package manifest"),
    "pubspec.yaml": ("dart", "Dart pub manifest"),
    "mix.exs": ("elixir", "Elixir Mix manifest"),
    "pom.xml": ("java", "Maven project manifest"),
    "build.gradle": ("java", "Gradle build manifest"),
    "build.gradle.kts": ("kotlin", "Kotlin Gradle build manifest"),
}


def read_text_bounded(path: Path) -> str | None:
    """Read at most MAX_FILE_SIZE bytes as UTF-8; None when the file is larger."""
    with path.open("rb") as fh:
        data = fh.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        return None
    return data.decode("utf-8-sig")


def table(data: object, key: str) -> dict:
    """Return data[key] when both are mappings, else an empty dict."""
    value = data.get(key) if isinstance(data, dict) else None
    return value if isinstance(value, dict) else {}


class LanguageDetector:
    """Detect represented languages from source extensions and explicit manifests.

    This reports repository representation, not buildability or runtime use.
    The analyzer consumes inventory paths and never traverses the repository.
    """

    name = "language"

    def run(
        self, target: InspectionTarget, inventory: DiscoveryInventory
    ) -> AnalyzerResult:
        found: dict[str, dict[str, Evidence]] = defaultdict(dict)
        diagnostics: list[Diagnostic] = []
        try:
            for rel in inventory.files:
                self._scan(target, rel, found, diagnostics)
        except Exception as exc:  # noqa: BLE001 - run() must never raise
            diagnostics.append(
                Diagnostic(
                    "language.internal_error",
                    f"Internal error ({type(exc).__name__}).",
                    "error",
                    self.name,
                    fatal=True,
                )
            )
        findings = tuple(
            Finding(
                FindingCategory.LANGUAGE,
                lang,
                DetectionState.DETECTED,
                tuple(sorted(items.values(), key=lambda e: e.path)),
                "Source file or recognized language manifest found.",
            )
            for lang, items in sorted(found.items())
            if items
        )
        if any(d.fatal for d in diagnostics):
            status = AnalysisStatus.FAILED
        else:
            status = AnalysisStatus.PARTIAL if diagnostics else AnalysisStatus.COMPLETE
        return AnalyzerResult(self.name, status, findings, tuple(diagnostics))

    def _scan(self, target, rel, found, diagnostics) -> None:
        path = Path(rel)
        language = EXTENSIONS.get(path.suffix.lower())
        if language:
            found[language][rel] = Evidence(
                rel, f"{path.suffix.lower()} source-file extension"
            )
        manifest = MANIFESTS.get(path.name)
        if path.name.endswith(".csproj"):
            manifest = ("c-sharp", ".NET project manifest")
        if manifest:
            found[manifest[0]][rel] = Evidence(rel, manifest[1])
        if path.name not in {"pyproject.toml", "package.json"}:
            return
        try:
            text = read_text_bounded(target.path / rel)
            if text is None:
                diagnostics.append(
                    Diagnostic(
                        "language.manifest_too_large",
                        "Manifest exceeds 1 MB limit; skipped.",
                        "warning",
                        self.name,
                        rel,
                    )
                )
                return
            if path.name == "pyproject.toml":
                data = tomllib.loads(text)
                if isinstance(data.get("project"), dict) or isinstance(
                    table(data, "tool").get("poetry"), dict
                ):
                    found["python"][rel] = Evidence(rel, "Python project manifest")
            else:
                data = json.loads(text)
                if isinstance(data, dict) and any(
                    k in data
                    for k in ("dependencies", "devDependencies", "scripts", "type")
                ):
                    found["javascript"][rel] = Evidence(rel, "Node.js package manifest")
        except (
            OSError,
            ValueError,
        ) as exc:  # ValueError covers UnicodeError, JSON, TOML
            diagnostics.append(
                Diagnostic(
                    "language.malformed_manifest",
                    f"Could not parse manifest ({type(exc).__name__}).",
                    "warning",
                    self.name,
                    rel,
                )
            )
