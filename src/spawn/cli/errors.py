import os
from typing import NoReturn

import typer

from spawn.core.exceptions import SpawnError
from spawn.utils.console import console

UNEXPECTED_EXIT_CODE = 10


def fail(e: SpawnError) -> NoReturn:
    """Print an expected error and exit with its category's exit code."""
    console.print(f"[red]❌ {e}[/red]")
    raise typer.Exit(e.exit_code)


def report_unexpected(e: BaseException) -> NoReturn:
    """Short message for unexpected errors; re-raise when SPAWN_DEBUG is set."""
    if os.environ.get("SPAWN_DEBUG", "").strip().lower() not in (
        "",
        "0",
        "false",
        "no",
    ):
        raise e
    console.print(f"[red]❌ Unexpected error ({type(e).__name__}): {e}[/red]")
    console.print("[dim]Re-run with SPAWN_DEBUG=1 for a traceback.[/dim]")
    raise typer.Exit(UNEXPECTED_EXIT_CODE)
