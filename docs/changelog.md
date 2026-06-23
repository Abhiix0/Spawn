# Changelog

All notable changes to Spawn are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

# Changelog

All notable changes to Spawn are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## v0.3.0 (unreleased)

### Breaking Changes

- The `fastapi` template slug has been removed. FastAPI projects are
  now generated via the `backend-api` intent: `spawn create` →
  Backend API → FastAPI. There is no automatic migration for
  `.spawn/meta.json` files or any stored config referencing
  `template: "fastapi"`.

### New Features

- Backend API intent: generates production-structured FastAPI, Flask,
  or Django projects
- Framework selection: choose FastAPI, Flask, or Django at creation time
- Extras system: opt-in ruff, pytest, docker, github-actions support
- Dependency installation: `uv add` runs automatically after generation
- Registry-driven menus: template list derived from registry, no
  hardcoded prompt mappings
- `instantiate_template()`: forwards framework and extras from
  ProjectConfig to templates that accept them

### Internal

- Templates restructured into per-intent subdirectories
- BaseTemplate gains generate(), get_readme_content(),
  get_dependencies(), post_install() methods
- TemplateMetadata added to registry with available_frameworks and
  available_extras fields

## v0.2.0 — GitHub Ninja (current)

Release theme: "From local project creation to a live GitHub repository without leaving the terminal."

### Added

- `spawn create` now asks "Publish to GitHub?" after project creation if Git was enabled
- `GitHubPublisher` class — stages all files, creates initial commit, renames branch to `main`, adds remote origin, pushes to GitHub
- GitHub URL validation — accepts `https://github.com/user/repo`, `.git` suffix variants, and SSH format `git@github.com:user/repo.git`
- `GitHubPublishError` exception — subclass of `SpawnError` for publishing-specific failures
- `spawn doctor` command — project health checker with 10 checks across 5 categories (Documentation, Version Control, Quality, Deployment, Configuration)
- `ProjectHealthChecker` class with weighted scoring system (100 points total)
- Prioritized recommendations for failed health checks
- Dynamic version reading via `importlib.metadata` — no more hardcoded version string
- Fuller `.gitignore` template — covers `__pycache__`, `.venv`, `dist/`, `build/`, `*.egg-info`, IDE files, OS files, pytest cache
- GitHub Actions CI workflow — runs `ruff check` and `pytest` on every push and pull request to `main`
- `ruff` added to dev dependencies

### Fixed

- `success.py` and `next_steps.py` merged into a single panel — previously showed two separate "Next Steps" sections back to back
- `run_git_command()` now catches `FileNotFoundError` and raises `SpawnError` — previously crashed with unhandled exception if git was not installed
- `except Exception` in `doctor.py` replaced with `except (OSError, ValueError)` — targeted exception handling
- `get_template()` return type annotated as `BaseTemplate | None`
- `git.py` and `uv.py` failures now raise `SpawnError` instead of `RuntimeError`
- All `write_text()` calls now include `encoding="utf-8"` — prevents crash on Windows with non-ASCII project names
- All subprocess calls use `capture_output=True` — git and uv output no longer bleeds into the Rich UI
- `project_path.mkdir(exist_ok=True)` replaced with existence check + `SpawnError` — prevents silent merge into existing folder
- Validator regex updated to require at least one letter or digit — previously accepted `-` and `--` as valid project names
- `test_templates.py` missing `FastAPITemplate` import fixed — was causing CI failure

## v0.1.0 — Project Generator (initial release)

Release theme: "Eliminate repetitive project setup."

### Added

- `spawn create` — interactive CLI for project generation
- 4 project templates: Python Script, FastAPI, Data Science, ML Project
- `BaseTemplate` dataclass — extensible template architecture with `name`, `folders`, `starter_files`
- Template registry — string key to template class mapping
- `ProjectGenerator` — orchestrates folder creation, README, `.gitignore`, git init, uv init
- `spawn version` command
- `SpawnError` — base exception, raised and caught cleanly throughout
- Rich terminal UI — success panel, template selection table, next steps panel
- Project name validation — letters, numbers, hyphens, underscores only
- Git integration — optional `git init` on project creation
- uv integration — `uv init --bare` and `uv venv` run automatically
- Template-specific next steps — each template shows the exact commands to run after creation
- Test suite — 62+ tests covering templates, registry, models, validators, generator, doctor
