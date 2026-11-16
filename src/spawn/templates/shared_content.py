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

# Single source of truth for the Ruff version used everywhere a Ruff pin
# appears: the root project's dev group, generated-project dev dependencies,
# and the pre-commit hook revision. Keeping them derived from one constant
# prevents the local hook, CI, and installed package from drifting apart.
RUFF_VERSION = "0.15.16"
RUFF_PRECOMMIT_REV = f"v{RUFF_VERSION}"

MIT_LICENSE_CONTENT = """MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

CHANGELOG_CONTENT = """# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]
"""

PRECOMMIT_CONFIG_CONTENT = (
    "repos:\n"
    "  - repo: https://github.com/astral-sh/ruff-pre-commit\n"
    f"    rev: {RUFF_PRECOMMIT_REV}\n"
    "    hooks:\n"
    "      - id: ruff\n"
    "      - id: ruff-format\n"
)

RUFF_PYPROJECT_SECTION = "\n[tool.ruff]\nline-length = 88\n"
MYPY_PYPROJECT_SECTION = (
    '\n[tool.mypy]\npython_version = "3.12"\nignore_missing_imports = true\n'
)
PYTEST_PYPROJECT_SECTION = '\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
MYPY_INI_CONTENT = "[mypy]\npython_version = 3.12\nignore_missing_imports = True\n"

AGENTS_MD_FIX_CONTENT = (
    "# Agent Context: {project_name}\n\n"
    "This file orients coding agents working in this repository.\n\n"
    "## Project structure\n\n"
    "See the folder layout in `README.md`.\n\n"
    "## Setup\n\n"
    "```bash\n"
    "{install_cmd}\n"
    "```\n\n"
    "## Running tests\n\n"
    "```bash\n"
    "{test_cmd}\n"
    "```\n"
)

GITHUB_ACTIONS_CI_BASE = """\
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ci:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5

      - name: Install dependencies
        run: uv sync
"""

GITHUB_ACTIONS_CI_RUFF_STEP = """\
      - name: Lint
        run: uv run ruff check .
"""

GITHUB_ACTIONS_CI_PYTEST_STEP = """\
      - name: Test
        run: uv run pytest
"""


def dev_dependency_extras(extras: list[str]) -> list[str]:
    """Return the common dev tools (ruff, mypy, pre-commit) for *extras*.

    These are the dev tools every project type shares. Framework-specific
    dev tools such as ``pytest`` (and its companions ``httpx`` or
    ``pytest-django``) are added by each template's ``get_dev_dependencies()``
    so that testing helpers stay out of the runtime dependency list.

    Ruff is pinned to ``RUFF_VERSION`` so that the installed package, the
    pre-commit hook revision, and the root project all agree on a version.
    """
    dev: list[str] = []
    if "ruff" in extras:
        dev.append(f"ruff>={RUFF_VERSION}")
    if "mypy" in extras:
        dev.append("mypy")
    if "pre-commit" in extras:
        dev.append("pre-commit")
    return dev
