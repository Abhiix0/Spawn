# Spawn
> Eliminate repetitive project setup. Go from zero to a fully structured dev environment in seconds.

Spawn is a local CLI tool that automates the tedious parts of starting a new Python project — creating directories, writing boilerplate files, initializing Git, and setting up a `uv` virtual environment — all through a clean, interactive terminal interface.

---

## Why Spawn?

Every new project starts the same way: create folders, add a README, set up `.gitignore`, init Git, create a virtual environment... It's repetitive, error-prone, and inconsistent across projects.

Spawn collapses all of that into a single command.

---

## Features

- **Interactive CLI** — beautiful prompt-driven setup powered by Rich
- **4 project templates** — Python Script, FastAPI, Data Science, ML Project
- **Git integration** — optionally runs `git init` on project creation
- **uv integration** — automatically runs `uv init --bare` and `uv venv`
- **Smart next steps** — shows template-specific commands to get coding immediately
- **Error handling** — clean, readable error messages when Git or uv aren't found

---

## Quick Start

**Prerequisites:** Python 3.12+, [`uv`](https://github.com/astral-sh/uv), and `git` on your PATH.

```bash
git clone https://github.com/Abhiix0/Spawn.git
cd Spawn

uv sync
uv tool install .

spawn create
```
---

## Usage

### Create a project

```bash
spawn create
```

You'll see an interactive prompt:

```
╭─────────────────────────────────────────────╮
│                 🚀 Spawn                   │
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

On completion, Spawn shows a summary and your next steps:

```
╭─────── ✨ Project Created Successfully ───────╮
│  Project     my-project                       │
│  Template    FastAPI                          │
│  Git         ✓ Enabled                        │
│  UV          ✓ Initialized                    │
│  Virtual Env ✓ Created                        │
╰───────────────────────────────────────────────╯

🚀 Next Steps
╭───────────────────────────────────╮
│  cd my-project                    │
│  uv add fastapi uvicorn           │
│  uv run uvicorn app.main:app --reload │
╰───────────────────────────────────╯
```

### Check version

```bash
spawn version
```

---

## Templates

### `[1]` Python Script
```
my-project/
├── README.md
├── .gitignore
├── src/
└── tests/
```
Next steps: `uv run python main.py`

---

### `[2]` FastAPI
```
my-project/
├── README.md
├── .gitignore
├── app/
├── src/
├── tests/
└── docs/
```
Next steps: `uv add fastapi uvicorn` → `uv run uvicorn app.main:app --reload`

---

### `[3]` Data Science
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
Next steps: `uv add pandas numpy matplotlib`

---

### `[4]` ML Project
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
Next steps: `uv add pandas numpy scikit-learn`

---

## Examples

```bash
# Spin up a FastAPI project with Git
spawn create
# → name: api-server, template: 2, git: Y

# Spin up a data science project without Git
spawn create
# → name: analysis, template: 3, git: N

# Check installed version
spawn version
# → Spawn v0.1.0
```
## 📸 Preview

![Spawn Preview](assets/preview.png)
---

## Roadmap

- GitHub API integration — create and push to a remote repo automatically
- Project templates marketplace — community-contributed templates
- Docker support — generate `Dockerfile` and `docker-compose.yml`
- Makefile support
- Starter dependency packs — install common deps per template automatically
- Config file support — save preferences for even faster reuse

---

## Contributing

Adding a new template takes 3 steps:

1. Create `src/spawn/templates/your_template.py` and subclass `BaseTemplate`
2. Register it in `src/spawn/core/registry.py`
3. Add its next steps to `src/spawn/utils/next_steps.py`

Run tests before submitting:

```bash
uv run pytest
```

---

## License

This project is open source. See [LICENSE](LICENSE) for details.
