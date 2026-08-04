INIT_CONTENT = ""

SERVER_CONTENT = """\
\"\"\"MCP server entrypoint for {project_name}.\"\"\"

from mcp.server import MCPServer

mcp = MCPServer("{project_name}")


def _add(a: int, b: int) -> int:
    return a + b


@mcp.tool()
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers together.\"\"\"
    return _add(a, b)


def _get_server_info() -> str:
    return "{project_name} MCP server, built with Spawn."


@mcp.resource("info://server")
def server_info() -> str:
    \"\"\"Return basic information about this MCP server.\"\"\"
    return _get_server_info()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
"""

TEST_CONTENT = """\
from src.server import _add, _get_server_info


def test_add():
    assert _add(2, 3) == 5


def test_add_negative_numbers():
    assert _add(-1, -1) == -2


def test_server_info_returns_nonempty_string():
    info = _get_server_info()
    assert isinstance(info, str)
    assert len(info) > 0
"""

ENV_CONTENT = """\
# Environment variables for {project_name}
# This MCP server has no required environment variables by default.
# Add any secrets or configuration your tools/resources need here.
"""

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


def make_readme() -> str:
    return """\
# {project_name}

An MCP (Model Context Protocol) server, generated with Spawn.

This server exposes one example tool (`add`) and one example resource
(`info://server`) over the `stdio` transport, ready to connect to any
MCP client — Claude Desktop, Claude Code, or your own client built on
the MCP SDK.

## Run it directly

```bash
uv run python -m src.server
```

It will wait on stdio for an MCP client to connect — this is normal,
it's not meant to be run standalone in a terminal for long.

## Connect it to Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{{
  "mcpServers": {{
    "{project_name}": {{
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/{project_name}", "run", "python", "-m", "src.server"]
    }}
  }}
}}
```

Replace `/absolute/path/to/{project_name}` with this project's actual
path, then restart Claude Desktop.

## Add your own tools and resources

Open `src/server.py`. Add a new function decorated with `@mcp.tool()`
for anything you want an MCP client to be able to call, or
`@mcp.resource("your://uri")` for anything you want it to be able to
read.

## Tests

```bash
uv run pytest
```
"""
