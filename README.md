# Spawn 

> Eliminate repetitive project setup. Go from zero to a fully structured dev environment in seconds.

Spawn is a local CLI tool that automates the tedious parts of starting a new Python project — creating directories, writing boilerplate files, initializing Git, and setting up a `uv` virtual environment — all through a clean, interactive terminal interface.

---

## Why Spawn?

Every new project starts the same way: create folders, add a README, set up `.gitignore`, init Git, create a virtual environment... It's repetitive, error-prone, and inconsistent across projects.

Spawn collapses all of that into a single command.

---

## Features

- **Interactive CLI** — guided prompts walk you through project setup step by step
- **4 built-in templates** — Python Script, FastAPI, Data Science, ML Project
- **Auto Git init** — optionally run `git init` on project creation
- **Auto `uv` init** — automatically runs `uv init --bare` and `uv venv` for clean environment management
- **Boilerplate generation** — `README.md` and `.gitignore` created automatically
- **Fast** — entire setup completes in under 30 seconds

---

## Tech Stack

| Tool | Role |
|---|---|
| Python 3.12+ | Core language |
| [Typer](https://typer.tiangolo.com/) | CLI framework |
| [Rich](https://rich.readthedocs.io/) | Terminal UI |
| [uv](https://github.com/astral-sh/uv) | Python environment management |
| Git | Version control initialization |

---

## Installation

**Prerequisites:** Python 3.12+, `uv`, and `git` installed and available on your PATH.

```bash
# Clone the repo
git clone https://github.com/your-username/spawn.git
cd spawn

# Install with uv
uv sync

# Or install via pip
pip install .
```

---

## Usage

### Create a new project

```bash
spawn create
```

You'll be walked through three prompts:

```
Project Name: my-cool-project

Available Templates:
 [1] python
 [2] fastapi
 [3] data-science
 [4] ml

Choose template: 2
Initialize Git? [Y/n]: Y
```

Spawn will then:
1. Create the project directory with the template's folder structure
2. Generate `README.md` and `.gitignore`
3. Run `git init` (if selected)
4. Run `uv init --bare` and `uv venv`

### Check version

```bash
spawn version
```

---

## Project Templates

### `[1] python` — Python Script

```
my-project/
├── README.md
├── .gitignore
├── src/
└── tests/
```

### `[2] fastapi` — FastAPI App

```
my-project/
├── README.md
├── .gitignore
├── app/
├── src/
├── tests/
└── docs/
```

### `[3] data-science` — Data Science Project

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

### `[4] ml` — ML Project

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

---

## Project Structure

```
spawn/
├── src/
│   └── spawn/
│       ├── cli/
│       │   ├── app.py          # Typer app & command definitions
│       │   └── prompts.py      # Interactive prompts logic
│       ├── core/
│       │   ├── models.py       # ProjectConfig dataclass
│       │   └── registry.py     # Template registry / lookup
│       ├── generators/
│       │   └── project_generator.py  # Orchestrates project creation
│       ├── templates/
│       │   ├── base.py         # BaseTemplate dataclass
│       │   ├── files.py        # README & .gitignore content
│       │   ├── python_script.py
│       │   ├── fastapi.py
│       │   ├── data_science.py
│       │   └── ml_project.py
│       └── utils/
│           ├── git.py          # git init wrapper
│           └── uv.py           # uv init + uv venv wrappers
├── tests/
├── pyproject.toml
└── README.md
```

---

## V1 Scope

**Included:**
- Interactive CLI
- 4 project templates
- Git initialization
- `uv` environment initialization
- `README.md` and `.gitignore` generation

**Not included in V1:**
- GitHub repository creation
- Dockerfile generation
- Makefile generation
- CI/CD setup
- Automatic package installation

---

## Roadmap (V2)

- GitHub API integration — create and push to remote repos automatically
- Project templates marketplace — community-contributed templates
- Docker support — generate `Dockerfile` and `docker-compose.yml`
- Makefile support
- Starter dependency packs — install common deps per template
- Config file support — save your preferences for faster reuse

---

## Contributing

Contributions are welcome! The template architecture is designed to be easily extensible — adding a new template is as simple as:

1. Create a new file in `src/spawn/templates/`
2. Subclass `BaseTemplate` with your `name` and `folders`
3. Register it in `src/spawn/core/registry.py`

---
