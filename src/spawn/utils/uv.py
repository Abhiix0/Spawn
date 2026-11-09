import subprocess
from pathlib import Path

from spawn.core.exceptions import ToolchainError
from spawn.utils.redact import redact_url


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
        raise ToolchainError("UV is not installed or not available in PATH.")

    except subprocess.CalledProcessError as exc:
        stderr_msg = redact_url(exc.stderr.strip()) if exc.stderr else ""
        raise ToolchainError(
            stderr_msg or "Failed to initialize UV environment."
        ) from exc


def install_packages(
    project_path: Path, packages: list[str], dev: bool = False
) -> None:
    if not packages:
        return

    cmd = ["uv", "add"] + (["--dev"] if dev else []) + packages

    try:
        subprocess.run(
            cmd,
            cwd=project_path,
            check=True,
            capture_output=True,
            text=True,
        )

    except FileNotFoundError:
        raise ToolchainError("UV is not installed or not available in PATH.")

    except subprocess.CalledProcessError as exc:
        stderr_msg = redact_url(exc.stderr.strip()) if exc.stderr else ""
        raise ToolchainError(
            stderr_msg or "Failed to install packages."
        ) from exc
