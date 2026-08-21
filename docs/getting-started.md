# Getting Started

## 1. Prerequisites

| Requirement | Minimum version | Install |
|---|---|---|
| Python | 3.12 | [python.org/downloads](https://www.python.org/downloads/) |
| uv | any | `pip install uv` or [github.com/astral-sh/uv](https://github.com/astral-sh/uv) |
| Git | any | [git-scm.com/downloads](https://git-scm.com/downloads/) |

> **Python 3.12 is required.** `pip install spawnio` will silently return "no matching distribution" on Python < 3.12. If you're using uv, run `uv python install 3.12` to get a compatible interpreter in seconds.

---

## 2. Installation

**From PyPI (recommended)**

```bash
pip install spawnio
```

or using `uv`:

```bash
uv tool install spawnio
```

or run once without installing:

```bash
uvx --from spawnio spawn create
```

**From source (for contributing)**

```bash
git clone https://github.com/Abhiix0/spawn.git
cd spawn
uv sync
uv tool install .
```

After installation, `spawn` is available anywhere on your machine.

---

## 3. Verify the installation

```bash
spawn version
# Spawn v1.0.7
```

Or just run `spawn` with no arguments to see the command overview:

```
SPAWN — scaffold your next project
v1.0.6

Commands
  create    Scaffold a new project
  doctor    Check the health of a project directory
  version   Show the installed version

Run spawn COMMAND --help for details on a command.
```

---

## 4. Your first project

### Option A — Backend API (FastAPI)

```bash
spawn create
```

```
Project Name: my-api

? Choose a template (Use arrow keys)
 » Backend API
   CLI Application
   ...

? Choose a framework (Use arrow keys)
 » fastapi
   flask
   django

? Select extras (space to toggle, enter to confirm)
 ○ ruff
 ○ pytest
 ○ docker
 ○ github-actions

Initialize Git? [Y/n]: Y
Also generate CLAUDE.md for Claude Code? [y/N]: N
```

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

```bash
cd my-api
uv run uvicorn app.main:app --reload
# GET http://localhost:8000/ → {"status": "running"}
```

---

### Option B — CLI Application (Typer, utility)

```bash
spawn create
```

```
Project Name: my-cli

? Choose a template (Use arrow keys)
   Backend API
 » CLI Application
   ...

? Choose CLI Type (Use arrow keys)
 » utility
   interactive

? Choose a framework (Use arrow keys)
 » typer
   click
   argparse

? Select extras (space to toggle, enter to confirm)
 ○ ruff
 ○ pytest
 ○ github-actions

Initialize Git? [Y/n]: Y
Also generate CLAUDE.md for Claude Code? [y/N]: N
```

```bash
cd my-cli
uv run python -m src.main hello
```

---

### Option C — Non-interactive (zero prompts)

```bash
spawn create --name my-api --template backend-api --framework fastapi --extras ruff,pytest --no-git
```

Or from a JSON config file:

```json
{
  "name": "my-api",
  "template": "backend-api",
  "framework": "fastapi",
  "extras": ["ruff", "pytest"],
  "git": false,
  "uv": true
}
```

```bash
spawn create --config spawn.json
```

Use `--dry-run` to validate and print the config without creating any files:

```bash
spawn create --name my-api --template backend-api --dry-run
# ✓ Config valid
# ProjectConfig(name='my-api', template='backend-api', ...)
```

---

## 5. What gets created

Every generated project includes:

| File | Purpose |
|---|---|
| `README.md` | Project README with setup and run instructions |
| `AGENTS.md` | Agent context file (structure, setup, conventions) |
| `.gitignore` | Python defaults |
| `.spawn/meta.json` | Spawn metadata (intent, framework, version, timestamps) |
| `pyproject.toml` | Project config + installed dependencies |
| `.venv/` | Local virtual environment |

**Backend API / FastAPI structure:**

```
my-api/
├── app/
│   ├── api/routes/health.py   # GET / → {"status": "running"}
│   ├── core/config.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── tests/
│   └── test_health.py
├── .env.example
├── AGENTS.md
├── README.md
├── .gitignore
└── pyproject.toml
```

---

## 6. All 8 templates at a glance

| Template | Slug | Frameworks | Run command |
|---|---|---|---|
| Backend API | `backend-api` | fastapi / flask / django | `uv run uvicorn app.main:app --reload` (fastapi) |
| CLI Application | `cli` | typer / click / argparse | `uv run python -m src.main hello` |
| Automation Tool | `automation` | — | `uv run python -m src.main` |
| AI Chatbot | `chatbot` | pydantic-ai / openai-sdk / litellm | `uv run python -m src.main` |
| AI Agent | `agent` | pydantic-ai / openai-agents | `uv run python -m src.main` |
| RAG System | `rag` | — (LlamaIndex + ChromaDB + OpenAI) | `uv run python -m src.main` |
| Data Project | `data` | — | varies by sub-type |
| MCP Server | `mcp` | — (official mcp SDK) | `uv run python -m src.server` |

For full details on each template — structures, all prompt options, available extras, and run commands — see [commands.md](commands.md) or the [Project Templates section of README.md](../README.md#project-templates).

---

## 7. Check project health

After creating a project (or on any existing Python project):

```bash
cd my-api
spawn doctor
```

Spawn scores the project out of 135 across Documentation, Version Control, Configuration, Testing, Automation, and Code Quality, and shows a prioritized recommendation for the most impactful next improvement.

---

## 8. Next steps

- All commands and flags → [commands.md](commands.md)
- Architecture and contribution guide → [architecture.md](architecture.md)
- Full version history → [changelog.md](changelog.md)
