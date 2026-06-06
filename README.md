<div align="center">

#  Spawn

**Stop repeating yourself. Start building.**

Spawn is a local CLI tool that sets up a complete Python project structure in seconds — directories, boilerplate files, Git initialization, and a virtual environment — all from a single command with a beautiful interactive prompt.

[![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen?style=flat-square)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![uv](https://img.shields.io/badge/Powered%20by-uv-orange?style=flat-square)](https://github.com/astral-sh/uv)

![Spawn Preview](assets/preview.png)

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

**Spawn collapses all of that into one command: `spawn create`**

---

## Features at a Glance

| Feature | What it does |
|---|---|
|  **Interactive CLI** | Beautiful prompt-driven setup powered by [Rich](https://github.com/Textualize/rich) |
|  **4 Project Templates** | Python Script, FastAPI, Data Science, ML Project |
|  **Git Integration** | Optionally runs `git init` automatically |
|  **uv Integration** | Runs `uv init --bare` and `uv venv` for you |
|  **Smart Next Steps** | Shows the exact commands to run after setup |
|  **Error Handling** | Clear, readable messages if Git or uv aren't found |

---

## Prerequisites

Before using Spawn, make sure you have these installed:

- **Python 3.12+** — [Download here](https://python.org/downloads)
- **uv** — A fast Python package manager. [Install guide](https://github.com/astral-sh/uv)
- **Git** — [Download here](https://git-scm.com/downloads)

> **First time with uv?** Run `pip install uv` or check their [quickstart](https://github.com/astral-sh/uv#getting-started). It's a faster alternative to pip and venv combined.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Abhiix0/Spawn.git

# 2. Navigate into the project folder
cd Spawn

# 3. Install dependencies
uv sync

# 4. Install Spawn as a global tool
uv tool install .
```

That's it! You can now run `spawn` from anywhere on your machine.

---

## Usage

### Create a new project

```bash
spawn create
```

Spawn will guide you through an interactive prompt:

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

When it's done, you'll see a clean summary and exactly what to do next:

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

### Check your version

```bash
spawn version
# → Spawn v0.1.0
```

---

## Project Templates

Choose the template that matches your use case. Each one creates the right folder structure and tells you which packages to install next.

### `[1]` Python Script — General purpose scripting

Best for: automation scripts, utilities, one-off tools.

```
my-project/
├── README.md
├── .gitignore
├── src/
└── tests/
```

**Next step:** `uv run python main.py`

---

### `[2]` FastAPI — Web APIs and backends

Best for: REST APIs, microservices, backend web apps.

```
my-project/
├── README.md
├── .gitignore
├── app/
├── src/
├── tests/
└── docs/
```

**Next steps:**
```bash
uv add fastapi uvicorn
uv run uvicorn app.main:app --reload
```

---

### `[3]` Data Science — Data analysis and visualization

Best for: exploratory data analysis, reporting, Jupyter notebooks.

```
my-project/
├── README.md
├── .gitignore
├── data/
├── notebooks/
├── src/
├── docs/
└── tests/
```

**Next step:** `uv add pandas numpy matplotlib`

---

### `[4]` ML Project — Machine learning pipelines

Best for: model training, feature engineering, experiments.

```
my-project/
├── README.md
├── .gitignore
├── data/
├── models/
├── src/
├── docs/
└── tests/
```

**Next step:** `uv add pandas numpy scikit-learn`

---

## Examples

```bash
# Spin up a FastAPI project with Git
spawn create
# → name: api-server, template: 2, git: Y

# Create a data science workspace without Git
spawn create
# → name: analysis, template: 3, git: N
```

---

## Running the Tests

Want to verify everything works after cloning?

```bash
uv run pytest
```

All tests should pass. If they don't, please [open an issue](https://github.com/Abhiix0/Spawn/issues).

---

---

## Roadmap

Here's what's planned next. Contributions welcome on any of these!

- [ ] **GitHub API integration** — create and push to a remote repo automatically
- [ ] **Project templates marketplace** — community-contributed templates
- [ ] **Docker support** — generate `Dockerfile` and `docker-compose.yml`
- [ ] **Makefile support** — common task automation out of the box
- [ ] **Starter dependency packs** — auto-install common packages per template
- [ ] **Config file support** — save your preferences for even faster reuse

---

## Contributing

Contributions are welcome! Whether it's a bug fix, a new template, or a feature from the roadmap — here's how to get started.

### Adding a new template (3 steps)

1. **Create the template file**
   ```
   src/spawn/templates/your_template.py
   ```
   Subclass `BaseTemplate` and define the folder structure.

2. **Register it**
   ```
   src/spawn/core/registry.py
   ```
   Add your template to the registry so Spawn can find it.

3. **Add next steps**
   ```
   src/spawn/utils/next_steps.py
   ```
   Tell users what to do after the project is created.

### Before submitting a PR

```bash
# Make sure all tests pass
uv run pytest
```

Not sure where to start? Check the [open issues](https://github.com/Abhiix0/Spawn/issues) or pick something from the roadmap above.

---

## License

This project is open source under the [MIT License](LICENSE). Use it, fork it, build on it.

---

<div align="center">

**[⭐ Star on GitHub](https://github.com/Abhiix0/Spawn)** · **[🐛 Report a Bug](https://github.com/Abhiix0/Spawn/issues)** · **[💡 Request a Feature](https://github.com/Abhiix0/Spawn/issues)**

</div>