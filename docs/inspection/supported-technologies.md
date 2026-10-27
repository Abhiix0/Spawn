# Supported Technologies (Spawn v1.1.0)

This is the Spawn v1.1.0 support matrix for language, framework, dependency, package-manager and tooling detection (#55-#57). Detection is static and local:
Spawn reads only paths supplied by `DiscoveryInventory`, never imports or runs
repository code, installs packages, or accesses the network. Findings describe
evidence in files; they do not assert that a project builds or works at runtime.

## Language indicators

A source extension is direct evidence that a language is represented. Recognized
manifests are direct evidence of a project in that language. Findings can include
multiple languages in a repository or monorepo. A language with no supported
indicator is omitted rather than reported as absent.

| Subject | Direct source extensions | Manifest indicators |
|---|---|---|
| `python` | `.py`, `.pyi` | `pyproject.toml` with `[project]` or `[tool.poetry]` |
| `javascript` | `.js`, `.mjs`, `.cjs`, `.jsx` | `package.json` with package metadata/dependency/script keys |
| `typescript` | `.ts`, `.tsx` | — |
| `java` | `.java` | `pom.xml`, `build.gradle` |
| `kotlin` | `.kt`, `.kts` | `build.gradle.kts` |
| `go` | `.go` | `go.mod` |
| `rust` | `.rs` | `Cargo.toml` |
| `c` | `.c` | — |
| `cpp` | `.cc`, `.cpp`, `.cxx`, `.hpp`, `.hh`, `.hxx` | — |
| `c-sharp` | `.cs` | `*.csproj` |
| `ruby` | `.rb` | `Gemfile` |
| `php` | `.php` | `composer.json` |
| `swift` | `.swift` | `Package.swift` |
| `dart` | `.dart` | `pubspec.yaml` |
| `elixir` | `.ex`, `.exs` | `mix.exs` |
| `erlang` | `.erl`, `.hrl` | — |
| `haskell` | `.hs`, `.lhs` | — |
| `scala` | `.scala`, `.sc` | — |
| `lua` | `.lua` | — |
| `perl` | `.pl`, `.pm` | — |
| `r` | `.r` | — |
| `julia` | `.jl` | — |
| `shell` | `.sh`, `.bash`, `.zsh` | — |
| `sql` | `.sql` | — |
| `cython` | `.pyx` | — |

`.h` is intentionally not mapped because C and C++ share the extension. `.vue`
and `.svelte` are not used as JavaScript language evidence by themselves. File
extensions are not proof of syntactic validity or buildability. Manifest parsing
is bounded to 1 MB; malformed or unreadable manifests produce diagnostics.

## Framework indicators

Framework dependency declarations alone produce `inferred` findings with an
explanation. A recognized source import/declaration or framework-specific config
or entry-point file produces `detected`. Both states require repository-relative
evidence. `detected` means the static indicator exists, not that the framework
is correctly configured or operational.

| Subject | Manifest package names | Static imports | Config/entry-point |
|---|---|---|---|
| `react` | `react` in `package.json` | JS/TS import from `react` | — |
| `nextjs` | `next` in `package.json` | import from `next` | `next.config.js`, `.mjs`, `.ts` |
| `vue` | `vue` in `package.json` | import from `vue` | — |
| `nuxt` | `nuxt` in `package.json` | import from `nuxt` | `nuxt.config.js`, `.ts` |
| `angular` | `@angular/core` in `package.json` | import from `@angular/` | `angular.json` |
| `svelte` | `svelte` in `package.json` | import from `svelte` | `svelte.config.js` |
| `express` | `express` in `package.json` | import/require from `express` | — |
| `fastapi` | `fastapi` in Python dependency manifests | Python import | — |
| `flask` | `flask` in Python dependency manifests | Python import | — |
| `django` | `django` in Python dependency manifests | Python import | `manage.py` |
| `starlette` | `starlette` in Python dependency manifests | Python import | — |
| `pydantic` | `pydantic` in Python dependency manifests | Python import | — |
| `laravel` | `laravel/framework` in `composer.json` | — | — |

Python package names are extracted from PEP 508 requirement strings and
normalized per PEP 503 (`Flask (>=2)`, `name[extra]>=1; marker` and
`pkg @ url` all resolve to their distribution name). Manifest sources:
`package.json` and `composer.json` dependency tables; `pyproject.toml`
`[project].dependencies`, `[project.optional-dependencies]`,
`[dependency-groups]` (strings only; `include-group` entries are skipped) and
Poetry `dependencies`, `dev-dependencies` and `group.*.dependencies`;
`Pipfile` (TOML `[packages]` and `[dev-packages]`); and line-oriented
`requirements.txt` / `requirements-dev.txt`. Nested includes, environment
markers, dynamic metadata, lockfiles and build scripts are not resolved.
`Gemfile`, `pom.xml` and `build.gradle*` are not parsed for frameworks, so
Rails and JVM frameworks are not detected.

Known false negatives: imports split across several lines
(`import {
 a,
 b } from 'react'`), destructured `require()` calls
(`const { Router } = require('express')`), and non-`import` forms such as
dynamic `import()`.

Known false positives: import-like text inside comments, string literals and
template literals (for example code samples embedded in generator templates) is
matched, because detection is regex-based and does not parse source.

`pydantic` and `starlette` are emitted as `framework` findings, like the others, so they can become `primary_framework` when they have the most evidence.

`Pipfile` is read by the framework detector for package names (TOML `[packages]`, `[dev-packages]`). The `rails` package rule exists but never fires: `Gemfile` is not parsed, so Rails is not detected. `pyproject.toml` language evidence needs `[project]` or `[tool.poetry]`; `.pyx` maps to the `cython` language.

## Error and ambiguity behavior

- Every positive finding contains at least one repository-relative `Evidence`.
- Manifest-only framework evidence is `inferred` and includes a `detail` reason.
- Weak directory names and README mentions do not produce framework findings.
- Shared or ambiguous file extensions are not forced into one language.
- Malformed, unreadable, non-UTF-8, and over-limit files produce recoverable
  diagnostics where applicable; results are `partial` when diagnostics exist.
- Unsupported technologies are omitted, not guessed or confirmed.
- Inventory traversal/exclusions remain the responsibility of Issue #54.

## Dependencies and package managers (#56)

One `dependency` finding (always `detected`) is emitted per directly declared package, with the declaring manifest as evidence. Only these sources are read; everything else is omitted, never guessed.

| Source | Read |
|---|---|
| `pyproject.toml` | `[project].dependencies`, `[project.optional-dependencies].*`, `[dependency-groups].*` (strings only; `include-group` tables skipped), `[tool.poetry]` `dependencies` / `dev-dependencies` / `group.*.dependencies` (`python` skipped), `[tool.uv].dev-dependencies`. A `[project].dynamic` entry `dependencies` gives `dependency.dynamic_metadata` and no guesses |
| `requirements.txt`, `requirements-*.txt` | any depth, line-oriented |
| `package.json` | `dependencies`, `devDependencies`, `peerDependencies`, `optionalDependencies` |

Python names are PEP 503 normalized; npm names are lowercased with the `@scope/` prefix kept. At most 500 manifests are read (`dependency.manifest_limit_reached`).

`package_manager` findings:

| Subject | Indicator | State |
|---|---|---|
| `uv` | `uv.lock`, `[tool.uv]` | detected |
| `poetry` | `poetry.lock`, `[tool.poetry]` | detected |
| `pipenv` | `Pipfile`, `Pipfile.lock` (presence only, never read for dependencies) | detected |
| `npm` | `package-lock.json`, `npm-shrinkwrap.json`, `package.json` `packageManager` | detected |
| `yarn` | `yarn.lock`, `packageManager` | detected |
| `pnpm` | `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `packageManager` | detected |
| `bun` | `bun.lock`, `bun.lockb`, `packageManager` | detected |
| `pip` | a requirements file | inferred (the tool actually used is not confirmed) |

Several managers are all reported; none is declared the winner.

## Tooling (#57)

Evidence is a static indicator only. Nothing claims a tool runs or passes. No YAML parser exists, so YAML-based indicators are detected by path presence and their content is never parsed. `.env` files are never read.

| Category | Subject | Indicator |
|---|---|---|
| `tool` | `ruff` | `ruff.toml`, `.ruff.toml`, `pyproject.toml` `[tool.ruff]` |
| `tool` | `black` | `pyproject.toml` `[tool.black]` |
| `tool` | `flake8` | `.flake8`, `setup.cfg` / `tox.ini` `[flake8]` |
| `tool` | `mypy` | `mypy.ini`, `.mypy.ini`, `[tool.mypy]`, `setup.cfg` `[mypy]` |
| `tool` | `pyright` | `pyrightconfig.json`, `[tool.pyright]` |
| `tool` | `pytest` | `pytest.ini`, `[tool.pytest.ini_options]`, `setup.cfg` `[tool:pytest]`, `tox.ini` `[pytest]` |
| `tool` | `eslint` | `.eslintrc*`, `eslint.config.{js,mjs,cjs,ts}`, `package.json` `eslintConfig` |
| `tool` | `prettier` | `.prettierrc*`, `prettier.config.{js,cjs,mjs}`, `package.json` `prettier` |
| `tool` | `jest` | `jest.config.{js,ts,mjs,cjs,json}`, `package.json` `jest` |
| `tool` | `vitest` | `vitest.config.{js,ts,mjs,cjs}` |
| `tool` | `pre-commit` | `.pre-commit-config.yaml` |
| `tool` | `git` | `.git` at the root (seen via discovery's skipped list): detected; only a root `.gitignore` / `.gitattributes`: inferred |
| `ci` | `github-actions` | `.github/workflows/*.yml` or `*.yaml` (one level) |
| `ci` | `gitlab-ci`, `circleci`, `jenkins`, `azure-pipelines` | `.gitlab-ci.yml`, `.circleci/config.yml`, `Jenkinsfile`, `azure-pipelines.yml` (repository root only) |
| `container` | `docker` | `Dockerfile`, `Dockerfile.*`, `*.Dockerfile` detected; only `.dockerignore` inferred |
| `container` | `docker-compose` | `docker-compose.y[a]ml`, `compose.y[a]ml` |
| `database` | `postgres` | `psycopg`, `psycopg2`, `psycopg2-binary`, `asyncpg`, `pg` |
| `database` | `mysql` | `pymysql`, `mysqlclient`, `mysql-connector-python`, `mysql2` |
| `database` | `mongodb` | `pymongo`, `motor`, `mongodb`, `mongoose` |
| `database` | `redis` | `redis`, `ioredis` |
| `database` | `sqlite` | `aiosqlite`, `better-sqlite3` |
| `structure` | `tests-directory` | root `tests`, `test` or `__tests__` |
| `structure` | `src-layout` | `src/<pkg>/__init__.py` |
| `structure` | `spawn-generated` | `.spawn/meta.json` that is a JSON object (marker only; present but unusable is inferred plus `tooling.malformed_metadata`) |

A tool config makes the tool `detected`. A tool declared as a dependency without config is `inferred`. Databases are always `inferred`, from driver packages only. `not_detected` (with the checked paths in `detail`) is reported only for `git`, `pytest`, `ruff`, `github-actions`, `docker` and `tests-directory`; for `pytest` and `ruff` a broken manifest or the manifest cap makes absence `unknown` instead.

## Limitations

- Directory exclusions match basenames at any depth, case-insensitively: `build`, `dist`, `env`, `venv`, `target`, `vendor`, `coverage`, `htmlcov`, `node_modules`, `__pycache__`, `.git` and similar are skipped wherever they occur, even when they hold real source.
- `.git` is detected only because discovery lists it as skipped; an export without `.git` reports git as `inferred` at best.
- Framework imports are regex-based: import-like text in comments or strings is a false positive (inspecting Spawn itself reports `django` because template sources contain it); multi-line and destructured imports are missed.
- A framework found only through a dependency declaration is `inferred`, and `summary.primary_framework` may be such an inferred framework. It is picked by evidence count, which reflects representation, not importance.
- CI, container and pre-commit detection is presence-only: no YAML is parsed.
- Databases are inferred from driver packages only; READMEs, `.env`, data files and compose images are not evidence.
- A pip and an npm package with the same name share one `(category, subject)` identity and merge into one finding.
- Unsupported manifests produce no dependency findings: `Pipfile` (package-manager presence only), `setup.py`, `setup.cfg`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`, `pom.xml`, Gradle files, and every lockfile as a dependency source.
- `summary.name` is the directory basename, not the project name declared in a manifest.
- Files over 1 MB are skipped with a diagnostic.
