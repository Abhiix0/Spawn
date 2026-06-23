# Getting Started

## 1. Prerequisites

| Requirement | Install command | Link |
|---|---|---|
| Python 3.12+ | `uv python install 3.12` | [python.org/downloads](https://www.python.org/downloads/) |
| uv | `pip install uv` | [github.com/astral-sh/uv](https://github.com/astral-sh/uv) |
| Git | `brew install git` | [git-scm.com/downloads](https://git-scm.com/downloads/) |

## 2. Installation

```bash
git clone https://github.com/Abhiix0/Spawn.git
cd Spawn
uv sync
uv tool install .
```

You can now run `spawn` from anywhere on your machine.

## 3. Your First Project

### Option A — Python Script (simplest)

```bash
$ spawn create
```

```
  1  Backend API
  2  Python Script
  3  Data Science
  4  ML Project

Choose Template [1-4]: 2
Initialize Git? [Y/n]: y
Initializing Git...

╭────── ✨ Project Created Successfully ──────╮
│                                              │
│  Project      my-script                      │
│  Template     Python Script                  │
│  Git          ✓ Enabled                      │
│  UV           ✓ Initialized                  │
│  Virtual Env  ✓ Created                      │
│                                              │
│  Next Steps                                  │
│    cd my-script                              │
│    uv run python main.py                     │
│                                              │
╰──────────────────────────────────────────────╯
```

### Option B — Backend API

```bash
$ spawn create
```

```
  1  Backend API
  2  Python Script
  3  Data Science
  4  ML Project

Choose Template [1-4]: 1

  1  fastapi
  2  flask
  3  django

Choose Framework [1-3]: 1

  1  ruff
  2  pytest
  3  docker
  4  github-actions

  Enter numbers separated by commas, or press Enter to skip
Extras []: 1,2

Initialize Git? [Y/n]: y
Initializing Git...
Installing dependencies...

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

## 4. What Gets Created (Backend API / FastAPI)

```
my-api/
├── .git/
├── .gitignore
├── .spawn/
│   └── meta.json
├── .venv/
├── .env.example
├── README.md
├── pyproject.toml
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
└── tests/
    ├── __init__.py
    └── test_health.py
```

| File / Folder | Purpose |
|---|---|
| `app/main.py` | FastAPI app entry point |
| `app/api/routes/health.py` | `GET /` health check route returning `{"status": "running"}` |
| `app/core/config.py` | Pydantic settings with `.env` support |
| `tests/test_health.py` | Health check test using `TestClient` |
| `.env.example` | Documents required environment variables |
| `.spawn/meta.json` | Spawn metadata: intent, framework, version |
| `pyproject.toml` | Project metadata + installed dependencies |
| `.venv/` | Local virtual environment |

## 5. Verify It Works

```bash
spawn version
```

```
Spawn v0.3.0
```

```bash
cd my-api
uv run uvicorn app.main:app --reload
```

Visit `http://localhost:8000/` — should return `{"status": "running"}`.

```bash
uv run pytest
```

```bash
spawn doctor
```

## 6. Next Steps

- Learn all commands → [commands.md](commands.md)
- Understand how Spawn works → [architecture.md](architecture.md)
- See what's changed → [changelog.md](changelog.md)
