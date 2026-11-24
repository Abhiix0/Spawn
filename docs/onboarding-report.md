# Onboarding JSON report

`spawn onboard [PATH] --json` emits one UTF-8 JSON object followed by a newline. The independent onboarding schema starts at `"1.0"`. The inspection JSON contract is separate.

| Key | Contents |
| --- | --- |
| `schema_version` | Onboarding schema version as a string |
| `generated_at` | UTC timestamp in ISO 8601 form |
| `status` | `complete` or `partial` |
| `repository` | Directory basename (`name`), `file_count`, and `directory_count` from discovery |
| `languages`, `frameworks` | Objects with `name`, `status`, `evidence`, and `evidence_count`. Status is `detected` or `candidate`. Each includes up to eight evidence references. |
| `entry_points` | Objects with `kind`, `target`, `state` (`detected` or `unknown`), `evidence`, and `reason` |
| `commands` | Objects with `category` (`install`, `start`, `test`, `lint`, or `format`), `argv` (array or null), `cwd`, `status`, `evidence`, and `note` |
| `structure` | `directories` at the root and selected `config_files` throughout the repository, including README, lockfiles, Python tooling and CI configuration |
| `diagnostic_counts` | Integer counts for `info`, `warning`, and `error` |

Evidence objects contain `path`, `indicator`, and `detail` (a source line reference or null). Paths are repository-relative with forward slashes. A command with `cwd` equal to `.` is relative to the inspected repository root.

An `explicit` command is backed by a recognized declaration. A `candidate` is inferred from static evidence. An `unknown` entry has null argv and explains the gap. Alternatives remain available within each category and working directory. Language and framework lists use name order, entries use kind, target and source path order, and commands use category and status before working directory and argv. Directory and config lists use path order. The timestamp can vary between equivalent reports.

Actual diagnostics go to stderr, summarized by severity unless `--verbose` is set. Verbose diagnostics use codes and relative paths. Reports omit absolute root paths, raw analyzer messages, raw recipe text, and recorded project metadata. Successful partial reports still exit 0. Invalid roots and fatal discovery return 7 and leave stdout empty. See the [command reference](commands.md#spawn-onboard).

The [FastAPI fixture](../tests/fixtures/static/onboarding/api-demo.json) contains a complete example with a fixed timestamp for testing.

## Large-tree benchmark

Run `uv run python tools/measure_onboarding_baseline.py` from the checkout.
The harness reports medians from three runs of each command on the Phase 0
2,000-file fixture. A second workload adds 2,000 files under `node_modules`
and 2,000 under a locally excluded scratch directory. The CLI measurements
include process startup.

Paired Linux Docker measurements on CPython 3.12.16 against `f2bb27f`, in seconds.

| Workload | Inspection core | Inspect CLI (JSON) | Onboard CLI (human) | Onboard CLI (JSON) |
| --- | ---: | ---: | ---: | ---: |
| 2,000 files, before | 0.789 | 1.762 | 2.877 | 2.833 |
| 2,000 files, after | 0.429 | 1.069 | 1.218 | 1.498 |
| With excluded trees, before | 0.863 | 2.454 | 3.655 | 2.602 |
| With excluded trees, after | 0.324 | 0.924 | 1.214 | 1.177 |

The tree digests matched in all runs. Inspection stayed complete. Onboarding
stayed partial because entry-point analysis reached its existing file limit.
The excluded workload went from 4,001 visible files to 2,001 after pruning
the local scratch directory. The built-in exclusion for `node_modules` applied
in both runs.

In the live Windows checkout, both onboarding modes had previously timed out
at 30 seconds. The stabilized checkout completed human onboarding in 11.96
seconds and JSON onboarding in 7.96 seconds. Inspection JSON completed in
8.46 seconds. The local scratch directory was skipped.

The [Phase 0 measurements](baseline/phase-0.md) recorded 1.993037 and 2.967307
seconds for inspection alone on Windows. Phase 2 recorded 3.132218 seconds
for the onboarding JSON CLI on Windows. Host load and platform differ across
these observations.
