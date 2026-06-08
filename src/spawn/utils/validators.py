import re

from spawn.core.exceptions import SpawnError


def validate_project_name(name: str) -> None:
    pattern = r"^(?=.*[a-zA-Z0-9])[a-zA-Z0-9_-]+$"

    if not re.match(pattern, name):
        raise SpawnError(
            "Project name can only contain letters, numbers, hyphens (-), and underscores (_)."
        )