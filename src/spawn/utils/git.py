import subprocess
from pathlib import Path


def initialize_git(project_path: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=project_path,
        check=True,
    )