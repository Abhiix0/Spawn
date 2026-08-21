# Command Reference

## Overview

| Command | Description |
|---|---|
| `spawn` | Show the banner, version, and command list |
| `spawn create` | Scaffold a new project (interactive or non-interactive) |
| `spawn doctor` | Score a project directory's health out of 135 |
| `spawn version` | Print the installed version |

---

## `spawn` (no arguments)

Running `spawn` with no arguments prints the banner, the installed version, and the command list.

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

## `spawn create`

Creates a new project directory, writes starter files, installs dependencies, and optionally runs `git init` and `uv init`.

### Interactive mode

Run with no flags to enter the arrow-key prompt flow:

```bash
spawn create
```

**Prompt sequence**

| Step | Prompt | When shown |
|---|---|---|
| 1 | `Project Name` | Always |
| 2 | `Choose a template` | Always |
| 3 | `Choose CLI Type` | CLI Application only |
| 4 | `Choose Project Type` | Data Project only |
| 5 | `Choose Framework` | Backend API, CLI Application, AI Chatbot, AI Agent |
| 6 | `Choose Provider` | AI Chatbot, AI Agent (filtered by framework) |
| 7 | `Select extras` | Templates with available extras |
| 8 | `Initialize Git? [Y/n]` | Always |
| 9 | `Also generate CLAUDE.md for Claude Code? [y/N]` | Always |
| 10 | `Publish to GitHub? [y/N]` | Only when Git was enabled and not in non-interactive mode |

Every menu (steps 2–7) is **arrow-key / spacebar** driven — no typed numbers.

**Template list**

```
? Choose a template (Use arrow keys)
 » Backend API
   CLI Application
   Automation Tool
   AI Chatbot
   AI Agent
   RAG System
   Data Project
   MCP Server
   Custom Structure
```

**Extras selection (checkbox)**

```
? Select extras (space to toggle, enter to confirm)
 ● ruff
 ● pytest
 ○ docker
 ○ github-actions
```

Space toggles, Enter confirms. Empty selection is valid (skip all extras).

**Project Name validation**

| Rule | Detail |
|---|---|
| Allowed characters | Letters, numbers, hyphens (`-`), underscores (`_`) |
| Required | At least one letter or digit |
| Rejected examples | `my project` (space), `my/project` (slash), `---` (no alphanumeric) |

---

### Non-interactive mode

Pass `--name` to skip all prompts. `--template` is required when using `--name`.

```bash
spawn create --name my-api --template backend-api --framework fastapi --extras ruff,pytest
```

Pass `--config` to read settings from a JSON file instead of flags:

```bash
spawn create --config spawn.json
```

`--config` takes precedence over individual flags. The JSON file may contain:

```json
{
  "name": "my-api",
  "template": "backend-api",
  "framework": "fastapi",
  "provider": null,
  "cli_type": null,
  "data_type": null,
  "extras": ["ruff", "pytest"],
  "git": true,
  "uv": true,
  "claude_md": false
}
```

**All `spawn create` flags**

| Flag | Default | Description |
|---|---|---|
| `--name` | — | Project name. Setting this enables non-interactive mode. |
| `--template` | — | Template slug (see table below). Required with `--name`. |
| `--framework` | first available | Framework for templates that support it |
| `--provider` | first available | AI provider for chatbot/agent templates |
| `--cli-type` | `utility` | `utility` or `interactive` (CLI Application only) |
| `--data-type` | `Data Analysis` | Sub-type for Data Project |
| `--extras` | none | Comma-separated extras, e.g. `ruff,pytest` |
| `--git` / `--no-git` | `--git` | Initialize a Git repository |
| `--uv` / `--no-uv` | `--uv` | Initialize uv and install dependencies |
| `--claude-md` / `--no-claude-md` | `--no-claude-md` | Also write `CLAUDE.md` alongside `AGENTS.md` |
| `--config` | — | Path to a JSON config file |
| `--yes` / `-y` | false | Skip the GitHub publish prompt |
| `--dry-run` | false | Validate and print the config without creating anything |

**Template slugs**

| Slug | Display name | Frameworks | Providers | CLI types | Project types | Extras |
|---|---|---|---|---|---|---|
| `backend-api` | Backend API | fastapi, flask, django | — | — | — | ruff, pytest, docker, github-actions |
| `cli` | CLI Application | typer, click, argparse | — | utility, interactive | — | ruff, pytest, github-actions |
| `automation` | Automation Tool | — | — | — | — | ruff, pytest, github-actions |
| `chatbot` | AI Chatbot | pydantic-ai, openai-sdk, litellm | openai, anthropic, gemini, openrouter, ollama, groq | — | — | ruff, pytest, rich, github-actions |
| `agent` | AI Agent | pydantic-ai, openai-agents | openai, anthropic, gemini, openrouter, ollama, groq | — | — | ruff, pytest, github-actions |
| `rag` | RAG System | — | — | — | — | ruff, pytest, github-actions |
| `data` | Data Project | — | — | — | Data Analysis, Dashboard, ETL Pipeline, Machine Learning | ruff, pytest, github-actions |
| `mcp` | MCP Server | — | — | — | — | ruff, pytest, github-actions |

> `openai-agents` only supports `openai` and `openrouter` as providers — the list is filtered per framework.

> Custom Structure is interactive-only. It is not available via `--template`.

---

### Per-template prompt flows

#### Backend API

```
? Choose a framework (Use arrow keys)
 » fastapi
   flask
   django

? Select extras (space to toggle, enter to confirm)
 ○ ruff
 ○ pytest
 ○ docker
 ○ github-actions
```

| Framework | Run command |
|---|---|
| fastapi | `uv run uvicorn app.main:app --reload` |
| flask | `uv run python run.py` |
| django | `uv run python manage.py runserver` |

---

#### CLI Application

```
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
```

| CLI type | Run command |
|---|---|
| utility | `uv run python -m src.main hello` |
| interactive | `uv run python -m src.main greet` |

---

#### Automation Tool

```
? Select extras (space to toggle, enter to confirm)
 ○ ruff
 ○ pytest
 ○ github-actions
```

Run: `uv run python -m src.main`

---

#### AI Chatbot

```
? Choose a framework (Use arrow keys)
 » pydantic-ai
   openai-sdk
   litellm

? Choose a provider (Use arrow keys)
 » openai
   anthropic
   gemini
   openrouter
   ollama
   groq

? Select extras (space to toggle, enter to confirm)
 ○ ruff
 ○ pytest
 ○ rich
 ○ github-actions
```

Run: add provider API key to `.env`, then `uv run python -m src.main`

---

#### AI Agent

```
? Choose a framework (Use arrow keys)
 » pydantic-ai
   openai-agents

? Choose a provider (Use arrow keys)
 » openai
   anthropic   ← pydantic-ai only
   ...

? Select extras (space to toggle, enter to confirm)
 ○ ruff
 ○ pytest
 ○ github-actions
```

Run: add provider API key to `.env`, then `uv run python -m src.main`

---

#### RAG System

No framework or provider prompt. Requires `OPENAI_API_KEY` in `.env`.

```
? Select extras (space to toggle, enter to confirm)
 ○ ruff
 ○ pytest
 ○ github-actions
```

Run: `uv run python -m src.main` (auto-ingests `data/` on first run)

---

#### Data Project

```
? Choose Project Type (Use arrow keys)
 » Data Analysis
   Dashboard
   ETL Pipeline
   Machine Learning

? Select extras (space to toggle, enter to confirm)
 ○ ruff
 ○ pytest
 ○ github-actions
```

| Type | Run command |
|---|---|
| Data Analysis | `uv run jupyter notebook` |
| Dashboard | `uv run streamlit run dashboard/app.py` |
| ETL Pipeline | `uv run python -m pipelines.run` |
| Machine Learning | `uv run python src/train.py` |

---

#### MCP Server

No framework or provider prompt.

```
? Select extras (space to toggle, enter to confirm)
 ○ ruff
 ○ pytest
 ○ github-actions
```

Run: `uv run python -m src.server` (waits on stdio for an MCP client to connect)

---

#### Custom Structure

The last option in the template picker. After selecting it, Spawn switches to a different flow:

1. Paste your folder/file layout (Tree, Markdown list, or Indented format) then Ctrl+D
2. Spawn previews the detected folder/file count
3. `Initialize Git? [Y/n]`
4. `Also generate CLAUDE.md for Claude Code? [y/N]`
5. `Initialize uv? [Y/n]`
6. *(if uv)* `Dependencies (comma separated, optional):`
7. *(if uv)* Optional Setup checkbox — `Ruff`, `Pytest`, `Pre-commit`, `Dockerfile`
8. `Additional ignore patterns (optional, comma separated):`
9. `Proceed? [Y/n]`

If the pasted structure contains a `README.md` or `.gitignore` entry, Spawn populates those files with generated content instead of leaving them empty.

---

### Generated files (every project)

Every generated project includes:

| File | Contents |
|---|---|
| `README.md` | Template-specific content with project name, structure, setup, and run instructions |
| `AGENTS.md` | Agent context file with project structure, setup, and conventions |
| `.gitignore` | Python defaults (`.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, etc.) |
| `.spawn/meta.json` | `intent`, `framework`, `provider`, `spawn_version`, `created_at`, `git`, `uv` |

If `--claude-md` was passed (or `"claude_md": true` in the config file), a `CLAUDE.md` file identical to `AGENTS.md` is also written.

`.spawn/meta.json` example:

```json
{
  "intent": "backend-api",
  "framework": "fastapi",
  "provider": null,
  "spawn_version": "1.0.6",
  "created_at": "2026-01-01T00:00:00+00:00",
  "generator": "blueprint",
  "git": true,
  "uv": true,
  "source": null
}
```

---

### GitHub publishing

After a successful creation, if Git was enabled, Spawn asks:

```
Publish to GitHub? [y/N]: y
Repository URL: https://github.com/your-username/my-project
```

Supported URL formats: `https://github.com/user/repo`, `https://github.com/user/repo.git`, `git@github.com:user/repo.git`.

Spawn stages all files, creates the initial commit, renames the branch to `main`, adds the remote, and pushes.

> The repository must already exist on GitHub. Spawn connects to it; it does not create it.

In non-interactive mode or when `--yes` / `-y` is passed, the publish prompt is skipped automatically.

---

### Error cases

All errors print `❌ message` in red. Any partial directory is deleted on failure.

| Situation | Exit code |
|---|---|
| Successful creation | 0 |
| SpawnError (bad name, unknown template, etc.) | 0 (error printed) |
| Non-interactive validation error | 1 |
| Ctrl+C at any prompt | 130 |

---

## `spawn doctor`

Scores the current directory (or a given path) for project health. All checks are filesystem-based — nothing is executed or sent over the network.

```bash
spawn doctor
spawn doctor ./path/to/project
```

**All checks**

| Check | Category | Weight |
|---|---|---|
| README.md | Documentation | 10 |
| AGENTS.md | Documentation | 5 |
| LICENSE | Documentation | 5 |
| CHANGELOG.md | Documentation | 5 |
| Git repository | Version Control | 15 |
| .gitignore | Version Control | 10 |
| Tests directory | Testing | 15 |
| Pytest configured | Testing | 10 |
| pyproject.toml | Configuration | 10 |
| .env.example | Configuration | 5 |
| Ruff configured | Code Quality | 10 |
| Type checker | Code Quality | 5 |
| Pre-commit | Code Quality | 5 |
| Dockerfile | Automation | 10 |
| GitHub Actions | Automation | 10 |

**Max score: 135**

**Score tiers**

| Score | Label |
|---|---|
| ≥ 80% | Excellent |
| 60–79% | Good |
| 40–59% | Fair |
| < 40% | Needs Attention |

---

## `spawn version`

Prints the installed version.

```bash
spawn version
# Spawn v1.0.6
```

---

## Exit codes

| Situation | Exit code |
|---|---|
| Any command succeeds | 0 |
| `spawn doctor` — path does not exist or is not a directory | 1 |
| Non-interactive validation error | 1 |
| Ctrl+C / EOF at any point | 130 |
