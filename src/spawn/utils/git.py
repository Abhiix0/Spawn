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

def run_git_command(
    project_path: Path,
    *args: str,
) -> None:
    """
    Execute a git command inside a project.
    """

    try:
        subprocess.run(
            ["git", *args],
            cwd=project_path,
            check=True,
            capture_output=True,
            text=True,
        )

    except FileNotFoundError:
        raise SpawnError(
            "Git is not installed or not available in PATH."
        )

    except subprocess.CalledProcessError as exc:
        raise SpawnError(
            exc.stderr.strip()
            or "Git command failed."
        ) from exc

def add_all(project_path: Path) -> None:
    run_git_command(
        project_path,
        "add",
        ".",
    )

def commit(
    project_path: Path,
    message: str,
) -> None:
    run_git_command(
        project_path,
        "commit",
        "-m",
        message,
    )

def rename_main_branch(
    project_path: Path,
) -> None:
    run_git_command(
        project_path,
        "branch",
        "-M",
        "main",
    )

def add_remote(
    project_path: Path,
    repo_url: str,
) -> None:
    run_git_command(
        project_path,
        "remote",
        "add",
        "origin",
        repo_url,
    )

def push_origin_main(
    project_path: Path,
) -> None:
    run_git_command(
        project_path,
        "push",
        "-u",
        "origin",
        "main",
    )

def remote_exists(
    project_path: Path,
) -> bool:
    """Check if a remote named 'origin' already exists in the repository."""
    try:
        result = subprocess.run(
            ["git", "remote"],
            cwd=project_path,
            check=True,
            capture_output=True,
            text=True,
        )
        return "origin" in result.stdout.splitlines()

    except FileNotFoundError:
        raise SpawnError(
            "Git is not installed or not available in PATH."
        )

    except subprocess.CalledProcessError:
        return False

def is_git_repository(
    project_path: Path,
) -> bool:
    """Check if the given path is inside a Git repository."""
    return (project_path / ".git").is_dir()