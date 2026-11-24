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

Run `uv run python tools/measure_onboarding_baseline.py` from the checkout. The
harness times inspection and the installed `spawn onboard --json` command on
the same 2,000-file fixture, then compares the tree digest. On Windows with
CPython 3.12, inspection took 1.852273 seconds and onboarding took 3.132218
seconds, including CLI startup. The digest matched. Onboarding was partial
because the entry-point analysis reached its file limit.

The [Phase 0 measurements](baseline/phase-0.md) recorded 1.993037 and
2.967307 seconds for inspection alone on this fixture. These are observations
from separate runs.
