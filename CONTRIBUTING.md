# Contributing to spawnio

Solo-maintained, but PRs are welcome. Here's what you need to know.

---

## Prerequisites

- Python 3.12+ (`uv python install 3.12` if using uv)
- [uv](https://github.com/astral-sh/uv) installed

---

## Setup

```bash
git clone https://github.com/Abhiix0/Spawn.git
cd Spawn
uv sync --all-groups
```

---

## Running tests

```bash
uv run pytest
```

With coverage:

```bash
uv run pytest --cov=src/spawn --cov-report=term-missing
```

---

## Linting and formatting

```bash
uv run ruff check .
uv run ruff format .
```

Both must pass before opening a PR. CI enforces this.

---

## Adding a new template

Templates follow a consistent three-file pattern. MCP Server (`src/spawn/templates/mcp_server/`) is the cleanest minimal example to copy from.

### 1. Create the template package

```
src/spawn/templates/<your_slug>/
    __init__.py     # MyTemplate(BaseTemplate) class
    content.py      # string constants + make_readme() + make_agents_md()
```

**`content.py`** holds all file content as triple-quoted strings with `{project_name}` placeholders (resolved later via `.format_map(context)`). Export `make_readme()` and `make_agents_md()` as functions that return the formatted string — these are called by `BaseTemplate` machinery automatically.

**`__init__.py`** subclasses `BaseTemplate`:

```python
class MyTemplate(BaseTemplate):
    def __init__(self, extras: list[str] | None = None) -> None:
        self.extras = extras or []
        super().__init__(
            name="My Template",
            folders=["src", "tests"],
            starter_files=[
                ("src/__init__.py", INIT_CONTENT),
                ("src/main.py",     MAIN_CONTENT),
                (".env.example",    ENV_CONTENT),
            ],
            next_steps=["cd {project_name}", "uv run python -m src.main"],
        )

    def get_readme_content(self, context: dict) -> str | None:
        return make_readme().format_map(context)

    def get_agents_md_content(self, context: dict) -> str | None:
        return make_agents_md().format_map(context)

    def get_dependencies(self) -> list[str]:
        base = ["some-package"]
        if "pytest" in self.extras:
            base.append("pytest")
        return base

    def post_install(self, project_path: Path) -> None:
        # Write pyproject.toml sections, CI workflows, etc. as needed.
        pass
```

If your template needs framework or provider selection, look at `ChatbotTemplate` or `AgentTemplate` — those accept `framework` and `provider` constructor args and use `get_supported_providers()` to filter the provider list per framework.

### 2. Register in `src/spawn/core/registry.py`

Add an import and a `TemplateMetadata` entry to `TEMPLATES`:

```python
from spawn.templates.my_template import MyTemplate

TEMPLATES = {
    # ... existing entries ...
    "my-slug": TemplateMetadata(
        slug="my-slug",
        display_name="My Template",
        description="One-line description shown in spawn doctor output",
        template_class=MyTemplate,
        available_extras=["ruff", "pytest", "github-actions"],
        # available_frameworks, available_providers, available_cli_types,
        # available_data_types — only set the fields your template uses.
    ),
}
```

`instantiate_template()` inspects the constructor signature and forwards only the fields the class accepts, so no changes to that function are needed.

### 3. Write tests

Add two test files mirroring the existing pattern:

| File | What to test |
|---|---|
| `tests/test_<slug>_template.py` | Template constants, `get_dependencies()`, `get_readme_content()`, `py_compile` on each Python starter file, no unescaped braces |
| `tests/test_<slug>_generator.py` | `ProjectGenerator().generate()` with mocked uv/git/install, directory structure, README content, `.spawn/meta.json` fields |

See `tests/test_mcp_server_template.py` and `tests/test_mcp_server_generator.py` for the exact mock patterns (`_mock_uv_and_install()` context manager, `_cfg()` helper, `patch.object(MyTemplate, "post_install")`).

Also update `tests/test_registry.py`: increment the `len(slugs) == N` assertion and add `assert "my-slug" in slugs`.

---

## Branch and commit conventions

The git log uses a lightweight conventional-commits style — prefix commits with `feat:`, `fix:`, `docs:`, or `chore:` and use the imperative mood in the subject line:

```
feat: add <slug> template
fix: handle edge case in parse_structure
docs: update CONTRIBUTING.md
chore: bump version to 1.0.8
```

Branch off `main`, use a short descriptive name (`feat/my-template`, `fix/windows-path`, etc.).

---

## PR expectations

- All existing tests must pass (`uv run pytest`).
- New templates require both a `_template` and a `_generator` test file.
- `uv run ruff check .` and `uv run ruff format --check .` must be clean.
- CI (`.github/workflows/ci.yml`) must be green.
- Keep PRs focused — one template or fix per PR.

---

## Reporting issues / asking questions

GitHub Issues are currently **restricted** on this repo. To reach the maintainer:

- Open a [GitHub Discussion](https://github.com/Abhiix0/Spawn/discussions) if Discussions are enabled.
- Otherwise, leave a comment on an existing PR or tag `@Abhiix0` in your PR description.

If you hit a bug that's blocking you, a PR with a failing test that reproduces it is a faster path to a fix than waiting for issues to be opened.
