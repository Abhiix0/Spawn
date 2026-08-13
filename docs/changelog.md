# Changelog

All notable changes to Spawn are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## v1.0.5 — 2026

### Added

- **Arrow-key selection menus** — every prompt in `spawn create` (template,
  framework, provider, CLI type, project type, extras, and Custom
  Structure's optional setup) now uses arrow-key/spacebar selection
  instead of typed numbers, powered by `questionary`.
- **`spawn` with no arguments** now shows the banner, current version, and
  a list of available commands, instead of Click's default usage error.

### Fixed

- **Consistent, clean cancellation** — pressing Ctrl+C at any point in
  `spawn create` (prompts, arrow-key menus, or mid-generation) now shows
  a single `Cancelled.` message and exits with code `130`, instead of a
  raw Python traceback or inconsistent messages depending on where the
  interrupt happened.

## v1.0.4 — 2026

### Added

- **AGENTS.md generation** — every generated project now ships an
  `AGENTS.md` file alongside its README, orienting coding agents on
  project structure, setup, and conventions. Uses a shared generic
  default for Automation, CLI, and Data Project, with template-specific
  content for Backend API (framework + run command), Chatbot/Agent
  (provider + required environment variable), RAG (required API key +
  ingestion behavior), and MCP Server (how to add tools/resources).
  Custom Structure generates it only when the user's pasted layout
  includes an `AGENTS.md` path, matching how README.md and .gitignore
  already work in that flow.
- **`--claude-md` / `--no-claude-md`** flag, interactive prompt, and
  `"claude_md"` config-file key — opt-in generation of an identical
  `CLAUDE.md` alongside `AGENTS.md`. Off by default.
- **`spawn doctor`** now checks for `AGENTS.md` as a Recommended-tier
  Documentation item.

## v1.0.3 — 2026

### Added

- **MCP Server intent** — `spawn create` can now scaffold a Model
  Context Protocol server using the official `mcp` Python SDK
  (`FastMCP`), with one working example tool and one example
  resource over `stdio` transport, plus a README explaining how to
  connect it to Claude Desktop or another MCP client.

## v1.0.2 — 2026

### Added

- **Non-interactive mode** — `spawn create` now accepts `--name`, `--template`,
  `--framework`, `--provider`, `--cli-type`, `--data-type`, `--extras`,
  `--git`/`--no-git`, and `--uv`/`--no-uv` flags, or a `--config <file.json>`
  JSON config file, to scaffold a project with zero prompts. Covers all 7
  registry templates (Custom Structure is not yet supported non-interactively).
- **`--dry-run`** — validates a non-interactive config and prints it without
  creating anything.
- **`--yes` / `-y`** — skips the GitHub-publish prompt. Non-interactive mode
  also always skips this prompt automatically, so agent-driven invocations
  never hang waiting for stdin.

## v1.0.1 — 2026

### Added

- **Custom Structure: dependency installation** — an optional "Dependencies (comma
  separated)" prompt when uv is enabled; packages install via `uv add` immediately
  after generation
- **Custom Structure: Optional Setup menu** — toggle Ruff, Pytest, Pre-commit, and/or
  Dockerfile; each installs its dependency (via `uv add --dev`) and generates its
  config file automatically
- **Custom Structure: README auto-population** — a pasted `README.md` is generated
  with real content (project name, structure tree, setup instructions) instead of
  being created empty
- **Custom Structure: smart .gitignore** — a pasted `.gitignore` is populated with
  Python defaults (`.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`,
  `.ruff_cache/`, etc.), plus an optional prompt for additional patterns,
  deduplicated against the defaults

### Fixed

- **Custom Structure metadata `source` field** — now reflects the actually detected
  input format (`tree`/`markdown`/`indented`) instead of a hardcoded `"tree"`
  placeholder

### Internal

- `install_packages()` gains an optional `dev: bool = False` parameter for
  `uv add --dev`; existing callers unaffected
- `ProjectConfig` gains `custom_dependencies`, `custom_dev_setup`,
  `custom_gitignore_extra`, `custom_source_format`
- `GITIGNORE_CONTENT` in `shared_content.py` extended with `.ruff_cache/`
- Version bumped to `1.0.1`

## v1.0.0 — 2026

### New Features

- **Custom Structure workflow** — bootstrap a project from your own pasted folder
  structure (Tree, Markdown list, or Indented format) instead of choosing a predefined
  blueprint; Spawn parses, previews detected folders/files, and reuses the existing
  Git/uv flow
- **Rich `.spawn/meta.json` metadata** — every generated project now records
  `created_at`, `generator`, `git`, `uv`, and `source` in addition to the existing
  `intent`/`framework`/`provider`/`spawn_version` fields; fully backward compatible
- **Doctor 2.0** — per-category health percentages (Documentation, Version Control,
  Configuration, Testing, Automation, Code Quality), three new checks (CHANGELOG.md,
  pyproject.toml, Type Checking, Pre-commit), tiered recommendations (Critical /
  Recommended / Optional), health rating label (Excellent / Good / Fair / Needs
  Attention), and a "Next Best Step" panel

### Internal

- `src/spawn/generators/custom_structure.py` — new module: `parse_structure()`,
  `ParsedEntry`, `CustomStructureGenerator`
- `ProjectConfig` gains `use_uv: bool = True` and `custom_entries: list | None = None`
- `StructureParseError` added to `core/exceptions.py`
- Doctor checks recategorized: `Quality` → `Testing` / `Code Quality`,
  `Deployment` → `Automation` (category names only; check logic unchanged)
- Version bumped to `1.0.0`

## v0.9.0 — 2026

### Added

- Data Project intent — 4 sub-types: Data Analysis, Dashboard, ETL Pipeline, Machine Learning
- Data Analysis: pandas + Jupyter notebook workflow with sample dataset
- Dashboard: Streamlit + Plotly interactive dashboard with sidebar filtering
- ETL Pipeline: configurable input/output paths via `.env`, data cleaning demo
- Machine Learning: RandomForestClassifier training script with per-run experiment logging to `experiments/`
- `ProjectConfig.data_type` field and matching CLI selection prompt ("Choose Project Type")
- Type-specific `.gitignore` rules for generated data artifacts (CSVs, models, experiment logs, notebook checkpoints)

### Fixed

- ETL `pipelines/run.py` next-step instruction caused `ModuleNotFoundError` — changed from script invocation (`python pipelines/run.py`) to module invocation (`python -m pipelines.run`)
- Dashboard used deprecated Streamlit `use_container_width` parameter, replaced with `width="stretch"`
- ML README example output didn't match actual results (dataset is trivially separable, always scores 1.0 accuracy) — corrected the documented example
- CLI prompt "Choose Data Type" renamed to "Choose Project Type" for clarity

## v0.8.0 — 2026

### New Features

- **RAG System intent** — generates a fully runnable Retrieval-Augmented Generation
  project using a fixed stack: LlamaIndex + ChromaDB + OpenAI
- **Fixed stack, no framework/provider prompt** — RAG skips the framework/provider
  selection entirely; `spawn create` goes straight from intent to extras
- **Auto-ingestion on first run** — if `chroma_db/` is empty, `src/main.py` ingests
  everything in `data/` automatically before accepting questions; no separate ingest
  command required
- **Sample knowledge base** — every generated project ships with
  `data/sample_knowledge.md` so users get a working Q&A demo immediately, with zero
  setup beyond an API key
- **Local vector persistence** — `src/knowledge/index.py` owns a
  `chromadb.PersistentClient` writing to `chroma_db/`, shared by both ingestion and
  retrieval
- **Correct modern LlamaIndex packaging** — installs `llama-index-core`,
  `llama-index-vector-stores-chroma`, `llama-index-embeddings-openai`,
  `llama-index-llms-openai`, and `chromadb` explicitly, instead of the heavy
  `llama-index` meta-package
- **`chroma_db/` gitignored correctly** — binary ChromaDB files are excluded via
  `.gitignore`, while a `.gitkeep` keeps the directory tracked in git

### Internal

- Registry: `rag` slug added with `available_extras` only — no `available_frameworks`
  or `available_providers`
- `RAGTemplate` follows the same `BaseTemplate` contract as other intents
  (`get_dependencies()`, `get_readme_content()`, `post_install()`, `next_steps`)
- `prompts.py` required no changes — empty `available_frameworks` and
  `available_providers` already skip those prompts automatically
- `shared_content.py`'s `GITIGNORE_CONTENT` extended with a `chroma_db/` rule
- Version bumped to `0.8.0`

## v0.7.0 — 2026

### New Features

- **AI Agent intent** — generates a fully runnable tool-calling agent project
  with `src/agent/`, `src/tools/`, `src/prompts/`, `src/config/`
- **2 frameworks**: PydanticAI, OpenAI Agents SDK
- **Provider-agnostic architecture** — users select a framework, not a provider;
  PydanticAI supports 6 providers (OpenAI, Anthropic, Gemini, OpenRouter, Ollama,
  Groq), OpenAI Agents SDK supports 2 (OpenAI, OpenRouter)
- **Calculator tool** — every generated agent ships with one working example
  tool, demonstrating real tool invocation with no API keys or external services
- **Centralized prompts** — `src/prompts/agent_prompt.txt` is editable without
  touching Python code
- **Provider-specific env vars and dependencies** — correct `.env.example` and
  `pyproject.toml` dependencies generated per framework + provider combination
  (e.g. `pydantic-ai[groq]` for the Groq combination)

### Internal

- Registry: `agent` slug added with `available_frameworks`, `available_providers`,
  and `available_extras`
- `AgentTemplate` follows the same `BaseTemplate` contract as chatbot/automation
  (`get_dependencies()`, `get_readme_content()`, `post_install()`, `next_steps`)
- CLI prompt flow filters provider choices per selected framework via
  `get_supported_providers()`, preventing invalid framework/provider combos
- Version bumped to `0.7.0`

## v0.6.0 — 2026

### New Features

- **AI Chatbot intent** — generates a fully runnable conversational AI project
  with runtime memory, centralized prompt management, and provider abstraction
- **3 frameworks**: PydanticAI, OpenAI SDK, LiteLLM
- **6 providers**: OpenAI, Anthropic, Gemini, OpenRouter, Ollama, Groq
- **16 supported combinations** — each generates correct dependencies,
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
