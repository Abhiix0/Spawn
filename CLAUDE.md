# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Spawn (PyPI: `spawnio`, entry point `spawn = spawn.cli.app:main`) is a Typer/Rich CLI that scaffolds Python projects from intent-based templates (`spawn create`), scores project health (`spawn doctor`, `spawn doctor --fix`), and optionally publishes to GitHub. Python 3.12+, managed with uv, built with hatchling. Version lives in `pyproject.toml` (`spawn.__version__` reads it via importlib.metadata, with a hardcoded fallback in `src/spawn/__init__.py` that must be kept in sync).

## Commands

```bash
uv sync --all-groups                 # install incl. dev group
uv run pytest                        # all tests
uv run pytest tests/test_app.py      # one file
uv run pytest tests/test_app.py::test_name   # one test
uv run pytest --cov=src/spawn --cov-report=term-missing
uv run ruff check .                  # lint (CI runs pytest + ruff check)
uv run ruff format .                 # format (required before PRs)
```

## Architecture

Detailed reference: `docs/architecture.md`, `docs/commands.md`, `CONTRIBUTING.md`. Big picture:

- **Create flow**: `cli/app.py` → a `core/models.ProjectConfig` from either interactive `cli/prompts.py` (questionary, menus derived from the registry) or `cli/noninteractive.py` (flags / `--config` JSON, validated by `core/planning.py::plan_project`) → `generators/pipeline.py::generate_project`, which dispatches to `ProjectGenerator` (templates) or `CustomStructureGenerator` (`template == "custom"`). Both guard the destination via `generators/destination.py` (`assert_available`, `safe_join`), write folders/files/README/.gitignore, run git init and (unless `--no-uv`) `uv init`/`uv venv`/`uv add`/`template.post_install()`, then `generators/metadata.py::write_project_meta` writes `.spawn/meta.json`. On failure only a directory created by this run is removed (`cleanup_created`); `OSError` becomes `FilesystemError`.
- **Template registry** (`core/registry.py`): `TEMPLATES` dict of `TemplateMetadata` is the single source of truth for slugs, frameworks, extras, and prompt menus. `instantiate_template(config)` passes `framework`/`extras`/`cli_type` etc. to a template's constructor only if its signature accepts them (signature introspection), so constructor parameter names matter.
- **Templates** (`templates/<slug>/__init__.py` + `content.py`): subclass `BaseTemplate` (`templates/base.py`); `__init__.py` holds the class (dispatching on framework), `content.py` holds all file contents as string constants plus `make_readme()` / `make_agents_md()`. `templates/mcp_server/` is the minimal example to copy. Shared README/gitignore/CI/tool-config strings are in `templates/shared_content.py`; standalone file writers in `generators/project_files.py`.
- **Custom structure** (`generators/custom_structure.py`): parses pasted Tree/Markdown/Indented layouts and builds them without a template.
- **Doctor**: `utils/doctor.py` computes the 0–100 health score; `utils/doctor_fix.py` plans/applies fixes (`plan_fixes`, `apply_fixes`) — it never overwrites existing files or installs packages.
- **GitHub publishing**: `github/publisher.py` (`GitHubPublisher`), errors derive from `PublishError`. All errors derive from `SpawnError` (`core/exceptions.py`), each class with its own `exit_code`; `cli/errors.py::fail` prints `❌ message` and exits with it, `report_unexpected` exits 10 (traceback with `SPAWN_DEBUG=1`).
- **Metadata**: `.spawn/meta.json` is historical, not authoritative; read it with `core/project.py::read_project_metadata`. `ProjectConfig` is generation intent only.
- Every generated project ships an `AGENTS.md` (plus `CLAUDE.md` with `--claude-md`).

## Adding a template

Create `src/spawn/templates/<slug>/` (`__init__.py`, `content.py`), register a `TemplateMetadata` entry in `core/registry.py`, and add tests (see `tests/test_*_template.py` / `test_*_generator.py` pairs and `test_registry.py`). Slugs retired in earlier versions are listed in `_REMOVED_SLUGS`.
