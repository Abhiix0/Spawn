# Issue #55 Handoff — Language and Framework Detection

> Implemented state (v1.1.0). Both analyzers run inside `run_inspection` (see `docs/architecture.md`) alongside the dependency and tooling analyzers. The support matrix is in `supported-technologies.md`.

## Interface

Both analyzers implement the approved `spawn.inspection.Analyzer` protocol:
`run(InspectionTarget, DiscoveryInventory) -> AnalyzerResult`. They consume the
shared inventory, read only relevant discovered files under `target.path`, and
return contract `Finding`, `Evidence`, and `Diagnostic` instances. They do not
walk directories, execute/import project code, install packages, or access the
network.

## Evidence semantics

- Language extension and recognized language-manifest indicators emit
  `language` findings with `detected` state and at least one relative-path
  evidence item.
- Framework imports and framework-specific configuration/entry-point files
  emit `detected` findings.
- Framework dependency-only signals emit `inferred` findings with explanatory
  `detail`, as required by the contract.
- Unknown technologies and weak directory/README mentions are omitted.
- Findings and evidence are sorted deterministically. Recoverable read/parse
  problems become analyzer diagnostics and make the result `partial`.

## Validation

```sh
uv run pytest tests/test_inspection_languages.py tests/test_inspection_frameworks.py
```

Files are read as bytes, at most 1,000,000 bytes (limit measured in bytes, not
characters); larger files produce `*.file_too_large` / `language.manifest_too_large`
diagnostics. Diagnostic messages contain fixed text plus the exception type
name only, never paths or raw exception text. Each `run()` catches unexpected
errors and returns the findings gathered so far with a fatal
`language.internal_error` / `framework.internal_error` diagnostic and status
`failed`.

## Limitations

- The support matrix documents currently implemented indicators; it is not an
  exhaustive language/framework catalog.
- Static imports may appear in comments/strings; source parsing is deliberately
  not a semantic analyzer.
- Dependency parsing is deliberately conservative and does not resolve
  environment markers, nested requirement includes, dynamic build metadata, or
  arbitrary build scripts.
- A detected config/import does not establish that the application works.
- `.h` is not assigned to C or C++ because the extension is ambiguous.

## Integration notes

The shared inspection models and discovery interface were not modified.
See `supported-technologies.md` for the documented false negatives and false
positives. `pydantic` and `starlette` are emitted as ordinary `framework` findings.
