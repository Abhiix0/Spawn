import subprocess
from pathlib import Path

from spawn.core.exceptions import SpawnError


def initialize_git(project_path: Path) -> None:
    try:
        subprocess.run(
            ["git", "init"],
            cwd=project_path,
            check=True,
            capture_output=True,
            text=True,
        )

    except FileNotFoundError:
        raise SpawnError(
            "Git is not installed or not available in PATH."
        )

    except subprocess.CalledProcessError:
        raise SpawnError(
            "Failed to initialize Git repository."
        )