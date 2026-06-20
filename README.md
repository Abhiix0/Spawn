<div align="center">

# Spawn

> Eliminate repetitive project setup. Go from zero to a fully structured dev environment in seconds.

[![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![uv](https://img.shields.io/badge/Powered%20by-uv-orange?style=flat-square)](https://github.com/astral-sh/uv)

</div>

---

## The Problem Spawn Solves

Every new Python project starts with the same manual ritual:

```
mkdir my-project
cd my-project
mkdir src tests docs
touch README.md .gitignore
git init
python -m venv .venv
source .venv/bin/activate
...
```

It's repetitive. It's error-prone. It's inconsistent. And you haven't even written a single line of *real* code yet.

```bash
spawn create
```

That's it. You pick the template. Spawn handles the rest.

---

## Who It's For

- **New to Python?** Stop spending your first hour on setup. Start writing code.
- **Seasoned dev?** You know how tedious this is. You don't have to do it anymore.
- **Building something serious?** Spawn's structure keeps your projects consistent from day one.

---

## Get Started

Before using Spawn, make sure you have these installed:

- **Python 3.12+** — [Download here](https://python.org/downloads)
- **uv** — A fast Python package manager. [Install guide](https://github.com/astral-sh/uv)
- **Git** — [Download here](https://git-scm.com/downloads)

> **First time with uv?** Run `pip install uv` or check their [quickstart](https://github.com/astral-sh/uv#getting-started). It's a faster alternative to pip and venv combined.

```bash
git clone https://github.com/Abhiix0/Spawn.git
cd Spawn
uv sync
uv tool install .
```

You can now run `spawn` from anywhere on your machine.

---

## Commands

### `spawn create` — Start a new project

Spawn walks you through an interactive prompt:

```
╭─────────────────────────────────────────────╮
│                    Spawn                    │
│  Create development environments in seconds │
╰─────────────────────────────────────────────╯

Project Name: my-project

  #  Template
  1  Python Script
  2  FastAPI
  3  Data Science
  4  ML Project

Choose Template [1-4]: 2

Initialize Git? [Y/n]: Y
```

When it's done, you get a clean summary and exactly what to run next:

```
╭───────    Project Created Successfully ───────╮
│  Project     my-project                       │
│  Template    FastAPI                          │
│  Git         ✓ Enabled                        │
│  UV          ✓ Initialized                    │
│  Virtual Env ✓ Created                        │
╰───────────────────────────────────────────────╯

 Next Steps
╭───────────────────────────────────────────────────╮
│  cd my-project                                    │
│  uv add fastapi uvicorn                           │
│  uv run uvicorn app.main:app --reload             │
╰───────────────────────────────────────────────────╯
```

**4 templates to choose from:**

| # | Template | Best for |
|---|---|---|
| 1 | Python Script | Automation scripts, utilities, one-off tools |
| 2 | FastAPI | REST APIs, microservices, backend web apps |
| 3 | Data Science | EDA, reporting, Jupyter notebooks |
| 4 | ML Project | Model training, feature engineering, experiments |

---

### `spawn doctor` — Check your project's health

Run it inside any project — not just ones Spawn created. It scans for the things that actually matter and scores everything out of 100.

```
╭─────────────── 🏥 Project Health Report ───────────────╮
│                                                          │
│  Documentation                                           │
│  ✓ README.md — Documentation file present               │
│  ⚠ LICENSE — Missing LICENSE file                       │
│                                                          │
│  Version Control                                         │
│  ✓ Git Repository — Git initialized                     │
│  ✓ .gitignore — Git ignore configured                   │
│                                                          │
│  Quality                                                 │
│  ✓ Tests — Test directory configured                    │
│  ✓ Ruff — Ruff configured in pyproject.toml             │
│  ✓ Pytest — Pytest configured in pyproject.toml         │
│                                                          │
│  Deployment                                              │
│  ⚠ Dockerfile — Missing Dockerfile                      │
│  ✓ GitHub Actions — GitHub Actions configured           │
│                                                          │
│  Configuration                                           │
│  ⚠ .env.example — Missing .env.example                  │
│                                                          │
│  Project Score: 70/100 (70%)                            │
╰──────────────────────────────────────────────────────────╯
```

You'll know exactly where your project stands and what it's missing — without digging through folders yourself.

---

### `spawn publish` — Push to GitHub

After project creation, if Git was enabled, Spawn will ask:

```
Publish to GitHub? [y/N]:
```

Paste your existing empty GitHub repository URL and Spawn handles the rest — stages all files, creates the initial commit, sets the branch to `main`, adds the remote, and pushes.

```
🚀 Published successfully!
```

> The repository must already exist on GitHub. Spawn connects to it — it does not create it.

---

### `spawn version` — Check your version

```bash
spawn version
# → Spawn v0.2.0
```

---

## What's Coming

- [x] **GitHub publishing** — connect and push to an existing GitHub repo
- [ ] **Project templates marketplace** — community-contributed templates
- [ ] **Docker support** — generate `Dockerfile` and `docker-compose.yml`
- [ ] **Makefile support** — common task automation out of the box
- [ ] **Starter dependency packs** — auto-install common packages per template
- [ ] **Config file support** — save your preferences for even faster reuse

---

## Contributing

Every great tool gets better with the people who use it. If something bugs you, something's missing, or you have an idea — you're in the right place.

Adding a new template is a good first contribution and easier than it looks:

1. **Create the template** in `src/spawn/templates/your_template.py`.
   Subclass `BaseTemplate` and define the folder structure.
2. **Register it** in `src/spawn/core/registry.py`.
   Add your template to the registry so Spawn can find it.
3. **Add next steps** in `src/spawn/utils/next_steps.py`.
   Tell users what to do after the project is created.

Before submitting a PR, make sure all tests pass:

```bash
uv run pytest
```

Not sure where to start? Check the [open issues](https://github.com/Abhiix0/Spawn/issues).

---

[![MIT License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE) — use it, fork it, build on it.
