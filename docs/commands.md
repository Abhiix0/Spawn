# Command Reference

## 1. Overview

| Command | Description | When to use it |
|---|---|---|
| `spawn create` | Scaffold a new Python project interactively | Starting a new project from a template |
| `spawn version` | Print the installed Spawn version | Confirming which version is on your PATH |
| `spawn doctor` | Score the current directory against project health checks | Auditing an existing project's setup |

---

## 2. `spawn create`

Creates a new project directory from a template, writes starter files, installs dependencies, optionally runs `git init`, and runs `uv init --bare` + `uv venv`.

### Prompt sequence

| Step | Prompt | When shown |
|---|---|---|
| 1 | `Project Name` | Always |
| 2 | Template list → `Choose Template [1-2]` | Always |
| 3 | CLI Type list → `Choose CLI Type [1-2]` | Only for CLI Application |
| 4 | Framework list → `Choose Framework [1-N]` | Only for templates with frameworks |
| 5 | Extras list → `Extras` | Only for templates with extras |
| 6 | `Initialize Git? [Y/n]` | Always |
| 7 | `Publish to GitHub? [y/N]` | Only if Git was enabled |
| 8 | `Repository URL` | Only if publish was confirmed |

#### `Project Name` validation

| Rule | Detail |
|---|---|
| Allowed characters | Letters, numbers, hyphens (`-`), underscores (`_`) |
| Required | At least one letter or digit |
| Rejected examples | `my project` (space), `my/project` (slash), `---` (no alphanumeric) |

**Error message (exact):**
```
Project name can only contain letters, numbers, hyphens (-), and underscores (_).
```

#### Template list

Templates are displayed as a numbered list. The current registry order:

| Input | Template | Description |
|---|---|---|
| `1` | `backend-api` | Backend API — production-ready FastAPI, Flask, or Django |
| `2` | `cli` | CLI Application — Typer, Click, or Argparse with Utility or Interactive type |

**Invalid input error (exact):**
```
Invalid choice. Please select a valid number.
```

---

### Backend API intent

Selecting Backend API triggers two additional prompts before the Git question.

#### Framework selection

```
  1  fastapi
  2  flask
  3  django

Choose Framework [1-3]:
```

| Input | Framework | Run command |
|---|---|---|
| `1` (default) | FastAPI | `uv run uvicorn app.main:app --reload` |
| `2` | Flask | `uv run python run.py` |
| `3` | Django | `uv run python manage.py runserver` |

Pressing Enter (empty) selects `1` (FastAPI).

#### Extras selection

```
  1  ruff
  2  pytest
  3  docker
  4  github-actions

  Enter numbers separated by commas, or press Enter to skip
Extras []:
```

| Extra | What it adds |
|---|---|
| `ruff` | Installs `ruff`; appends `[tool.ruff]` to `pyproject.toml` |
| `pytest` | Installs `pytest` + `httpx`; adds `filterwarnings` config to `pyproject.toml` |
| `docker` | Writes `Dockerfile` and `.dockerignore` for the selected framework |
| `github-actions` | Writes `.github/workflows/ci.yml` with ruff + pytest steps |

Enter comma-separated numbers (e.g. `1,2`) or press Enter to skip all. Invalid numbers are silently ignored.

#### Dependency installation

After `uv init`, Spawn calls `uv add` with the base and selected-extras dependencies automatically. No manual `pip install` or `uv add` is needed.

| Framework | Base dependencies |
|---|---|
| FastAPI | `fastapi`, `uvicorn[standard]`, `pydantic-settings` |
| Flask | `flask`, `python-dotenv` |
| Django | `django` |

#### Generated project structure (FastAPI example)

```
my-api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── models/
│   ├── schemas/
│   └── services/
├── tests/
│   ├── __init__.py
│   └── test_health.py
├── .env.example
├── .spawn/
│   └── meta.json
├── .gitignore
├── README.md
└── pyproject.toml
```

#### Generated project structure (Flask example)

```
my-api/
├── app/
│   ├── __init__.py         # App factory (create_app)
│   ├── config.py
│   └── routes/
│       ├── __init__.py
│       └── health.py
├── run.py
├── tests/
│   ├── __init__.py
│   └── test_health.py
├── .env.example
├── .spawn/
│   └── meta.json
└── pyproject.toml
```

#### Generated project structure (Django example)

```
my-api/
├── manage.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   └── health/
│       ├── __init__.py
│       ├── views.py
│       ├── urls.py
│       └── tests.py
├── .spawn/
│   └── meta.json
└── pyproject.toml
```

#### Next steps by framework

| Framework | Command |
|---|---|
| FastAPI | `uv run uvicorn app.main:app --reload` |
| Flask | `uv run python run.py` |
| Django | `uv run python manage.py runserver` |

---

### CLI Application intent

Selecting CLI Application triggers two additional prompts before the extras and Git questions.

#### CLI Type selection

```
  1  utility
  2  interactive

Choose CLI Type [1-2]:
```

| Input | CLI Type | Description |
|---|---|---|
| `1` (default) | `utility` | Command-oriented CLI; generates `src/commands/` and `src/utils/` |
| `2` | `interactive` | Prompt-driven CLI; adds `src/prompts/` and `src/ui/` |

Pressing Enter (empty) selects `1` (utility).

#### Framework selection

```
  1  typer
  2  click
  3  argparse

Choose Framework [1-3]:
```

| Input | Framework | Dependencies |
|---|---|---|
| `1` (default) | Typer | `typer` |
| `2` | Click | `click` |
| `3` | Argparse | None (stdlib only) |

#### Extras selection

```
  1  ruff
  2  pytest
  3  github-actions

  Enter numbers separated by commas, or press Enter to skip
Extras []:
```

| Extra | What it adds |
|---|---|
| `ruff` | Installs `ruff`; appends `[tool.ruff]` to `pyproject.toml` |
| `pytest` | Installs `pytest`; appends `[tool.pytest.ini_options]` to `pyproject.toml` |
| `github-actions` | Writes `.github/workflows/ci.yml` with ruff + pytest steps |

#### Generated project structure (Typer utility example)

```
my-cli/
├── src/
│   ├── __init__.py
│   ├── commands/
│   │   └── __init__.py
│   ├── utils/
│   │   └── __init__.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   └── test_cli.py
├── .spawn/
│   └── meta.json
├── .gitignore
├── README.md
└── pyproject.toml
```

#### Generated project structure (Typer interactive example)

```
my-cli/
├── src/
│   ├── __init__.py
│   ├── commands/
│   │   └── __init__.py
│   ├── prompts/
│   │   └── __init__.py
│   ├── ui/
│   │   └── __init__.py
│   ├── utils/
│   │   └── __init__.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   └── test_cli.py
├── .spawn/
│   └── meta.json
├── .gitignore
├── README.md
└── pyproject.toml
```

#### Next steps by CLI type

| CLI Type | Command |
|---|---|
| Utility | `uv run python -m src.main hello` |
| Interactive | `uv run python -m src.main greet` |

---

### `.spawn/meta.json`

Every generated project receives a `.spawn/meta.json` file:

```json
{
  "intent": "backend-api",
  "framework": "fastapi",
  "spawn_version": "0.3.0"
}
```

This file is excluded from git via `.gitignore`. It records the intent slug, framework used (or `null`), and the Spawn version that created the project.

---

### `Initialize Git?`

| Answer | Behavior |
|---|---|
| `Y` / Enter | Prints `Initializing Git...` (yellow), runs `git init` |
| `N` | Skips `git init`. After success panel, prints: `ℹ GitHub publishing requires Git. Skipping.` (yellow). Command ends — no GitHub prompt. |

### `Publish to GitHub?`

Only shown when Git was enabled. Default is **N**.

| Answer | Behavior |
|---|---|
| `N` / Enter | Command ends after success panel |
| `Y` | Prompts `Repository URL`, then runs publish flow |

#### `Repository URL` formats

| Format | Example |
|---|---|
| HTTPS | `https://github.com/user/repo` |
| HTTPS with `.git` | `https://github.com/user/repo.git` |
| SSH | `git@github.com:user/repo.git` |

### Success panel

```
╭────── ✨ Project Created Successfully ──────╮
│                                              │
│  Project      my-api                         │
│  Template     Backend API                    │
│  Git          ✓ Enabled                      │
│  UV           ✓ Initialized                  │
│  Virtual Env  ✓ Created                      │
│                                              │
│  Next Steps                                  │
│    cd my-api                                 │
│    uv run uvicorn app.main:app --reload      │
│                                              │
╰──────────────────────────────────────────────╯
```

### Error cases

All generation errors are prefixed with `❌` in red. The partially created directory is deleted on failure.

| Situation | Message (exact) |
|---|---|
| Directory already exists | `❌ Directory '{name}' already exists.` |
| Git not installed | `❌ Git is not installed or not available in PATH.` |
| uv not installed | `❌ UV is not installed or not available in PATH.` |
| uv command failed | `❌ {uv stderr}` or `❌ Failed to initialize UV environment.` |
| Package install failed | `❌ {uv stderr}` or `❌ Failed to install packages.` |
| Unknown template | `❌ Unknown template: {template}` |
| Invalid GitHub URL | `❌ Invalid GitHub repository URL.` |
| Origin remote already exists | `❌ Origin remote already exists.` |

---

## 3. `spawn version`

Prints the installed package version.

**Output (exact):**

```
Spawn v0.3.0
```

---

## 4. `spawn doctor`

Scans the **current working directory** for project health indicators and prints a weighted score out of 100.

### All checks

| Check Name | Category | Weight | What it looks for |
|---|---|---|---|
| README.md | Documentation | 10 | `README.md` file exists |
| LICENSE | Documentation | 5 | `LICENSE` file exists |
| Git Repository | Version Control | 15 | `.git/` directory exists |
| .gitignore | Version Control | 10 | `.gitignore` file exists |
| Tests | Quality | 15 | `tests/` directory exists |
| Ruff | Quality | 10 | `ruff.toml`, `.ruff.toml`, or Ruff config/dependency in `pyproject.toml` |
| Pytest | Quality | 10 | `pytest.ini`, `setup.cfg` `[pytest]`, or Pytest config/dependency in `pyproject.toml` |
| Dockerfile | Deployment | 10 | `Dockerfile` file exists |
| GitHub Actions | Deployment | 10 | `.github/workflows/*.yml` or `*.yaml` |
| .env.example | Configuration | 5 | `.env.example` file exists |

**Max score:** 100

### Scoring

| Score range | Color | Meaning |
|---|---|---|
| 80%+ | Green | Strong project hygiene |
| 50–79% | Yellow | Core setup present, gaps remain |
| 0–49% | Red | Missing multiple essentials |

---

## 5. Exit codes

| Situation | Exit code |
|---|---|
| Command completes successfully | 0 |
| `spawn create` — `SpawnError` caught | 0 |
| `spawn create` — `GitHubPublishError` caught | 0 |
| Uncaught exception (e.g. keyboard interrupt) | 1 |
