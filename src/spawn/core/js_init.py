# ── js_init.py ─────────────────────────────────────────────────────────────────
# Handles JavaScript-specific project initialization:
#   - Checks that node and npm are available on PATH
#   - Runs `npm init -y` inside the new project directory
#
# Mirrors the pattern used by uv_init.py for Python projects.
# ───────────────────────────────────────────────────────────────────────────────

import shutil
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


def _check_dependency(cmd: str) -> bool:
    """Return True if `cmd` is available on PATH, False otherwise."""
    return shutil.which(cmd) is not None


def run_npm_init(project_path: Path) -> bool:
    """
    Run `npm init -y` inside *project_path*.

    Returns True on success, False on failure (with a Rich error message printed).
    Missing node / npm is treated as a non-fatal warning so the project folder
    is still created — the user just needs to run `npm init -y` manually.
    """
    if not _check_dependency("node"):
        console.print(
            "[yellow]⚠ node not found on PATH — skipping npm init.[/yellow]\n"
            "  Install Node.js from https://nodejs.org and then run [bold]npm init -y[/bold] "
            "inside your project."
        )
        return False

    if not _check_dependency("npm"):
        console.print(
            "[yellow]⚠ npm not found on PATH — skipping npm init.[/yellow]\n"
            "  Make sure npm is installed alongside Node.js, then run "
            "[bold]npm init -y[/bold] inside your project."
        )
        return False

    try:
        subprocess.run(
            ["npm", "init", "-y"],
            cwd=project_path,
            check=True,
            capture_output=True,   # keeps the terminal clean; errors surface via CalledProcessError
        )
        return True
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[red]✗ npm init failed:[/red] {exc.stderr.decode().strip() or str(exc)}"
        )
        return False
