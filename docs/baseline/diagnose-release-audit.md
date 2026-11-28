# Diagnose release audit

Scope is the local v1.3.0 candidate on `v130`, starting at `c7e9b74`.
The comparison baseline is the `v1.2.0` tag. The earlier phase-zero
[baseline](phase-0.md) established separate interpreter environments, local
package smoke, read-only fixtures, and a separate remote-CI gate. Its timing
and filename-encoding caveats still apply.

## Independent corpus and walkthrough

On Windows CPython 3.12.13, run
`uv run --python 3.12 python tools/evaluate_diagnostics.py`. The script writes
the complete labels and expected evidence before invoking Diagnose, then
records all discrepancies. Ten hand-authored repositories exercise FastAPI,
Flask, Django, Starlette, a packaged CLI, a frontend, a mixed multi-project
tree, malformed TOML, excluded targets, and hostile declarations. The
implementation fixtures are separate. The two positive and two negative
examples per rule share configurations across frameworks, so these are
correlated examples and a narrow validation of the supported syntax.

| Rule | TP / FP / FN | Precision | Defect recall | Pass | Unknown | Not applicable |
| --- | --- | --- | --- | --- | --- | --- |
| `py-container-001` | 2 / 0 / 0 | 2/2 | 2/2 | 2 | 4 | 2 |
| `py-deps-001` | 2 / 0 / 0 | 2/2 | 2/2 | 2 | 5 | 1 |
| `py-entry-001` | 2 / 0 / 0 | 2/2 | 2/2 | 2 | 5 | 1 |
| `py-test-001` | 2 / 0 / 0 | 2/2 | 2/2 | 2 | 5 | 1 |
| `py-test-002` | 2 / 0 / 0 | 2/2 | 2/2 | 2 | 4 | 2 |

Each row has ten labeled rule/repository observations. A true positive
requires the exact evidence and warning severity. An unmatched claim counts
as a false positive and a missed labeled defect as a false negative. Precision
uses TP/(TP+FP) and recall uses TP/(TP+FN). An undefined denominator is N/A.
All 50 labels matched. No rule returned failed or not checked. No rule was
tuned and no error findings occurred. These numbers do not estimate
production precision or recall.

The automated walkthrough started with the FastAPI dispatch fixture.
The terminal report had five warnings. The script applied the next steps
below to that fixture, re-ran with `--fail-on warning`, and obtained
`status=complete`, five passes, zero findings and exit 0.

| Finding title | Reported location | Walkthrough edit |
| --- | --- | --- |
| Final Python Docker stage selects root | `Dockerfile:3` | Select the declared unprivileged runtime account in the example. |
| Requirements include is missing | `requirements.txt:2` | Restore the referenced `config/pinned.txt`. |
| Console script target is absent from its module | `dispatch.py`, `pyproject.toml [project.scripts]` | Define the intended `start` function. |
| Pytest testpaths entry is missing | `pyproject.toml [tool.pytest.ini-options.testpaths]` | Restore the `qa/suites` directory. |
| Make recipe names a missing pytest config | `Makefile:3` | Restore `config/check.ini`. |

The frontend capture showed `0 findings | 0 checks evaluated`,
`PARTIAL ANALYSIS`, five unknown outcomes, and exit 9. Both cases are emitted
as terminal captures by the evaluator. This is reproducible technical
triage evidence. No independent developer or user participated.

## Security

New rule reads remain inventory-member reads through the existing anchored
reader. File handles reject links and reparse points, and the per-report
cache stays bounded. The CLI tests inject a substitution immediately after
discovery and execute the actual command in both output modes. Linux uses a
symlink and Windows uses a junction. Tests also exercise malformed UTF-8
names on Linux, hostile names and source, invalid input, private canaries,
and an unprivileged Linux unreadable subtree. Target mutation, subprocess
execution and network use are checked separately.

The Windows focused run passed 63 tests with eight platform skips. Linux
as UID `nobody` passed 169 with one Windows-only skip. Full-suite expected
failures are tracked separately below.

## Paired performance

Export `v1.2.0` source with `git archive --format=tar v1.2.0 src`, extract
it away from the candidate, and run
`uv run --python 3.12 python tools/measure_diagnostics_release.py BASELINE/src`.
Both sides used one Linux Docker CPython 3.12.16 environment with the same
locked dependencies and the same fixture directories. Three fresh-process
pairs per row alternate baseline-first and candidate-first. Core time
includes imports and analysis inside the worker. CLI time includes process
startup and output capture. Startup is the version command. The driver
reuses the original inspection fixture and digest helper and the onboarding
Git/local exclusion builder.

The audit tolerates median increases within 20% or 50 ms, whichever is
larger. This accommodates process scheduling variance and short-core noise
on three runs while still flagging material changes for profiling and a
focused rerun. It is a local comparison rule, not a latency promise. The
largest old-command increase was about 10.2% for large-tree onboarding
core. The sample ranges overlap and no old command triggered the tolerance.

Measurements are in seconds, median [minimum–maximum].

| Fixture | Command/mode | v1.2.0 | Candidate |
| --- | --- | --- | --- |
| Small | startup | 1.493 [1.476–1.495] | 1.582 [1.389–1.670] |
| Small | inspect/core | 0.220 [0.199–0.265] | 0.146 [0.113–0.235] |
| Small | inspect/human | 1.873 [1.598–2.764] | 1.832 [1.713–2.405] |
| Small | inspect/json | 1.733 [1.595–1.884] | 1.802 [1.302–1.931] |
| Small | onboard/core | 0.240 [0.168–0.266] | 0.193 [0.133–0.194] |
| Small | onboard/human | 1.436 [1.431–2.467] | 1.466 [1.458–1.741] |
| Small | onboard/json | 1.539 [1.350–1.680] | 1.537 [1.518–1.596] |
| Small | diagnose/core | — | 0.172 [0.171–0.182] |
| Small | diagnose/human | — | 1.720 [1.602–1.907] |
| Small | diagnose/json | — | 2.311 [1.904–2.983] |
| 2,000 files | startup | 1.402 [1.144–1.450] | 1.263 [1.130–1.364] |
| 2,000 files | inspect/core | 0.645 [0.590–0.745] | 0.646 [0.518–0.717] |
| 2,000 files | inspect/human | 2.187 [2.082–2.570] | 2.210 [2.058–2.458] |
| 2,000 files | inspect/json | 2.018 [1.676–3.116] | 2.176 [1.934–2.316] |
| 2,000 files | onboard/core | 1.082 [0.916–1.538] | 1.192 [0.777–1.361] |
| 2,000 files | onboard/human | 2.538 [2.170–2.692] | 2.425 [2.178–2.863] |
| 2,000 files | onboard/json | 2.296 [1.902–2.806] | 2.035 [1.998–2.731] |
| 2,000 files | diagnose/core | — | 0.254 [0.172–0.257] |
| 2,000 files | diagnose/human | — | 1.352 [1.315–1.600] |
| 2,000 files | diagnose/json | — | 1.324 [1.258–1.367] |
| Excluded trees | startup | 1.099 [1.049–1.171] | 1.157 [1.118–1.254] |
| Excluded trees | inspect/core | 0.493 [0.427–0.561] | 0.441 [0.416–0.572] |
| Excluded trees | inspect/human | 1.621 [1.415–1.806] | 1.458 [1.420–2.193] |
| Excluded trees | inspect/json | 1.758 [1.647–2.071] | 1.905 [1.565–2.323] |
| Excluded trees | onboard/core | 0.875 [0.823–1.102] | 0.781 [0.735–1.089] |
| Excluded trees | onboard/human | 2.209 [1.676–3.335] | 1.752 [1.663–2.243] |
| Excluded trees | onboard/json | 1.821 [1.668–2.139] | 1.610 [1.558–1.621] |
| Excluded trees | diagnose/core | — | 0.208 [0.170–0.215] |
| Excluded trees | diagnose/human | — | 1.313 [1.180–1.450] |
| Excluded trees | diagnose/json | — | 1.332 [1.100–1.362] |
| 10,001 entries | diagnose/core | — | 0.154 [0.127–0.211] |
| 10,001 entries | diagnose/human | — | 1.180 [1.036–1.306] |
| 10,001 entries | diagnose/json | — | 1.128 [1.087–1.363] |

No timeouts or digest changes. The three normal fixtures returned complete
coverage. The 10,001-entry fixture hit the inventory cap and consistently
reported partial with exit 9 in both CLI modes. Diagnose process peak RSS
was 25,600–28,140 KiB in core and 40,336–42,484 KiB in the CLI. The
measurement records sample RSS for the old commands as well. The existing
single-inventory and shared-read assertions remain in the test suite.

## Matrix procedure

Each matrix cell uses a separate environment and the checked-in lockfile.
The Linux images are `python:3.12-bookworm` and `python:3.13-bookworm`.
Use the corresponding version for `X`:

```bash
uv sync --locked --all-groups --python X
uv run --python X python -V
uv run --python X python -c "import sys; assert sys.version_info[:2] == tuple(map(int, sys.argv[1].split('.')))" X
uv run --python X pytest -p no:cacheprovider -q -rs --tb=short
uv run --python X ruff check .
uv run --python X ruff format --check .
uv run --python X python -m compileall -q src tests tools
uv build --python X
UV_PYTHON=X bash .github/scripts/smoke.sh 1.3.0
```

The Windows builds used a clean source export and separate output folders
for each interpreter. The smoke commands ran from those folders' parent
with exactly one wheel in `dist`. Git Bash used a temporary LF copy of the
script. The generated project and wheel metadata both reported 1.3.0.
The smoke has assertions for both version flags, metadata, creation,
Doctor, inspection and onboarding JSON, and Diagnose success, threshold,
partial coverage and invalid root.

The first Windows attempt was blocked by the sandbox denying access to
the hatchling index. Fresh environments with approved access resolved
that. The initial Docker wrapper failed before invoking uv due to shell
quoting; running an LF script resolved it. The first package smoke used a
generated scaffold below Doctor's success threshold. A separate fixture
with known coverage exercises Doctor successfully. The existing Doctor
exit contract and health scoring are unchanged.

Only the project's version changed in `uv.lock`. The CI matrix now supplies
the selected interpreter to each `uv run` and asserts its runtime version.
Earlier baseline logs showed that implicit runs honored the 3.12 pin even
when launched in an environment intended for 3.13. GitHub Actions has not
run against this candidate.

| Platform and verified interpreter | Full pytest | Sync, version assertion, Ruff lint and format, compileall | Wheel and sdist | Clean-wheel smoke |
| --- | --- | --- | --- | --- |
| Windows 3.12.13 | 2,319 passed, 45 skipped | Exit 0 each | Exit 0 | Exit 0 |
| Windows 3.13.13 | 2,319 passed, 45 skipped | Exit 0 each | Exit 0 | Exit 0 |
| Linux 3.12.16 | 2,355 passed, 9 skipped | Exit 0 each | Exit 0 | Exit 0 after fixture correction |
| Linux 3.13.18 | 2,355 passed, 9 skipped | Exit 0 each | Exit 0 | Exit 0 after fixture correction |

Pytest exited 0 in all cells with zero expected failures or unexpected
passes. Windows skips include unavailable symlink privileges and
POSIX-only checks. Linux skips include Windows junction cases and two
permission cases requiring a non-root user, which ran separately in the
unprivileged security suite. Detailed logs, failed setup attempts,
terminal captures and benchmark samples are retained locally under the
ignored `.tmp-diagnostics/phase4/` directory.

## Release gates

| Gate | Status | Evidence |
| --- | --- | --- |
| A — Functional | PASS | Five checks match all 50 independent labels, including exact warning evidence; the CLI and partial/threshold contract are tested. |
| B — Automated quality | PASS | Full pytest, Ruff lint and format, and compileall across the local matrix. |
| C — Compatibility | PASS | Both supported Python minors on Windows and Linux, existing CLI contract tests and JSON goldens, and clean installs. |
| D — Security | PASS | Actual CLI tests on both containment backends, private canaries, inert input, and Linux unprivileged permission coverage. |
| E — Performance | PASS | Paired results within the tolerance; discovery bounds and read-only digests verified. |
| F — Developer experience | PASS | Actionable terminal evidence and remediation walkthrough; structured output and CI exit handling documented. |
| G — Release engineering | PASS | Local fallback, metadata, lock, wheel, and sdist agree on 1.3.0. Remote CI is pending. |
| H — Product value | BLOCKED | Automated evidence is available. Independent human acceptance remains pending. |

The candidate is ready for remote CI. Release approval is blocked on human
acceptance and the remote checks for the exact candidate.
