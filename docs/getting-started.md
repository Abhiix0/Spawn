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

```bash
$ spawn create
╭─────────────────────────────────────────────╮
│ 🚀 Spawn                                    │
│ Create development environments in seconds  │
╰─────────────────────────────────────────────╯

Project Name: my-api

      Available Templates
┏━━━┳━━━━━━━━━━━━━━━┓
┃ # ┃ Template      ┃
┡━━━╇━━━━━━━━━━━━━━━┩
│ 1 │ Python Script │
│ 2 │ FastAPI       │
│ 3 │ Data Science  │
│ 4 │ ML Project    │
└───┴───────────────┘

Choose Template [1-4]: 2
Initialize Git? [Y/n]: y
Initializing Git...

╭────── ✨ Project Created Successfully ──────╮
│                                              │
│  Project      my-api                         │
│  Template     FastAPI                        │
│  Git          ✓ Enabled                      │
│  UV           ✓ Initialized                  │
│  Virtual Env  ✓ Created                      │
│                                              │
│  Next Steps                                  │
│    cd my-api                                 │
│    uv add fastapi uvicorn                    │
│    uv run uvicorn app.main:app --reload      │
│                                              │
╰──────────────────────────────────────────────╯

Publish to GitHub? [y/N]: n
```

## 4. What Got Created

```
my-api/
├── .git/
├── .gitignore
├── .venv/
├── README.md
├── app/
│   └── main.py
├── docs/
├── pyproject.toml
├── src/
└── tests/
```

| File / Folder | Purpose |
|---|---|
| `app/main.py` | Starter FastAPI app with a `/` route |
| `src/` | Application source code |
| `tests/` | Test files |
| `docs/` | Project documentation |
| `README.md` | Project overview |
| `.gitignore` | Ignores venv, caches, and build artifacts |
| `pyproject.toml` | Project metadata (created by `uv init --bare`) |
| `.venv/` | Local virtual environment (created by `uv venv`) |
| `.git/` | Git repository (created because Git was enabled) |

## 5. Verify It Works

```bash
spawn version
```

```
Spawn v0.2.0
```

```bash
cd my-api
spawn doctor
```

```
╭────────────── 🏥 Project Health Report ──────────────╮
│                                                       │
│  Documentation                                        │
│  ✓ README.md — Documentation file present           │
│  ⚠ LICENSE — Missing LICENSE file                     │
│                                                       │
│  Version Control                                      │
│  ✓ Git Repository — Git initialized                   │
│  ✓ .gitignore — Git ignore configured                 │
│                                                       │
│  Quality                                              │
│  ✓ Tests — Test directory configured                  │
│  ⚠ Ruff — Ruff not configured                         │
│  ⚠ Pytest — Pytest not configured                     │
│                                                       │
│  Deployment                                           │
│  ⚠ Dockerfile — Missing Dockerfile                  │
│  ⚠ GitHub Actions — GitHub Actions not configured     │
│                                                       │
│  Configuration                                        │
│  ⚠ .env.example — Missing .env.example                │
│                                                       │
│  Project Score: 50/100 (50%)                          │
╰───────────────────────────────────────────────────────╯
```

## 6. Next Steps

- Learn all commands → [commands.md](commands.md)
- Understand how Spawn works → [architecture.md](architecture.md)
- See what's changed → [changelog.md](changelog.md)
