# Issue #55 Handoff — Language and Framework Detection

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

Command run:

```sh
PYTHONPATH=/mnt/data/spawn_review/spawn/src python -m pytest -c /dev/null -q /tmp/spawn-detector-tests
```

Result: `11 passed`. The two detector test modules were copied to a temporary
test directory so the repository-wide `tests/conftest.py` would not load.

`compileall` passed for the new modules and tests. Ruff could not run because
Ruff is not installed in the environment. The normal in-repository pytest
command remains blocked by pre-existing `pyproject.toml` merge-conflict markers
(line 23 onwards); bypassing that config then reaches a missing `questionary`
dependency from the existing `tests/conftest.py`. No existing test suite
assertions have therefore been run.

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

The shared inspection models and discovery interface were not modified. The
repository's existing `pyproject.toml` conflict markers are outside this issue's
scope and must be resolved by the repository owner before full validation.
