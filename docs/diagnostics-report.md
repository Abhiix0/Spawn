# Internal diagnostics report

Diagnostics schema **1.0** describes proved static repository issues and the
coverage of the rules that check for them. A repository issue is separate from
an inspection finding (an observed fact) and an inspection diagnostic (analysis
health). Diagnostics do not participate in project configuration or doctor
scoring. The registry has no CLI entry point.

## Outcomes and completeness

| Outcome | Meaning |
| --- | --- |
| pass | The rule evaluated the condition with sufficient evidence and found it absent. |
| finding | One or more distinct occurrences of the static condition were proved. |
| unknown | Scope was unclear or the required evidence or coverage was insufficient. |
| not_checked | The rule could not start or was skipped. |
| not_applicable | Positive file evidence established that the rule was outside its scope. |
| failed | The rule raised or returned an invalid result. |

Every outcome carries a fixed reason code. Rule errors use fixed codes
without copying exception messages. A report is **failed** when the root is
unavailable or discovery fails fatally. It is **partial** when required
inventory, inspection, or rule coverage is missing, including when limits
prevent evaluation. Otherwise it is **complete**. Out-of-scope rules leave
completeness unchanged. Completeness describes coverage. A clean report
requires complete coverage, at least one pass, and zero findings. Empty
registries and runs with only out-of-scope rules are unevaluated.

## Findings and wire format

Rules declare stable lowercase IDs and categories, fixed issue descriptions,
and any structured evidence keys in code. Each issue carries a title,
problem, recommendation, severity, and one or more repository-relative file
locations. Each location may specify a one-based line or a rule-owned key.
Evidence must refer to an inventory member. Descriptions and keys are authored
by the rule, and the report carries no source lines or configuration values.
Unsafe locations are rejected. Credential resources and environment files
are excluded from reads and evidence.

An occurrence ID hashes the rule ID, issue kind, and canonical evidence
locations. Exact repeats collapse. Conflicting entries for one occurrence
are invalid, and distinct locations or issue kinds remain distinct. The
flattened findings order is error, warning, info, then rule ID and evidence
location with issue kind as a tie-breaker. JSON stores findings within
outcomes using that order, with outcomes sorted by rule ID.

JSON uses UTF-8 and carries a schema version, repository label, status,
coverage, derived counts and clean flag, and rule outcomes. The opaque label
is a hash of the checkout basename. It is nullable for an unavailable root
and may match for unrelated checkouts with the same name. The report omits
absolute roots and timestamps. The decoder accepts exactly schema 1.0 and
validates all required fields, derived values, and occurrence identities.
Unknown versions or fields and duplicate JSON object keys are rejected.

## Limits and coverage

Discovery counts at most 10,000 directory entries, including skipped items.
The shared reader reserves at most 512 read requests and 128,000,128 bytes
across inspection and rules, and the aggregate analysis budget allows 100,000
work units. Each rule defaults to 32 read requests, 8,000,008 reserved bytes,
and 25,000 work units. Reservations charge the requested cap plus one byte
for overflow detection, including requests served from the bounded cache.
Each request reaching the reader is charged once against the shared budget.
The built-in rules cap each read at 64 KiB and use one discovery inventory.
Rules charge custom iteration with the context work budget and use bounded
inventory reads. Discovery limits discard incomplete inventories. Rules
check the relevant inventory scope for absence claims and abstain when a
required read is missing, undecodable, or over budget. Git and standard
directory exclusions define the inventory scope. Skipped links inside a
rule's relevant scope prevent absence claims there.

## Python checks

All five checks emit warnings. They require a readable root pyproject with a
named project and abstain when another discovered project manifest or an uv
workspace makes ownership unclear. Paths use a restricted literal syntax.
The checks abstain on excluded paths, link gaps, ambiguous case, and unsupported
syntax. An unsupported input can prevent the entire rule from drawing a
conclusion, including when another declaration in that rule is understood.

| Rule | Evidence and example | Remediation |
| --- | --- | --- |
| `py-entry-001` | A script such as `demo = "cli:main"` refers to a declared flat setuptools module whose parsed top level contains only plain functions and an optional docstring, with no `main` binding. The report cites the scripts table and module, grouping missing attributes in the same module. | Correct the target or define the intended function. |
| `py-test-001` | A literal entry such as `testpaths = ["unit"]` in `tool.pytest.ini_options` names no file or directory in the inventory. One issue covers the affected list. | Restore the path, update the list, or remove its stale entry. |
| `py-test-002` | A standalone root Makefile `test` recipe such as `pytest -c unit.ini` names a file absent from the root inventory. The recipe line is the evidence. | Restore the config file or correct the option. |
| `py-deps-001` | A literal `-r requirements/dev.txt` or `--requirement=requirements/dev.txt` in root `requirements.txt` names a missing file. Each missing include gets its own line reference. | Restore the file or correct the include. |
| `py-container-001` | A declared FastAPI, Starlette, Flask, or Django project has a supported Dockerfile whose final Python stage ends with an explicit `USER root` or `USER 0`. The final USER line is the evidence. | Select an unprivileged account and grant it the required file access. |

- Console scripts support only explicit root `py-modules` in setuptools with
  the standard backend and bare setuptools build requirement. Imports,
  reexports, annotations, dynamic hooks, conditional definitions, alternate
  layouts, and unresolved targets cause abstention.
- Testpaths checks require no competing root pytest configuration and use the
  literal list from the manifest. The finding describes a stale declaration.
- The Makefile check covers `make -f Makefile test` from the repository root
  with a single literal recipe, optional `.PHONY: test`, and either `pytest`
  or `python -m pytest`. Variables, shell operators, extra arguments, included
  makefiles, and alternate working directories are outside the supported shape.
- Requirements include checking stays in the root file. It neither follows
  include chains nor interprets URLs, quoted paths, continuations, or other
  pip options. The dependency analyzer's package facts support recognizing
  ordinary requirement lines. They cannot establish a complete environment,
  so the catalog has no rule for an undeclared pytest dependency.
- Docker scope requires a bare framework dependency in the root manifest.
  The last stage must name a literal tagged official Python image. The parser
  accepts simple stage declarations, literal USER, and a narrow subset of RUN,
  COPY, WORKDIR, EXPOSE, and JSON CMD and ENTRYPOINT instructions. Stage
  inheritance, variable USER, parser directives, and multiline syntax cause
  abstention. An omitted USER does not trigger a finding. The rule describes
  the Dockerfile default.

## Severity rubric

| Severity | Use |
| --- | --- |
| error | A verified static defect in a declared project contract that calls for correction. |
| warning | A verified inconsistency or omission with a practical maintenance or development impact. |
| info | A verified condition with a concrete, optional improvement. |

Severity reflects the static condition. Runtime outcomes require runtime
evidence and fall outside this report.
