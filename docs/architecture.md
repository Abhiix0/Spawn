# Architecture

## 1. Overview

Spawn is a Python CLI tool built with Typer and Rich. It scaffolds new Python projects from templates, optionally publishes them to GitHub, and scores existing projects for environment health.

The three main capabilities are **project generation** (`spawn create`), **GitHub publishing** (optional post-create flow), and **environment health checking** (`spawn doctor`).

## 2. Technology Stack

| Tool | Version | Role |
|---|---|---|
| Python | 3.12+ | Core language |
| Typer | 0.26.7+ | CLI framework |
| Rich | 15.0.0+ | Terminal UI |
| uv | any | Environment management |
| Git | any | Version control |
| Hatchling | any | Build backend |

Entry point: `spawn.cli.app:main` (defined in `pyproject.toml` as `[project.scripts]`).

## 3. Repository Structure

```
src/spawn/
├── __init__.py         # __version__ via importlib.metadata, fallback "0.6.0"
├── cli/
│   ├── app.py          # Typer app: create, version, doctor commands
│   └── prompts.py      # Interactive prompts; derives menu from registry
├── core/
│   ├── exceptions.py   # SpawnError — base exception
│   ├── models.py       # ProjectConfig dataclass (name, template, use_git, framework, extras)
│   └── registry.py     # TemplateMetadata, TEMPLATES dict, get_template(),
│                       # instantiate_template(), get_metadata(), list_templates()
├── generators/
│   └── project_generator.py  # Orchestrates generation, dependency install, meta.json write
├── github/
│   ├── exceptions.py   # GitHubPublishError
│   ├── publisher.py    # GitHubPublisher — stages, commits, pushes
│   └── validators.py   # GitHub URL validation
├── templates/
│   ├── base.py         # BaseTemplate dataclass
│   ├── shared_content.py     # README_CONTENT, GITIGNORE_CONTENT
│   ├── backend_api/
│   │   ├── __init__.py       # BackendAPITemplate (dispatches by framework)
│   │   └── content.py        # All FastAPI/Flask/Django/Docker/CI content strings
│   ├── cli_application/
│   │   ├── __init__.py       # CLITemplate (dispatches by framework + cli_type)
│   │   └── content.py        # All framework × cli_type content strings
│   ├── automation/
│   │   ├── __init__.py       # AutomationTemplate
│   │   └── content.py        # Workflow, task, logger, test, README content strings
│   ├── chatbot/
│   │   ├── __init__.py       # ChatbotTemplate (branches on framework)
│   │   └── content.py        # LLM provider, chat, prompt, test, README strings
│   ├── python_script/        # Reserved — not in active menu
│   ├── data_science/         # Reserved — not in active menu
│   └── ml_project/           # Reserved — not in active menu
└── utils/
    ├── banner.py       # show_banner() — ASCII wordmark with ice-fade colours
    ├── console.py      # Shared Rich Console instance
    ├── doctor.py       # ProjectHealthChecker, run_health_check()
    ├── git.py          # initialize_git(), run_git_command(), add_all(), commit() etc.
    ├── success.py      # show_success() — renders the success panel
    ├── uv.py           # initialize_uv(), install_packages()
    └── validators.py   # validate_project_name()
```

## 4. Key Flows

### 4a. Project Creation Flow

1. User runs `spawn create`
2. `app.create()` calls `show_banner()`
3. `get_project_config()` collects name, template, framework, extras, and Git preference
4. `ProjectGenerator.generate()` resolves the template via `instantiate_template(config)`,
   creates directories, writes starter files, writes README and `.gitignore`, runs
   `initialize_git()` (if enabled), `initialize_uv()`, `install_packages()`, `post_install()`,
   and writes `.spawn/meta.json`
5. `show_success()` renders the success panel using `template_obj.next_steps`
6. If Git was enabled, optionally `GitHubPublisher.publish()` stages, commits, and pushes

```
spawn create
    │
    ▼
show_banner()                 banner.py
    │
    ▼
get_project_config()          prompts.py
    │  → ProjectConfig (name, template, framework, extras, use_git)
    ▼
ProjectGenerator.generate()   project_generator.py
    ├── instantiate_template()  registry.py  (forwards framework + extras)
    ├── mkdir + write files     templates/
    ├── write README.md         shared_content.py
    ├── write .gitignore        shared_content.py
    ├── initialize_git()        git.py         (if use_git)
    ├── initialize_uv()         uv.py
    ├── install_packages()      uv.py          (if deps non-empty)
    ├── post_install()          template       (ruff/pytest config, Docker, CI)
    └── write .spawn/meta.json
    │
    ▼
show_success()                success.py
    └── template_obj.next_steps (formatted with project_name)
    │
    ▼
GitHubPublisher.publish()     publisher.py    (optional)
```

### 4b. Template System

`BaseTemplate` is a dataclass with these fields:

| Field | Type | Purpose |
|---|---|---|
| `name` | `str` | Display name shown in the success panel |
| `folders` | `list[str]` | Directories created under the project root |
| `starter_files` | `list[tuple[str, str]]` | `(relative_path, content_template)` pairs; `{project_name}` substituted at write time |
| `next_steps` | `list[str]` | Run commands shown after creation; `{project_name}` substituted at display time |

`BaseTemplate` also provides overridable methods:

| Method | Default | Purpose |
|---|---|---|
| `generate(project_path, context)` | Creates folders and writes starter files | Template-specific generation |
| `get_readme_content(context)` | Returns `None` (use shared README) | Custom README per template |
| `get_dependencies()` | Returns `[]` | Packages to install via `uv add` |
| `post_install(project_path)` | No-op | Config writes, Docker files, CI files |

Each template lives in its own subdirectory with an `__init__.py` (class) and `content.py` (string constants).

#### Registry

`registry.py` holds `TEMPLATES: dict[str, TemplateMetadata]`. Current entries in order:

| Key | Template class | Frameworks | Extras |
|---|---|---|---|
| `backend-api` | `BackendAPITemplate` | fastapi, flask, django | ruff, pytest, docker, github-actions |
| `cli` | `CLITemplate` | typer, click, argparse | ruff, pytest, github-actions |
| `automation` | `AutomationTemplate` | none | ruff, pytest, github-actions |
| `chatbot` | `ChatbotTemplate` | pydantic-ai, openai-sdk | ruff, pytest, github-actions |

`get_template(slug)` returns a default-constructed instance. `instantiate_template(config)` forwards `framework`, `extras`, and `cli_type` from `ProjectConfig` to templates whose constructors accept them, using signature introspection.

`_REMOVED_SLUGS = {"fastapi", "python", "data-science", "ml"}` documents slugs that existed in previous versions but are no longer registered.

### 4c. Backend API Dispatch

`BackendAPITemplate.__init__` branches on `framework` to select the correct folder list,
starter files, and next steps:

```
framework == "flask"   → FLASK_FOLDERS, FLASK_FILES, flask next steps
framework == "django"  → DJANGO_FOLDERS, DJANGO_FILES, django next steps
else (None/"fastapi")  → FASTAPI_FOLDERS, FASTAPI_FILES, fastapi next steps
```

`get_dependencies()` returns base deps for the framework plus any selected extras.
`post_install()` writes ruff config, pytest filterwarnings, Dockerfile, `.dockerignore`,
and/or `.github/workflows/ci.yml` depending on `self.extras`.

### 4d. Error Handling

```
SpawnError                    # core/exceptions.py
└── GitHubPublishError        # github/exceptions.py
```

`ProjectGenerator.generate()` wraps its body in try/except. Any `OSError` is converted to
`SpawnError`; any `BaseException` (including `SpawnError`) triggers `shutil.rmtree()` rollback
before re-raising. The CLI catches both exception types and prints `❌ {message}` in red.

## 5. Adding a New Template

1. Create `src/spawn/templates/your_intent/` with `__init__.py` and `content.py`
2. Subclass `BaseTemplate`; set `name`, `folders`, `starter_files`, `next_steps`
3. Override `get_dependencies()`, `post_install()`, `get_readme_content()` as needed
4. Register in `registry.py` — add a `TemplateMetadata` entry to `TEMPLATES`
5. Write tests in `test_templates.py` and `test_registry.py`

## 6. Running Tests

```bash
uv run pytest
uv run pytest -v
uv run pytest tests/test_generator.py
uv run ruff check .
```
