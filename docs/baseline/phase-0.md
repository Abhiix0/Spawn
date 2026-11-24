# Phase 0: Baseline and Release Readiness

- Baseline run date: 2026-11-24
- Starting revision: `1644f4e` (`v1.1.2`, clean `main`)
- Baseline environment: Windows, uv 0.11.11, uv-managed CPython 3.12.13 and 3.13.13
- Package: `spawnio 1.1.2`

This phase establishes test, package, inspection-contract, adversarial-fixture,
and read-only baselines. It adds no inspection capabilities and changes no
public JSON fields or CLI behavior.

## Baseline before Phase 0 changes

| Check | Result |
|---|---|
| `uv sync --all-groups` | PASS, exit 0 |
| `uv run pytest` | PASS, 2,109 passed, 34 skipped, exit 0 |
| Python 3.12 CI-equivalent suite | PASS, 2,109 passed, 34 skipped; Ruff and format passed |
| Python 3.13 CI-equivalent suite | PASS, 2,109 passed, 34 skipped; Ruff and format passed |
| Focused inspection CLI and sample contract tests | PASS, 77 passed, 1 skipped |
| `uv run ruff check .` | PASS, exit 0 |
| `uv run ruff format --check .` | PASS, 148 files formatted |
| `uv build` | PASS, wheel and sdist built |
| `.github/scripts/smoke.sh` | PASS using Git Bash; clean wheel install and generated-project smoke |
| `uv run python -m compileall -q src tests` | PASS, exit 0 |

The baseline used the documented uv workflow. An initial unprivileged uv test
attempt could not access uv's user cache; the same command completed after the
environment granted cache access. The blocked attempt and successful log are
both retained.

## Added baseline corpus and contracts

- `secret_canary` contains a fake secret in ignored environment files and a
  Python payload that would create a marker if executed. Inspection must neither
  reveal the canary nor create the marker, and a before/after tree snapshot must
  remain identical.
- The symlink case points into a canary file outside the inspected root. On
  platforms that permit creating the link, inspection must not expose or alter
  the target. Windows did not permit the symlink in this run, so this case was
  skipped locally.
- `large_tree` deterministically materializes 2,000 Python files and a project
  manifest. `tools/measure_inspection_baseline.py` measures `run_inspection`
  against a temporary instance and verifies the tree digest before and after.
- `tests/fixtures/static/inspect_exit_codes.json` records existing exit behavior:
  complete JSON inspection 0, invalid root 7, unknown option 2, and partial
  inspection 0. The sample report remains the byte-for-byte JSON CLI golden.
- Existing discovery tests retain the one-inventory-walk and symlink-pruning
  assertions; the new corpus reuses that discovery and analyzer pipeline.

## Verification after changes

Final results are captured in [`logs/`](logs/). Key measurements:

| Check | Result |
|---|---|
| Focused safety, CLI, discovery and report-contract tests | PASS, 108 passed, 16 skipped |
| Ruff check | PASS, exit 0 |
| Ruff format | PASS after formatting the new measurement helper |
| Large-tree inspection | PASS, 2,000 source files, 1.993037 seconds, complete report, no contract errors, read-only digest unchanged |
| Final full Python 3.12 suite | PASS, 2,115 passed, 35 skipped, exit 0 |
| Final full Python 3.13 suite | PASS, 2,115 passed, 35 skipped, exit 0 |
| Ruff check / format, Python 3.12 and 3.13 | PASS, exit 0 on both versions |
| `python -m compileall -q src tests tools` | PASS on Python 3.12 and 3.13, exit 0 |
| Final `uv build` | PASS, wheel and sdist built |
| Final clean-wheel smoke (`smoke.sh 1.1.2`) | PASS, exit 0 |
| `uv run spawn --version` | PASS, `Spawn v1.1.2`, exit 0 |

Two first attempts exposed test-maintenance issues and are retained: the fixture
catalog assertion required baseline-only archetypes to be excluded from its
golden table, and the corpus helper needed Ruff formatting. Both were corrected.
One full run also measured an existing 5-second large-file timing test at 8.36
seconds; the isolated rerun passed in 3.38 seconds and both final full suites
passed. Its initial failure log remains available for context.

## Platform status and limitations

- **Windows / Python 3.12.13 and 3.13.13:** the finalization rerun used separate
  uv environments and the checked-in lockfile. Each suite passed with 2,115
  passed and 35 skipped. Ruff lint, format and compileall passed on both.
  Windows skipped the external symlink canary because the process lacked the
  required privilege. The finalization measurement inspected 2,000 source
  files in 2.967307 seconds with a valid report and unchanged tree digest.
  `uv build --python 3.12` and the clean-wheel smoke via Git Bash also passed.
- **Local Linux / Python 3.12.16 and 3.13.18:** Docker Desktop ran the full
  suites using uv 0.11.11 and the checked-in lockfile. Each suite passed with
  2,142 passed, 7 skipped and 1 expected failure. Ruff lint, format and
  compileall passed. The external symlink canary test passed on both versions.
  The containers ran as root, so the
  existing POSIX permissions test that requires a non-root user was skipped.
  The expected failure covers JSON encoding of filenames with non-UTF-8 bytes.
- **Local Linux package:** `uv build` and `bash .github/scripts/smoke.sh 1.1.2`
  passed. The first smoke attempt encountered CRLF in the Windows snapshot.
  The rerun restored Git's LF line endings in the temporary container only.
- **Remote Linux CI:** BLOCKED for this checkout. The GitHub Actions jobs in
  `.github/workflows/ci.yml` must pass before release approval. A locally
  verified Phase 0 commit can proceed while the remote result is pending.
- No target fixture is executed by inspection or the performance harness. The
  reports contain no secret-canary value, and tests compare the fixture tree
  before and after inspection.

The finalization logs retain the failed timing runs as well as the successful
Docker reruns. The existing large-file parser test exceeded its five-second
limit on initial Windows and Linux runs. The assertion was kept intact. The
first runs in the Python 3.13 image used Python 3.12 because uv honored the
repository's `.python-version`. The final run explicitly selected Python 3.13
and confirmed it in the pytest header.

Finalization evidence includes the [Windows command and exit log](logs/finalization-windows-serial.txt),
the [Linux 3.12 run](logs/finalization-linux-3.12-serial.txt),
the [Linux 3.13 run](logs/finalization-linux-python-3.13.txt), and the
[Linux package smoke](logs/finalization-linux-package.txt).
