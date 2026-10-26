# Static Language and Framework Detection Support Matrix (#55)

This is the initial Spawn v1.1.0 support matrix. Detection is static and local:
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

`pydantic` and `starlette` are emitted as `framework` findings; whether they
meet the contract's "application-level framework" definition is pending a
decision in #58.

## Error and ambiguity behavior

- Every positive finding contains at least one repository-relative `Evidence`.
- Manifest-only framework evidence is `inferred` and includes a `detail` reason.
- Weak directory names and README mentions do not produce framework findings.
- Shared or ambiguous file extensions are not forced into one language.
- Malformed, unreadable, non-UTF-8, and over-limit files produce recoverable
  diagnostics where applicable; results are `partial` when diagnostics exist.
- Unsupported technologies are omitted, not guessed or confirmed.
- Inventory traversal/exclusions remain the responsibility of Issue #54.
