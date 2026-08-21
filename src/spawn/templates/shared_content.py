README_CONTENT = """# {project_name}

Project generated with Spawn.
"""

GITIGNORE_CONTENT = """# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.pyc

# Virtual environments
.venv/
venv/
env/

# Distribution / packaging
dist/
build/
*.egg-info/
*.egg

# uv
.uv/

# Environment variables
.env
.env.*

# IDEs
.vscode/
.idea/
*.iml

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Mypy
.mypy_cache/

# Ruff
.ruff_cache/

# Spawn metadata
.spawn/

# Logs
logs/*.log

# ChromaDB vector store (regenerate with: delete chroma_db/ and re-run)
chroma_db/
!chroma_db/.gitkeep
"""

AGENTS_MD_CONTENT = """# Agent Context: {project_name}

This file orients coding agents (Claude Code, and others that read
`AGENTS.md`) working in this repository.

## Project structure

See the folder layout in `README.md`. This project was generated
with Spawn.

## Setup

```bash
uv sync
```

## Running tests

```bash
uv run pytest
```

## Conventions

- Dependencies are managed with uv, not pip directly.
- Run `uv run ruff check .` before committing, if Ruff is configured
  for this project (see `pyproject.toml`).
"""
