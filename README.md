<div align="center">

# 🦋 Spawn

> Eliminate repetitive project setup. Go from zero to a fully structured dev environment in seconds.

Spawn is a local CLI tool that transforms one command into a complete Python project foundation — directories, Git, dependencies, and a virtual environment set up automatically, so you can start building immediately.

[![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square)](https://github.com/Abhiix0/spawn/actions)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![uv](https://img.shields.io/badge/Powered%20by-uv-orange?style=flat-square)](https://github.com/astral-sh/uv)

</div>

---

## The Problem Spawn Solves

Every new Python project starts with the same manual ritual:

```bash
mkdir my-project
cd my-project
mkdir src tests docs
touch README.md .gitignore
git init
python -m venv .venv
source .venv/bin/activate
...
```

It's repetitive. It's error-prone. It's inconsistent. And you haven't written a single line of *real* code yet.

**Spawn collapses all of that into one command: `spawn create`**

---

## Features at a Glance

| Feature | What it does |
|---|---|
| **Interactive CLI** | Prompt-driven setup powered by [Rich](https://github.com/Textualize/rich) |
| **Intent-based templates** | Backend API (FastAPI / Flask / Django), Python Script, Data Science, ML Project |
| **Framework selection** | Choose your framework at creation time — no post-setup reconfiguring |
| **Extras system** | Opt-in ruff, pytest, Docker, GitHub Actions — installed and configured automatically |
| **Dependency installation** | `uv add` runs automatically with the right packages for your choices |
| **Git integration** | Optionally runs `git init` and publishes to GitHub |
| **uv integration** | Runs `uv init` and `uv venv` for you |
| **Smart next steps** | Shows the exact commands to run after setup |
| **GitHub publishing** | Connects your project to an existing GitHub repo and pushes the initial commit |
| **spawn doctor** | Scans your project directory for health indicators and scores it out of 100 |

---

## Prerequisites

Before using Spawn, make sure you have these installed:

- **Python 3.12+** — [Download here](https://python.org/downloads)
- **uv** — A fast Python package manager. [Install guide](https://github.com/astral-sh/uv)
- **Git** — [Download here](https://git-scm.com/downloads)

> **First time with uv?** Run `pip install uv` or check their [quickstart](https://github.com/astral-sh/uv#getting-started).

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Abhiix0/spawn.git

# 2. Navigate into the project folder
cd spawn

# 3. Install dependencies
uv sync

# 4. Install Spawn as a global tool
uv tool install .
```

That's it. You can now run `spawn` from anywhere on your machine.

---

## Usage

### Create a new project

```bash
spawn create
```

Spawn guides you through an interactive prompt. The flow depends on which template you choose.

#### Python Script, Data Science, ML Project

```
Project Name: my-script

  1  Backend API
  2  Python Script
  3  Data Science
  4  ML Project

Choose Template [1-4]: 2
Initialize Git? [Y/n]: Y
```

#### Backend API

Selecting Backend API adds two extra steps — framework and extras:

```
Project Name: my-api

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

Initialize Git? [Y/n]: Y
```

When it's done, you'll see a clean summary and exactly what to do next:

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

### Check your version

```bash
spawn version
# → Spawn v0.3.0
```

---

### Publish to GitHub

After project creation, if Git was enabled, Spawn will ask:

```
Publish to GitHub? [y/N]:
```

Paste your existing empty GitHub repository URL:

```
Repository URL: https://github.com/your-username/my-project
```

Spawn will automatically:
- Stage all files (`git add .`)
- Create the initial commit
- Set the branch to `main`
- Add the remote origin
- Push to GitHub

```
🚀 Published successfully!
```

> The repository must already exist on GitHub. Spawn connects to it — it does not create it.

---

## Project Templates

### `[1]` Backend API — Production-ready backend

Best for: REST APIs, microservices, backend web apps.

Choose a framework at creation time:

| Framework | Run command |
|---|---|
| FastAPI | `uv run uvicorn app.main:app --reload` |
| Flask | `uv run python run.py` |
| Django | `uv run python manage.py runserver` |

Optional extras: `ruff`, `pytest`, `docker`, `github-actions`

All selected extras are installed automatically via `uv add`. No manual setup required.

**FastAPI structure:**

```
my-api/
├── app/
│   ├── api/routes/health.py
│   ├── core/config.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── main.py
├── tests/
│   └── test_health.py
├── .env.example
├── README.md
└── .gitignore
```

The health endpoint is ready immediately:

```bash
uv run uvicorn app.main:app --reload
# → GET http://localhost:8000/ returns {"status": "running"}
```

---

### `[2]` Python Script — General purpose scripting

Best for: automation scripts, utilities, one-off tools.

```
my-project/
├── main.py
├── README.md
├── .gitignore
├── src/
└── tests/
```

**Next step:** `uv run python main.py`

---

### `[3]` Data Science — Data analysis and visualization

Best for: exploratory data analysis, reporting, Jupyter notebooks.

```
my-project/
├── main.py
├── README.md
├── .gitignore
├── data/
├── notebooks/
├── src/
├── docs/
└── tests/
```

**Next steps:**

```bash
uv add pandas numpy matplotlib
uv run python main.py
```

---

### `[4]` ML Project — Machine learning pipelines

Best for: model training, feature engineering, experiments.

```
my-project/
├── main.py
├── README.md
├── .gitignore
├── data/
├── models/
├── src/
├── docs/
└── tests/
```

**Next steps:**

```bash
uv add pandas numpy scikit-learn
uv run python main.py
```

---

## spawn doctor

```bash
spawn doctor
```

`spawn doctor` scans your current project directory and checks for essential project health indicators — documentation, version control, test setup, linting, deployment config, and more. Each check is weighted and tallied into a score out of 100.

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
│  ✓ .env.example — Environment template present          │
│                                                          │
│  Project Score: 80/100 (80%)                            │
╰──────────────────────────────────────────────────────────╯
```

---

## Examples

```bash
# FastAPI backend with ruff and pytest
spawn create
# → name: api-server, template: 1 (Backend API), framework: 1 (FastAPI)
# → extras: 1,2 (ruff, pytest), git: Y

# Simple Python script, no Git
spawn create
# → name: my-tool, template: 2 (Python Script), git: N

# Data science workspace
spawn create
# → name: analysis, template: 3 (Data Science), git: N
```

---

## Running the Tests

```bash
uv run pytest
```

All tests should pass. If they don't, please [open an issue](https://github.com/Abhiix0/spawn/issues).

---

## Roadmap

- [x] **GitHub publishing** — connect and push to an existing GitHub repo (v0.2.0)
- [x] **Backend API intent** — FastAPI, Flask, Django with production structure (v0.3.0)
- [x] **Extras system** — ruff, pytest, Docker, GitHub Actions installed automatically (v0.3.0)
- [x] **Dependency installation** — `uv add` runs automatically after generation (v0.3.0)
- [ ] **CLI Application intent** — Typer-based CLI scaffold (v0.4.0)
- [ ] **Automation Tool intent** — scripting and scheduling scaffold (v0.5.0)
- [ ] **AI Chatbot intent** — LLM-integrated chat app scaffold (v0.6.0)
- [ ] **AI Agent intent** — tool-calling agent scaffold (v0.7.0)
- [ ] **RAG System intent** — retrieval-augmented generation scaffold (v0.8.0)
- [ ] **Data Project intent** — analysis, dashboard, ETL, ML sub-options (v0.9.0)

---

## Contributing

Contributions are welcome! Whether it's a bug fix, a new template, or a feature from the roadmap — here's how to get started.

### Adding a new intent (3 steps)

**1. Create the intent directory**

```
src/spawn/templates/your_intent/
├── __init__.py    ← template class, subclass BaseTemplate
└── content.py     ← all file content as string constants
```

**2. Register it**

`src/spawn/core/registry.py` — add a `TemplateMetadata` entry to the `TEMPLATES` dict with your slug, display name, description, template class, and any `available_frameworks` or `available_extras`.

**3. Write tests**

```
tests/test_templates.py
tests/test_generator.py
```

Cover template instantiation, generated structure, and dependency list. Mock `initialize_uv` and `install_packages` in generator tests.

### Before submitting a PR

```bash
uv run pytest        # all tests must pass
uv run ruff check .  # must be clean
```

Not sure where to start? Check the [open issues](https://github.com/Abhiix0/spawn/issues) or pick something from the roadmap above.

---

## License

This project is open source under the [MIT License](LICENSE).

---

<div align="center">

**[⭐ Star on GitHub](https://github.com/Abhiix0/spawn)** · **[🐛 Report a Bug](https://github.com/Abhiix0/spawn/issues)** · **[💡 Request a Feature](https://github.com/Abhiix0/spawn/issues)**

</div>
