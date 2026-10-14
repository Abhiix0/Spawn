# Inspection Contract — v1.0

**Issue #53 · Spawn v1.1.0**
**Status: implemented and tested — this document is authoritative**

This is the definitive specification for the Spawn inspection subsystem.
All downstream work — #54 safe discovery, #55 language/framework detection,
#56 dependency inspection, #57 tooling detection, #58 orchestrator and report,
#59 `spawn inspect` CLI and JSON output — implements against the types and
rules stated here.

**Ground truth:** the live Python source in `src/spawn/inspection/` is the
machine-verifiable form of this contract. If this document and the code
disagree, the code wins and this document must be updated. The sample report
in `tests/fixtures/static/sample_report.json` is generated from the models by
`tests/fixtures/make_sample_report.py`; any drift causes a test failure.

---

## Contents

1. [Purpose and scope](#1-purpose-and-scope)
2. [Model set](#2-model-set)
3. [Finding representation](#3-finding-representation)
4. [Detection states](#4-detection-states)
5. [Evidence](#5-evidence)
6. [Diagnostics](#6-diagnostics)
7. [Report status and partial results](#7-report-status-and-partial-results)
8. [Analyzer interface](#8-analyzer-interface)
9. [Serialization and versioning](#9-serialization-and-versioning)
10. [`.spawn/meta.json` handling](#10-spawnmetajson-handling)
11. [Separation from generation](#11-separation-from-generation)
12. [Extension rules](#12-extension-rules)
13. [Interface for downstream owners](#13-interface-for-downstream-owners)
14. [Open questions](#14-open-questions)
15. [Integration note for downstream owners](#15-integration-note-for-downstream-owners)
16. [Appendix A — full sample report JSON](#appendix-a--full-sample-report-json)
17. [Appendix B — validate_report rules](#appendix-b--validate_report-rules)

---

## 1. Purpose and Scope

The inspection subsystem answers one question about an existing repository: what
is in it? It does not create, modify, or publish files. It does not run
repository code, resolve dependencies over the network, or validate that tools
work correctly — it only reads the filesystem statically.

**In scope for v1.1.0:**
- Defining shared data models, enums, and interfaces (this issue, #53).
- Safe, deterministic filesystem discovery (#54).
- Language and framework detection (#55).
- Dependency and package-manager detection (#56).
- Engineering tooling detection (#57).
- Orchestrating analyzers into a single unified report (#58).
- A `spawn inspect` CLI command and JSON output (#59).

**Out of scope for v1.1.0:** vulnerability scanning, dependency resolution,
semantic code analysis, running tests, executing linters, and changes to
`spawn create` or `spawn doctor`.

---

## 2. Model Set

All types live in `src/spawn/inspection/`. Import everything from
`spawn.inspection` (the package `__init__.py` re-exports the full public
surface). FINAL.

| Type | Location | Kind | Purpose |
|---|---|---|---|
| `SCHEMA_VERSION` | `models.py` | `str = "1.0"` | Embedded in every report; governs the bump policy |
| `DetectionState` | `models.py` | `StrEnum` | Five confidence levels for a finding |
| `AnalysisStatus` | `models.py` | `StrEnum` | Four completion states for an analyzer run or the report |
| `FindingCategory` | `models.py` | `StrEnum` | Nine subject categories |
| `Evidence` | `models.py` | `@dataclass(frozen=True)` | One supporting file reference |
| `Diagnostic` | `models.py` | `@dataclass(frozen=True)` | One recoverable analysis problem |
| `Finding` | `models.py` | `@dataclass(frozen=True)` | One claimed observation |
| `AnalyzerResult` | `models.py` | `@dataclass(frozen=True)` | Output bundle from one analyzer run |
| `InspectionTarget` | `models.py` | `@dataclass(frozen=True)` | Validated, resolved inspection root |
| `DiscoveryInventory` | `models.py` | `@dataclass(frozen=True)` | File/dir listing produced by #54 |
| `InspectionReport` | `models.py` | `@dataclass(frozen=True)` | Root result object |
| `validate_report` | `models.py` | function | Contract validation (returns violation strings) |
| `Analyzer` | `base.py` | `@runtime_checkable Protocol` | Interface every analyzer must satisfy |
| `InspectionError` | `exceptions.py` | `SpawnError` subclass | Fatal inspection error, `exit_code = 7` |
| `ReportDecodeError` | `serialization.py` | `InspectionError` subclass | Raised when a JSON report cannot be decoded |
| `to_json` | `serialization.py` | function | `InspectionReport → str` (deterministic JSON) |
| `from_dict` | `serialization.py` | function | `dict → InspectionReport` (version-gated, unknown-field-tolerant) |
| `from_json` | `serialization.py` | function | `str → InspectionReport` (parses JSON, then `from_dict`) |

**Rejected types:**

- `ProjectModel` (separate from `InspectionReport`) — rejected. The report is
  the project model. A wrapper adds a layer with no information gain. FINAL.
- Per-category subclasses (`LanguageFinding`, `DependencyFinding`, …) —
  rejected. A single `Finding` with a category enum covers all kinds without
  requiring consumers to switch on type. FINAL.
- `AnalyzerMetadata` registry — deferred to #58. The contract defines the
  interface; the orchestrator defines registration. FINAL.

---

## 3. Finding Representation

FINAL.

A single `Finding` class covers every subject category, discriminated by
`FindingCategory`. There are no per-kind subclasses.

```python
@dataclass(frozen=True)
class Finding:
    category:        FindingCategory       # what kind of thing is being reported
    subject:         str                   # stable key within the category
    detection_state: DetectionState        # how confident the analyzer is
    evidence:        tuple[Evidence, ...]  # supporting file references
    detail:          str | None = None     # optional human-readable elaboration
```

### Finding identity

Identity is exactly `(category, subject)`. `detection_state` is **not** part
of identity. When two findings share the same identity, the orchestrator (#58):

1. Keeps the higher-confidence state:
   `detected > inferred > unknown > not_detected > not_checked`
2. Merges evidence: union by `path`, preserving first-seen order.

This deduplication rule is the orchestrator's responsibility; the models do
not enforce it.

### `subject` format

Lowercase, hyphen-separated strings. Each analyzer documents the exact
subject strings it emits. The contract does not enumerate them globally.

Examples: `"python"`, `"fastapi"`, `"pytest"`, `"uv"`, `"postgres"`,
`"tests-directory"`, `"github-actions"`, `"spawn-generated"`.

### `FindingCategory` values

FINAL for the nine v1.0 values. New values are additive (no schema bump).
Consumers must handle unknown category values gracefully — skip, do not crash.

| Value | Meaning |
|---|---|
| `"language"` | Programming language |
| `"framework"` | Application-level framework (FastAPI, Django, Express, …) |
| `"package_manager"` | Package manager (uv, poetry, pip, npm, cargo, …) |
| `"dependency"` | One declared package or library (one Finding per package) |
| `"tool"` | Engineering tool: linter, formatter, type-checker, test runner, VCS, pre-commit, … |
| `"ci"` | CI/CD system evidence |
| `"container"` | Container or orchestration config |
| `"database"` | Database or cache indicator |
| `"structure"` | Repository layout observation |

Note: testing frameworks (pytest, jest) belong in `"tool"`, not `"framework"`.
`"framework"` is reserved for application-level frameworks. FINAL — confirmed
with #55.

### Canonical ordering

`InspectionReport.findings` is sorted ascending by `(category.value, subject)`.
`InspectionReport.analyzer_results` is sorted ascending by `analyzer_name`.
`evidence` within a finding is sorted ascending by `path`.
The orchestrator (#58) is responsible for constructing these in sorted order.

---

## 4. Detection States

FINAL.

```python
class DetectionState(StrEnum):
    DETECTED     = "detected"
    INFERRED     = "inferred"
    UNKNOWN      = "unknown"
    NOT_DETECTED = "not_detected"
    NOT_CHECKED  = "not_checked"
```

### Definitions and examples

| State | Meaning | Example |
|---|---|---|
| `detected` | Direct, unambiguous file evidence confirms presence | `[tool.pytest.ini_options]` in `pyproject.toml` → pytest detected |
| `inferred` | Probable conclusion from indirect evidence; cannot confirm without executing code or network | `fastapi` in `requirements.txt` with no pyproject framework section → FastAPI inferred |
| `unknown` | Analyzer ran, found relevant files, could not determine presence or absence | `install_requires` is a dynamic expression the parser cannot evaluate |
| `not_detected` | Active negative: analyzer checked and found no evidence | No `pytest.ini`, no `[tool.pytest]`, no pytest dependency anywhere |
| `not_checked` | Analyzer did not attempt this subject | Dependency analyzer skipped — `pyproject.toml` was unreadable |

### Evidence and `detail` rules

Enforced by `validate_report()`.

| State | Evidence | `detail` |
|---|---|---|
| `detected` | **Required** (≥1) | Optional |
| `inferred` | **Required** (≥1) | **Required** — must explain the inference chain |
| `unknown` | Optional | Optional |
| `not_detected` | Optional (may cite checked locations) | Recommended — name what was checked |
| `not_checked` | **Must be empty** | Optional |

### Confidence precedence (for deduplication)

```
detected (5) > inferred (4) > unknown (3) > not_detected (2) > not_checked (1)
```

This ordering is encoded in `_DETECTION_STATE_PRECEDENCE` in `models.py`.

---

## 5. Evidence

FINAL.

```python
@dataclass(frozen=True)
class Evidence:
    path:      str              # repository-relative, forward-slash
    indicator: str              # short human-readable description
    detail:    str | None = None  # optional context
```

### `path` rules — all mandatory

- Relative to the inspection root (`InspectionTarget.path`).
- Always forward slashes (`/`), regardless of OS.
- Never starts with `/` or a drive letter (`C:`).
- Never contains `..` segments.
- Correct: `"pyproject.toml"`, `".github/workflows/ci.yml"`, `"src/app.py"`
- Wrong: `"/absolute/path"`, `"C:\\Windows"`, `"../outside"`

### `indicator`

Short, human-readable description of what was found. Not machine-parsed; used
for display and traceability.

Examples: `"[tool.pytest.ini_options] section"`, `"import fastapi"`,
`"Dockerfile FROM python:3.12"`, `"fastapi in [project.dependencies]"`.

### `detail`

Optional context — a line number, matched version string, specific key.
Plain string only. No structured sub-fields in v1.0. Revisit in v1.2 if
renderers need structured detail.

---

## 6. Diagnostics

FINAL.

```python
@dataclass(frozen=True)
class Diagnostic:
    code:     str              # "source_slug.snake_case_reason"
    message:  str              # human-readable description
    severity: str              # "error" | "warning" | "info"
    source:   str              # analyzer slug, "discovery", or "orchestrator"
    path:     str | None = None  # repository-relative posix path, if applicable
    fatal:    bool = False     # True → source cannot continue
```

### Code scheme

`<source_slug>.<snake_case_reason>`. All lowercase, no spaces. Each analyzer
defines and documents its own codes; there is no global registry.

| Example code | Emitted by | Meaning |
|---|---|---|
| `"discovery.unreadable_file"` | `"discovery"` | A file could not be read |
| `"discovery.permission_denied"` | `"discovery"` | A directory was inaccessible |
| `"dependency.malformed_manifest"` | `"dependency"` | A manifest could not be parsed |
| `"tooling.unrecognised_ci_syntax"` | `"tooling"` | CI config has unexpected structure |
| `"orchestrator.meta_unreadable"` | `"orchestrator"` | `.spawn/meta.json` could not be read |

### `severity` values

Exactly three: `"error"`, `"warning"`, `"info"`. Validated by `validate_report()`.

### `fatal` semantics

- `fatal=True` → the emitting source cannot continue. The orchestrator sets
  that analyzer's `AnalysisStatus` to `FAILED`. A `fatal=True` diagnostic
  from discovery sets the entire report `status` to `FAILED`.
- `fatal=False` → the source recovered and continued. Its status is `PARTIAL`.

### Diagnostic vs `not_checked` finding

A `Diagnostic` is about the *analysis process* (something went wrong with the
tooling). A `not_checked` finding is about a *subject* (something in the
repository was not examined). They coexist:

```
Diagnostic(code="dependency.unreadable_manifest", path="requirements.txt")
```
explains *why* findings about packages in that file are `not_checked`. Both
are present; neither replaces the other.

---

## 7. Report Status and Partial Results

FINAL.

```python
class AnalysisStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL  = "partial"
    FAILED   = "failed"
    SKIPPED  = "skipped"
```

### Per-analyzer status rules (set by the orchestrator, #58)

| Condition | `AnalyzerResult.status` |
|---|---|
| Ran, zero diagnostics | `complete` |
| Ran, ≥1 non-fatal diagnostic | `partial` |
| ≥1 fatal diagnostic **or** unhandled exception | `failed` |
| Never attempted | `skipped` |

### Overall report status rules (set by the orchestrator, #58)

| Condition | `InspectionReport.status` |
|---|---|
| All analyzers `complete` or `skipped` | `complete` |
| ≥1 analyzer `partial` or `failed`, discovery succeeded | `partial` |
| Discovery failed fatally | `failed` |

### Partial-result guarantee

Valid findings produced **before** a fatal error must be preserved in the
report. The orchestrator must not discard findings from a failed analyzer run.
This is a hard contract requirement.

### Worked example — malformed optional file

1. Dependency analyzer parses `pyproject.toml` successfully.
2. Opens `requirements.txt` — finds it truncated. Emits:
   `Diagnostic(code="dependency.malformed_manifest", fatal=False, path="requirements.txt")`
3. Continues; adds findings from `pyproject.toml`.
4. `AnalyzerResult.status = PARTIAL`.
5. Overall `InspectionReport.status = PARTIAL`.
6. Findings from `pyproject.toml` are in the report.
   `requirements.txt` entries are absent; the diagnostic says why.

See `tests/fixtures/static/sample_report.json` for a complete worked example.

---

## 8. Analyzer Interface

FINAL (Protocol vs ABC: APPROVED by #55, #56, #57).

Defined in `src/spawn/inspection/base.py`.

```python
from typing import Protocol, runtime_checkable
from spawn.inspection.models import AnalyzerResult, DiscoveryInventory, InspectionTarget

@runtime_checkable
class Analyzer(Protocol):
    name: str   # stable slug: lowercase, hyphen-separated
                # e.g. "language", "dependency", "tooling"

    def run(
        self,
        target: InspectionTarget,
        inventory: DiscoveryInventory,
    ) -> AnalyzerResult: ...
```

A plain class with `name: str` and a matching `run()` method satisfies this
interface without inheriting from anything. `isinstance(obj, Analyzer)` works
at runtime because the Protocol is `@runtime_checkable`.

### What `InspectionTarget` carries

```python
@dataclass(frozen=True)
class InspectionTarget:
    path: Path   # resolved, absolute, confirmed readable directory
```

Constructed by the orchestrator (#58) after validating the supplied path.
Analyzers receive it and use `target.path` to open files.

### What `DiscoveryInventory` carries

Produced by #54. Defined here so #55–#58 can compile before #54 is merged.

```python
@dataclass(frozen=True)
class DiscoveryInventory:
    files:       tuple[str, ...]        # sorted, relative, posix paths
    directories: tuple[str, ...]        # sorted, relative, posix paths
    skipped:     tuple[str, ...]        # paths not traversed
    diagnostics: tuple[Diagnostic, ...] # recoverable discovery errors
```

All path strings: repository-relative, forward-slash, sorted lexicographically,
never absolute. #54 must produce an object that satisfies this exact shape.

### Contracts on `run()`

1. **MUST NOT raise.** Catch all exceptions internally; emit
   `Diagnostic(fatal=True)` and return `AnalyzerResult(status=FAILED, ...)`.
2. **MUST NOT modify** any file under `target.path`.
3. **MUST NOT execute** repository code or spawn subprocesses.
4. **MUST NOT** make network requests.
5. **MAY** return zero findings (valid when a subject is absent).
6. `analyzer_name` on the returned `AnalyzerResult` **must equal** `self.name`.

### Why Protocol, not ABC

Structural subtyping means analyzers need not inherit from anything in
`inspection/`. Tests can use anonymous stub objects. IDE support is
equivalent for `@runtime_checkable` Protocols.

---

## 9. Serialization and Versioning

FINAL.

### Entry points

```python
from spawn.inspection import to_json, from_dict, from_json, ReportDecodeError

to_json(report: InspectionReport, *, indent: int = 2) -> str
from_json(text: str) -> InspectionReport    # raises ReportDecodeError
from_dict(d: dict) -> InspectionReport      # raises ReportDecodeError
```

`to_json()` returns a UTF-8 string ending with `\n`. Byte-identical output
for equal reports (same `generated_at`). `ensure_ascii=False` — non-ASCII
characters in strings are preserved as-is.

### JSON field type mapping

| Python type | JSON representation |
|---|---|
| `StrEnum` | `str` — the `.value` |
| `Path` | `str` — via `.as_posix()` |
| `None` | `null` |
| `tuple[T, ...]` | JSON array |
| `bool` | `true` / `false` |
| Nested model | Nested object via `.to_dict()` |

### Top-level field order (stable)

```
schema_version → status → generated_at → target →
recorded_metadata → findings → analyzer_results → diagnostics
```

### List ordering (canonical, required for determinism)

| List | Order |
|---|---|
| `findings` | Ascending by `(category.value, subject)` |
| `analyzer_results` | Ascending by `analyzer_name` |
| `evidence` within a finding | Ascending by `path` |
| `diagnostics` within an `AnalyzerResult` | Emission order (no sort) |

The orchestrator (#58) is responsible for constructing these in sorted order.
`to_json()` and `to_dict()` serialise exactly as constructed; they do not sort.

### Required fields for `from_json` / `from_dict`

`schema_version`, `status`, `target` (with `path` inside). All other fields
are optional; absent fields default to their model defaults (empty tuples,
`None`, empty string).

### Version gating

| Incoming `schema_version` | Behaviour |
|---|---|
| Same major, any minor (e.g. `"1.5"`) | Accepted; unknown fields silently ignored |
| Different major (e.g. `"2.0"`) | `ReportDecodeError` — clear message naming both versions |
| Missing or non-string | `ReportDecodeError` |
| Malformed (not `"major.minor"`) | `ReportDecodeError` |

### Unknown fields on load

Silently ignored at every level of the JSON object. This enables
forward-compatible reading of reports produced by a newer minor version.
Consistent with `read_project_metadata()` behaviour in `core/project.py`.

### `schema_version` bump policy

| Change | Required action |
|---|---|
| Add a new optional field to any model | No bump |
| Add a new required field | Minor bump (`"1.0"` → `"1.1"`) |
| Rename or remove any field | Major bump (`"1.0"` → `"2.0"`) |
| Add a `FindingCategory` value | No bump |
| Change a `FindingCategory` string | Major bump |
| Change a `subject` string | Breaking — emit old alongside new for one minor version |

### `generated_at`

ISO 8601 UTC string (e.g. `"2026-10-14T10:00:00+00:00"`). Present in the
report for human reference. **Exclude from regression comparisons** — it
changes on every run. Tests must pop this key before comparing two serialised
reports (same pattern as `created_at` in `tests/test_fixtures.py`).

### `ReportDecodeError`

Subclass of `InspectionError` (and therefore `SpawnError`), `exit_code = 7`.
Raised for: invalid JSON, missing required fields, wrong types, unknown enum
values, and incompatible major version. The CLI (#59) catches it uniformly
alongside `InspectionError`.

### `target.path` in serialised output

`target.path` is serialised as a posix string via `.as_posix()`. It is the
resolved, absolute inspection root (e.g. `"/projects/acme-api"`). Evidence
paths and diagnostic paths are always repository-relative — they must never
be absolute. No evidence or diagnostic path in `to_dict()` output may start
with `/` or a drive letter.

---

## 10. `.spawn/meta.json` Handling

FINAL.

### How it is included

`InspectionReport` has one optional field:

```python
recorded_metadata: ProjectMetadata | None = None
```

`ProjectMetadata` is the existing frozen dataclass from `core/project.py`.
`read_project_metadata(target.path)` is the only sanctioned way to read
`.spawn/meta.json`. It returns `None` if the file is absent, raises
`ConfigError` if the file is unreadable or malformed.

The orchestrator (#58) calls `read_project_metadata`, catches `ConfigError`,
emits `Diagnostic(code="orchestrator.meta_unreadable", fatal=False)`, and
leaves `recorded_metadata = None`.

### Semantics — treat as untrusted and possibly stale

- The repository may have changed since Spawn wrote `.spawn/meta.json`. This
  is stated in the `ProjectMetadata` docstring and is a hard contract rule.
- Analyzers **must not** use `recorded_metadata` as the basis of a `detected`
  finding. It may support an `inferred` finding (e.g., an `Evidence` with
  `path=".spawn/meta.json"`).
- The JSON field is named `"recorded_metadata"` — not `"spawn_meta"` — to
  make its provenance unambiguous.
- `null` when the project was not generated by Spawn.

### `ProjectMetadata` fields

Inherited from `core/project.py`. All fields default to `None` when absent.

| JSON key | Python field | Type |
|---|---|---|
| `"intent"` | `intent` | `str \| None` |
| `"framework"` | `framework` | `str \| None` |
| `"provider"` | `provider` | `str \| None` |
| `"spawn_version"` | `spawn_version` | `str \| None` |
| `"created_at"` | `created_at` | `str \| None` (ISO 8601) |
| `"generator"` | `generator` | `str \| None` (`"blueprint"` or `"custom"`) |
| `"git"` | `git` | `bool \| None` |
| `"uv"` | `uv` | `bool \| None` |
| `"source"` | `source` | `str \| None` |

### Expressing "this is a Spawn-generated project" as a finding

```python
Finding(
    category=FindingCategory.STRUCTURE,
    subject="spawn-generated",
    detection_state=DetectionState.DETECTED,
    evidence=(Evidence(
        path=".spawn/meta.json",
        indicator=".spawn/meta.json present",
    ),),
)
```

`recorded_metadata` carries the raw historical record. Both are present in the
report; neither replaces the other.

---

## 11. Separation from Generation

FINAL.

`inspection/` is a new top-level sibling package under `src/spawn/`. It does
not affect `spawn create` or `spawn doctor`.

### Import rules

| `inspection/` may import | `inspection/` must not import |
|---|---|
| `core.exceptions` | `core.models` (generation-side — `ProjectConfig`) |
| `core.project` | `core.planning`, `core.registry` |
| stdlib | `generators.*`, `templates.*` |
| | `utils.*` (utils are for terminal rendering; inspection models are pure data) |
| | `spawn.cli` |

### No effect on existing functionality

- `ProjectConfig` and `HealthCheck` are not modified, subclassed, or imported.
- `spawn create` and `spawn doctor` import nothing from `inspection/`.
- The baseline 1213 generation/doctor tests continue to pass unchanged.

### Boundary enforcement

`"inspection"` is in the `GUARDED` tuple in `tests/test_boundaries.py`.
The boundary test statically verifies that nothing in `inspection/` imports
`spawn.cli`. This runs on every `uv run pytest` invocation.

---

## 12. Extension Rules

FINAL.

### Adding a new analyzer

1. Create a class satisfying the `Analyzer` Protocol (§8).
2. Register it in the orchestrator (#58). No change to `models.py`.
3. Document the `subject` strings it emits and the `Diagnostic` codes it
   produces in that analyzer's own documentation.
4. No schema version bump needed.

### Adding a new `FindingCategory` value

1. Add to `FindingCategory` in `models.py`.
2. No schema version bump (additive — consumers must handle unknown categories
   gracefully).
3. Update this document.

### Adding a new optional field to any model

1. Add with a default so existing construction sites still compile.
2. Bump schema minor version (`"1.0"` → `"1.1"`).
3. Document the field here and in the model docstring.

### Removing or renaming a field

1. Bump schema major version (`"1.0"` → `"2.0"`).
2. Coordinate with all downstream owners.
3. Deprecate in a minor release before removing.

### Changing a `subject` string

Breaking change even within the same `schema_version`. Emit the old subject
alongside the new one for one full minor version before removing the old one.

---

## 13. Interface for Downstream Owners

This section lists the exact Python imports, constructors, fields, enums, and
serialization entry points for each downstream issue. Read only the subsection
relevant to your issue. Import everything from `spawn.inspection`.

### For #54 — Safe Discovery

You produce a `DiscoveryInventory`. Your module must construct one and return
it from your discovery entry point.

```python
from spawn.inspection import DiscoveryInventory, Diagnostic

# Construct (all paths must be sorted, relative, posix)
inventory = DiscoveryInventory(
    files=("pyproject.toml", "src/main.py"),         # tuple, sorted
    directories=("src", "tests"),                     # tuple, sorted
    skipped=(".git",),                                # paths not traversed
    diagnostics=(),                                   # Diagnostic instances
)

# Field reference
inventory.files        # tuple[str, ...]
inventory.directories  # tuple[str, ...]
inventory.skipped      # tuple[str, ...]
inventory.diagnostics  # tuple[Diagnostic, ...]
```

Path rules: relative, forward-slash, lexicographically sorted. Never absolute.
Your `skipped` entries are path strings; the reason lives in a companion
`Diagnostic` in `inventory.diagnostics` (not encoded in the path string).

Diagnostic code convention for discovery: `"discovery.<reason>"`, e.g.
`"discovery.permission_denied"`, `"discovery.unreadable_file"`.

### For #55 — Language and Framework Detection

You implement an `Analyzer`. You receive `InspectionTarget` and
`DiscoveryInventory`, and return `AnalyzerResult`.

```python
from spawn.inspection import (
    Analyzer,          # Protocol your class satisfies
    AnalyzerResult,
    AnalysisStatus,
    Diagnostic,
    DetectionState,
    Evidence,
    Finding,
    FindingCategory,
    InspectionTarget,
    DiscoveryInventory,
)

class LanguageAnalyzer:
    name = "language"   # must match AnalyzerResult.analyzer_name

    def run(self, target: InspectionTarget, inventory: DiscoveryInventory) -> AnalyzerResult:
        findings = []

        # DETECTED: direct file evidence
        if "pyproject.toml" in inventory.files:
            findings.append(Finding(
                category=FindingCategory.LANGUAGE,
                subject="python",
                detection_state=DetectionState.DETECTED,
                evidence=(Evidence(
                    path="pyproject.toml",
                    indicator="requires-python field",
                    detail=">=3.12",
                ),),
            ))

        # INFERRED: indirect evidence — detail is required
        if "requirements.txt" in inventory.files and not _has_pyproject_framework(inventory):
            findings.append(Finding(
                category=FindingCategory.FRAMEWORK,
                subject="fastapi",
                detection_state=DetectionState.INFERRED,
                evidence=(Evidence(path="requirements.txt", indicator="fastapi in deps"),),
                detail="fastapi found in requirements.txt; no pyproject framework section",
            ))

        return AnalyzerResult(
            analyzer_name=self.name,
            status=AnalysisStatus.COMPLETE,
            findings=tuple(findings),
            diagnostics=(),
        )
```

**Category note:** testing frameworks (pytest, jest) belong in
`FindingCategory.TOOL`, not `FindingCategory.FRAMEWORK`. `FRAMEWORK` is
application-level only.

**Subject strings** — document the exact strings you emit in your own module.
Use lowercase, hyphen-separated names.

### For #56 — Dependency Inspection

You implement an `Analyzer`. The key distinction for this issue:

- One `Finding` per declared package — `subject` = normalised package name.
- `FindingCategory.PACKAGE_MANAGER` for the package manager itself.
- `FindingCategory.DEPENDENCY` for each individual declared package.

```python
from spawn.inspection import (
    Finding, FindingCategory, DetectionState, Evidence,
    Diagnostic, AnalyzerResult, AnalysisStatus,
)

# Package manager finding
pm_finding = Finding(
    category=FindingCategory.PACKAGE_MANAGER,
    subject="uv",                              # lowercase package-manager name
    detection_state=DetectionState.DETECTED,
    evidence=(Evidence(path="uv.lock", indicator="uv.lock present"),),
)

# Individual dependency finding
dep_finding = Finding(
    category=FindingCategory.DEPENDENCY,
    subject="fastapi",                         # normalised package name
    detection_state=DetectionState.DETECTED,
    evidence=(Evidence(
        path="pyproject.toml",
        indicator="fastapi in [project.dependencies]",
        detail="fastapi>=0.115.0",
    ),),
)

# Recoverable error on a malformed file (non-fatal → analyzer continues)
diag = Diagnostic(
    code="dependency.malformed_manifest",
    message="requirements.txt is truncated",
    severity="warning",
    source="dependency",
    path="requirements.txt",
    fatal=False,                # non-fatal → AnalysisStatus.PARTIAL, not FAILED
)
```

When a manifest is unreadable, emit a non-fatal `Diagnostic` and continue
with whatever other manifests you could parse. Set `status=PARTIAL`.

### For #57 — Tooling Detection

You implement an `Analyzer`. Engineering tools (linters, formatters,
type-checkers, test runners, VCS, pre-commit) all use `FindingCategory.TOOL`.
CI systems use `FindingCategory.CI`. Container configs use
`FindingCategory.CONTAINER`.

```python
# Git (VCS) — belongs in TOOL
Finding(
    category=FindingCategory.TOOL,
    subject="git",
    detection_state=DetectionState.DETECTED,
    evidence=(Evidence(path=".git", indicator=".git directory present"),),
)

# GitHub Actions — belongs in CI
Finding(
    category=FindingCategory.CI,
    subject="github-actions",
    detection_state=DetectionState.DETECTED,
    evidence=(Evidence(path=".github/workflows/ci.yml", indicator="workflow file"),),
)

# A tool that was checked but not found — detail should name locations
Finding(
    category=FindingCategory.TOOL,
    subject="ruff",
    detection_state=DetectionState.NOT_DETECTED,
    evidence=(),
    detail="checked pyproject.toml [tool.ruff], ruff.toml, .ruff.toml — none present",
)
```

Configuration presence does not imply the tool executes correctly. Do not
claim `detected` for a tool unless you found its configuration file evidence.

### For #58 — Orchestrator and Report

You construct the `InspectionReport`. Key responsibilities:

```python
from spawn.inspection import (
    InspectionReport, InspectionTarget, AnalysisStatus,
    validate_report,
)
from spawn.core.project import read_project_metadata
from spawn.core.exceptions import ConfigError
from pathlib import Path

def run_inspection(path: Path) -> InspectionReport:
    target = InspectionTarget(path=path.resolve())

    # Load recorded metadata; treat errors as non-fatal
    try:
        recorded_metadata = read_project_metadata(target.path)
    except ConfigError as e:
        recorded_metadata = None
        # emit Diagnostic(code="orchestrator.meta_unreadable", ...)

    # Run discovery, then each registered analyzer in a try/except
    # ...

    # Deduplicate findings using (category, subject) identity
    # Keep higher-confidence state; merge evidence union
    # Sort findings by (category.value, subject)
    # Sort analyzer_results by analyzer_name
    # Sort evidence within each finding by path

    # Determine overall status:
    # all complete/skipped → complete
    # any partial/failed, discovery ok → partial
    # discovery fatal → failed

    report = InspectionReport(
        target=target,
        status=overall_status,
        recorded_metadata=recorded_metadata,
        findings=tuple(sorted_findings),
        analyzer_results=tuple(sorted_results),
        diagnostics=tuple(report_level_diagnostics),
    )
    return report
```

**Partial-result guarantee:** preserve valid findings from failed analyzers.
Do not discard findings because one analyzer errored.

**Report serialization** (for #59):

```python
from spawn.inspection import to_json
json_str = to_json(report)          # deterministic, ends with \n
```

### For #59 — CLI and JSON Output

You receive an `InspectionReport` from the orchestrator and render it.

```python
from spawn.inspection import (
    InspectionReport, AnalysisStatus,
    to_json, from_json, ReportDecodeError,
    SCHEMA_VERSION,
)

# Serialise to JSON (for --json flag)
print(to_json(report), end="")      # to_json already ends with \n

# Deserialise from stored JSON (if loading a cached report)
try:
    report = from_json(text)
except ReportDecodeError as e:
    # e.exit_code == 7; handle uniformly with other SpawnError subclasses
    ...

# Regression comparison: pop generated_at before comparing
d = report.to_dict()
d.pop("generated_at")
```

**Exit code guidance (for your own decision):**

The contract does not mandate CLI exit codes — that is #59's decision. The
suggested baseline: `0` = complete, `1` = partial (some findings missing),
`2` = failed (no usable output). This is open; see §14.

---

## 14. Open Questions

The following items were raised during review and remain open for the stated
owners to decide before their implementations are merged.

| # | Question | Owner | Notes |
|---|---|---|---|
| 1 | Does `DiscoveryInventory.skipped` need a `(path, reason)` tuple rather than a plain path string? | #54 | Current shape uses plain strings; reasons go in diagnostics. Reply needed before #54 is merged. |
| 2 | What are the exact `subject` strings for languages and frameworks #55 will detect? | #55 | A table in #55's own documentation is sufficient before implementation begins. |
| 3 | Is `DEPENDENCY` one finding per declared dependency (potentially hundreds), or per manifest? | #56 | Contract says one per package. If too verbose, #56 should flag this before merging. |
| 4 | Does `PACKAGE_MANAGER` cover Python only, or also npm/cargo/etc. in v1.1.0? | #56 | Contract does not restrict it; #56 decides scope. |
| 5 | Suggested CLI exit codes (§13 for #59): `0`=complete, `1`=partial, `2`=failed. Is partial a non-zero exit? | #59 | The contract does not mandate exit codes. #59 decides and documents them. |

---

## 15. Integration Note for Downstream Owners

All downstream modules import from `spawn.inspection`. Do not import directly
from `spawn.inspection.models`, `spawn.inspection.base`, or
`spawn.inspection.serialization` — those are implementation files; the public
surface is the package.

```python
from spawn.inspection import (
    SCHEMA_VERSION,
    Analyzer, AnalyzerResult, AnalysisStatus,
    Diagnostic, DiscoveryInventory, DetectionState,
    Evidence, Finding, FindingCategory,
    InspectionError, InspectionReport, InspectionTarget,
    ReportDecodeError, from_dict, from_json, to_json,
    validate_report,
)
```

**Do not import** `ProjectConfig`, `TemplateMetadata`, `generate_project`,
`plan_project`, or anything else from `core/models`, `core/planning`,
`core/registry`, `generators/`, or `templates/`. The inspection subsystem is
independent of the generation pipeline.

**Do import** `read_project_metadata` from `core.project` if your analyzer
needs to consult `.spawn/meta.json`. Treat the result as untrusted and
possibly stale (see §10).

**Testing pattern:**

```python
# Minimal stub that satisfies Analyzer without inheriting
class MyStubAnalyzer:
    name = "my-analyzer"

    def run(self, target, inventory):
        return AnalyzerResult(
            analyzer_name=self.name,
            status=AnalysisStatus.COMPLETE,
            findings=(),
            diagnostics=(),
        )

assert isinstance(MyStubAnalyzer(), Analyzer)  # True — runtime-checkable Protocol
```

**Regenerating the sample report** after any intentional model change:

```bash
uv run python tests/fixtures/make_sample_report.py
```

The drift-prevention test (`TestDriftPrevention::test_factory_matches_file_bytes`)
will fail until you regenerate.

---

## Appendix A — Full Sample Report JSON

The live canonical version is `tests/fixtures/static/sample_report.json`,
generated by `tests/fixtures/make_sample_report.py`. The excerpt below covers
all five detection states, a partial analyzer, and a recoverable diagnostic.

```json
{
  "schema_version": "1.0",
  "status": "partial",
  "generated_at": "2026-10-14T10:00:00+00:00",
  "target": {
    "path": "/projects/acme-api"
  },
  "recorded_metadata": {
    "intent": "backend-api",
    "framework": "fastapi",
    "provider": null,
    "spawn_version": "1.0.9",
    "created_at": "2026-01-01T00:00:00+00:00",
    "generator": "blueprint",
    "git": true,
    "uv": true,
    "source": null
  },
  "findings": [
    {
      "category": "ci",
      "subject": "github-actions",
      "detection_state": "not_detected",
      "evidence": [],
      "detail": "checked .github/workflows/*.yml, .github/workflows/*.yaml, .circleci/config.yml, .gitlab-ci.yml — none present"
    },
    {
      "category": "container",
      "subject": "docker",
      "detection_state": "not_checked",
      "evidence": [],
      "detail": null
    },
    {
      "category": "dependency",
      "subject": "sqlalchemy",
      "detection_state": "unknown",
      "evidence": [
        { "path": "setup.cfg", "indicator": "dynamic install_requires expression", "detail": null }
      ],
      "detail": "setup.cfg contains a dynamic install_requires that references an external version file; static analysis cannot resolve the value"
    },
    {
      "category": "framework",
      "subject": "fastapi",
      "detection_state": "detected",
      "evidence": [
        { "path": "pyproject.toml", "indicator": "fastapi in [project.dependencies]", "detail": "fastapi>=0.115.0" }
      ],
      "detail": null
    },
    {
      "category": "language",
      "subject": "python",
      "detection_state": "detected",
      "evidence": [
        { "path": "pyproject.toml", "indicator": "requires-python field", "detail": ">=3.12" }
      ],
      "detail": null
    },
    {
      "category": "package_manager",
      "subject": "uv",
      "detection_state": "inferred",
      "evidence": [
        { "path": "uv.lock", "indicator": "uv.lock lockfile present", "detail": null }
      ],
      "detail": "uv.lock is present but no [tool.uv] section found in pyproject.toml; uv inferred as package manager from lockfile evidence alone"
    },
    {
      "category": "structure",
      "subject": "spawn-generated",
      "detection_state": "detected",
      "evidence": [
        { "path": ".spawn/meta.json", "indicator": ".spawn/meta.json present", "detail": null }
      ],
      "detail": null
    },
    {
      "category": "tool",
      "subject": "pytest",
      "detection_state": "detected",
      "evidence": [
        { "path": "pyproject.toml", "indicator": "[tool.pytest.ini_options] section", "detail": null }
      ],
      "detail": null
    }
  ],
  "analyzer_results": [
    {
      "analyzer_name": "dependency",
      "status": "partial",
      "findings": [],
      "diagnostics": [
        {
          "code": "dependency.malformed_manifest",
          "message": "requirements.txt is truncated and could not be fully parsed; partial dependency list from this file may be missing",
          "severity": "warning",
          "source": "dependency",
          "path": "requirements.txt",
          "fatal": false
        }
      ]
    },
    { "analyzer_name": "language",  "status": "complete", "findings": [], "diagnostics": [] },
    { "analyzer_name": "tooling",   "status": "complete", "findings": [], "diagnostics": [] }
  ],
  "diagnostics": []
}
```

---

## Appendix B — `validate_report` Rules

`validate_report(report: InspectionReport) -> list[str]` in `models.py`
returns a list of violation strings (empty = valid). Not called during normal
inspection; used by contract tests and CI validation.

Rules enforced:

1. `detected` or `inferred` finding → `len(evidence) >= 1`
2. `not_checked` finding → `len(evidence) == 0`
3. `inferred` finding → `detail` is non-empty
4. All `Evidence.path` values: relative, forward-slash, no `..`, not absolute
5. All `Diagnostic.severity` values: one of `"error"`, `"warning"`, `"info"`
