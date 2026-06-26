INIT_CONTENT = ""

TYPER_MAIN_CONTENT = """\
import typer

app = typer.Typer()


@app.command()
def hello() -> None:
    \"\"\"Say hello.\"\"\"
    typer.echo("Hello from {project_name}!")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
"""

TYPER_COMMANDS_INIT_CONTENT = ""

TYPER_UTILS_INIT_CONTENT = ""

TYPER_TEST_CONTENT = """\
from typer.testing import CliRunner

from src.main import app

runner = CliRunner()


def test_hello_command() -> None:
    result = runner.invoke(app, ["hello"])
    assert result.exit_code == 0
    assert "Hello" in result.output
"""

TYPER_README_CONTENT = """\
# {project_name}

A CLI application generated with Spawn.

## Getting Started

```bash
uv run python -m src.main hello
```

## Running Tests

```bash
uv run pytest
```

## Commands

| Command | Description             |
|---------|-------------------------|
| hello   | Prints a hello message  |

## Development

```bash
uv run python -m src.main --help
```
"""

# ---------------------------------------------------------------------------
# Click
# ---------------------------------------------------------------------------

CLICK_MAIN_CONTENT = """\
import click


@click.group()
def main() -> None:
    \"\"\"CLI tool for {project_name}.\"\"\"
    pass


@main.command()
def hello() -> None:
    \"\"\"Say hello.\"\"\"
    click.echo("Hello from {project_name}!")


if __name__ == "__main__":
    main()
"""

CLICK_TEST_CONTENT = """\
from click.testing import CliRunner

from src.main import main

runner = CliRunner()


def test_hello_command() -> None:
    result = runner.invoke(main, ["hello"])
    assert result.exit_code == 0
    assert "Hello" in result.output
"""

CLICK_README_CONTENT = """\
# {project_name}

A CLI application generated with Spawn.

## Getting Started

```bash
uv run python -m src.main hello
```

## Running Tests

```bash
uv run pytest
```

## Commands

| Command | Description             |
|---------|-------------------------|
| hello   | Prints a hello message  |

## Development

```bash
uv run python -m src.main --help
```

Built with Click
"""

# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------

ARGPARSE_MAIN_CONTENT = """\
import argparse


def hello(args: argparse.Namespace) -> None:
    \"\"\"Say hello.\"\"\"
    print("Hello from {project_name}!")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="{project_name}",
        description="{project_name} CLI",
    )

    subparsers = parser.add_subparsers(dest="command")

    hello_parser = subparsers.add_parser("hello", help="Say hello")
    hello_parser.set_defaults(func=hello)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
"""

ARGPARSE_TEST_CONTENT = """\
import subprocess
import sys


def test_hello_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "src.main", "hello"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Hello" in result.stdout
"""

ARGPARSE_README_CONTENT = """\
# {project_name}

A CLI application generated with Spawn.

## Getting Started

```bash
uv run python -m src.main hello
```

## Running Tests

```bash
uv run pytest
```

## Commands

| Command | Description             |
|---------|-------------------------|
| hello   | Prints a hello message  |

## Development

```bash
uv run python -m src.main --help
```

Built with Python's standard argparse library. No external dependencies required.
"""

# ---------------------------------------------------------------------------
# Interactive — Typer
# ---------------------------------------------------------------------------

TYPER_INTERACTIVE_MAIN_CONTENT = """\
import typer

app = typer.Typer()


@app.command()
def greet() -> None:
    \"\"\"Greet the user interactively.\"\"\"
    name = typer.prompt("What is your name?")
    typer.echo(f"Hello, {{name}}! Welcome to {project_name}.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
"""

TYPER_INTERACTIVE_TEST_CONTENT = """\
from typer.testing import CliRunner

from src.main import app

runner = CliRunner()


def test_greet_command() -> None:
    result = runner.invoke(app, ["greet"], input="Alice\\n")
    assert result.exit_code == 0
    assert "Hello, Alice" in result.output
"""

# ---------------------------------------------------------------------------
# Interactive — Click
# ---------------------------------------------------------------------------

CLICK_INTERACTIVE_MAIN_CONTENT = """\
import click


@click.group()
def main() -> None:
    \"\"\"Interactive CLI for {project_name}.\"\"\"
    pass


@main.command()
def greet() -> None:
    \"\"\"Greet the user interactively.\"\"\"
    name = click.prompt("What is your name?")
    click.echo(f"Hello, {{name}}! Welcome to {project_name}.")


if __name__ == "__main__":
    main()
"""

CLICK_INTERACTIVE_TEST_CONTENT = """\
from click.testing import CliRunner

from src.main import main

runner = CliRunner()


def test_greet_command() -> None:
    result = runner.invoke(main, ["greet"], input="Alice\\n")
    assert result.exit_code == 0
    assert "Hello, Alice" in result.output
"""

# ---------------------------------------------------------------------------
# Interactive — Argparse
# ---------------------------------------------------------------------------

ARGPARSE_INTERACTIVE_MAIN_CONTENT = """\
import argparse


def greet(args: argparse.Namespace) -> None:
    \"\"\"Greet the user interactively.\"\"\"
    name = input("What is your name? ")
    print(f"Hello, {{name}}! Welcome to {project_name}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="{project_name}",
        description="{project_name} interactive CLI",
    )

    subparsers = parser.add_subparsers(dest="command")

    greet_parser = subparsers.add_parser("greet", help="Greet the user")
    greet_parser.set_defaults(func=greet)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
"""

ARGPARSE_INTERACTIVE_TEST_CONTENT = """\
import subprocess
import sys


def test_greet_command() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "src.main", "greet"],
        input="Alice\\n",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Hello, Alice" in result.stdout
"""
