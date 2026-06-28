# Changelog

All notable changes to Spawn are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## v0.6.0 — 2026

### New Features

- **AI Chatbot intent** — generates a fully runnable conversational AI project
  with runtime memory, centralized prompt management, and provider abstraction
- **3 frameworks**: PydanticAI, OpenAI SDK, LiteLLM
- **5 providers**: OpenAI, Anthropic, Gemini, OpenRouter, Ollama
- **13 supported combinations** — each generates correct dependencies,
  provider-specific env vars, and working llm.py out of the box
- **Runtime memory** — `src/memory/history.py` maintains conversation
  context across turns within a session; no database required
- **Plain-text prompt system** — `src/prompts/system.txt` is editable
  without touching Python code; loaded dynamically at runtime
- **Rich extra** — opt-in `rich` terminal UI with colored panels and
  styled input/output
- **Provider-specific env vars** — generated `.env.example` uses the
  correct key name for each provider (OPENAI_API_KEY, ANTHROPIC_API_KEY,
  GOOGLE_API_KEY, OPENROUTER_API_KEY, OLLAMA_BASE_URL)

### Bug Fixes

- Fixed `result.data` → `result.output` in PydanticAI provider
  (AgentRunResult attribute name in current pydantic-ai)
- Fixed `setdefault("OPENAI_API_KEY")` pattern that silently broke
  non-OpenAI providers; api_key is now passed directly to run_sync()

### Internal

- `ProjectConfig` gains `provider: str | None = None` field
- `TemplateMetadata` gains `available_providers: list[str]` field
- `instantiate_template()` forwards `provider` to template constructors
- Registry: chatbot updated to 3 frameworks, 5 providers, 4 extras
- Version bumped to 0.6.0

## v0.5.0 — 2026

### New Features

- **Automation Tool intent** — generates a workflow-based automation project
  with `src/workflows/`, `src/tasks/`, `src/integrations/`, `src/utils/`,
  `logs/`, and a working example that runs immediately
- **Logging out of the box** — every generated project includes a `setup_logger()`
  utility and writes to `logs/app.log` with no manual configuration required
- **Working example workflow** — `load_sample_data → generate_report → log output`
  runs on first `uv run python -m src.main` without modification
- **`.env.example`** — pre-wired environment config template included in every
  generated project
- **Automation extras** — opt-in `ruff`, `pytest`, `github-actions`;
  installed and wired automatically

### Internal

- Registry expanded to three active templates: `backend-api`, `cli`, `automation`
- No new fields added to `ProjectConfig` or `TemplateMetadata` — automation
  uses the existing `extras` field; prompt flow adapts automatically via guards
- Version bumped to `0.5.0`

## v0.4.0 — June 2026

### New Features

- **CLI Application intent** — generates Typer, Click, or Argparse projects
  with Utility or Interactive sub-types; each produces the correct folder
  structure, main entry point, working example command, and tests
- **CLI type selection** — choose Utility (command-oriented) or Interactive
  (prompt-driven) at creation time; Utility generates `src/commands/` and
  `src/utils/`; Interactive adds `src/prompts/` and `src/ui/`
- **CLI extras** — opt-in `ruff`, `pytest`, `github-actions`; installed and
  wired automatically the same way as Backend API extras
- **Interactive README** — each CLI type × framework combination now produces
  a tailored README with the correct run command and commands table

### Breaking Changes

- The `python`, `data-science`, and `ml` template slugs have been removed
  from the active menu. These intents are planned for future re-registration
  as fully-featured, intent-based templates. Projects generated with those
  slugs are unaffected — `.spawn/meta.json` still records the original slug.

### Internal

- Registry reduced to two active templates: `backend-api` and `cli`
- `_REMOVED_SLUGS` updated to include `python`, `data-science`, `ml`
- CLI type prompt now precedes framework prompt (matches PRD spec)
- Version bumped to `0.4.0`

## v0.3.0 — June 2026

### Breaking Changes

- The `fastapi` template slug has been removed. FastAPI projects are
  now generated via the `backend-api` intent: `spawn create` →
  Backend API → FastAPI. There is no automatic migration for
  `.spawn/meta.json` files or any stored config referencing
  `template: "fastapi"`.

### New Features

- **Backend API intent** — generates production-structured FastAPI, Flask,
  or Django projects with full folder layouts, health routes, config, and tests
- **Framework selection** — choose FastAPI, Flask, or Django at creation time;
  each produces a different, correct project structure
- **Extras system** — opt-in extras at creation: `ruff`, `pytest`, `docker`,
  `github-actions`; selected extras are installed and configured automatically
- **Automatic dependency installation** — `uv add` runs after `uv init`;
  base and extra dependencies are installed into the project venv
- **Registry-driven menus** — template list, framework list, and extras list
  are all derived from registry metadata; no hardcoded prompt mappings
- **`instantiate_template()`** — new registry function that forwards
  `framework` and `extras` from `ProjectConfig` to templates that accept them
- **`.spawn/meta.json`** — every generated project receives a metadata file
  recording `intent`, `framework`, and `spawn_version`; excluded from git
  via `.gitignore`
- **`next_steps` on templates** — each template owns its run commands as a
  `next_steps` field; `next_steps.py` has been deleted

### Internal

- Templates restructured into per-intent subdirectories
  (`python_script/`, `fastapi_template/`, `data_science/`, `ml_project/`,
  `backend_api/`) — each with `__init__.py` and `content.py`
- `BaseTemplate` gains `generate()`, `get_readme_content()`,
  `get_dependencies()`, `post_install()`, and `next_steps` field
- `TemplateMetadata` added to registry with `available_frameworks` and
  `available_extras` fields
- `show_success()` signature updated to accept `next_steps: list[str]`
  directly from the template object
- `next_steps.py` removed; `utils/` is now free of slug-keyed dicts
- Version bumped to `0.3.0`

## v0.2.0 — GitHub Ninja

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
