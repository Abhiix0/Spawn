import subprocess
from pathlib import Path

from spawn.core.exceptions import SpawnError


def initialize_uv(project_path: Path) -> None:
    try:
        subprocess.run(
            ["uv", "init", "--bare"],
            cwd=project_path,
            check=True,
            capture_output=True,
            text=True,
        )

        subprocess.run(
            ["uv", "venv"],
            cwd=project_path,
            check=True,
            capture_output=True,
            text=True,
        )

    except FileNotFoundError:
        raise SpawnError(
            "UV is not installed or not available in PATH."
        )

    except subprocess.CalledProcessError as exc:
        raise SpawnError(
            exc.stderr.strip() or "Failed to initialize UV environment."
        ) from exc


def install_packages(project_path: Path, packages: list[str]) -> None:
    if not packages:
        return

    try:
        subprocess.run(
            ["uv", "add"] + packages,
            cwd=project_path,
            check=True,
            capture_output=True,
            text=True,
        )

    except FileNotFoundError:
        raise SpawnError(
            "UV is not installed or not available in PATH."
        )

    except subprocess.CalledProcessError as exc:
        raise SpawnError(
            exc.stderr.strip() or "Failed to install packages."
        ) from exc
