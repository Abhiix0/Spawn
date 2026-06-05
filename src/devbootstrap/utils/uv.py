import subprocess
from pathlib import Path


def initialize_uv(project_path: Path) -> None:
    subprocess.run(
        ["uv", "init", "--bare"],
        cwd=project_path,
        check=True,
    )

    subprocess.run(
        ["uv", "venv"],
        cwd=project_path,
        check=True,
    )