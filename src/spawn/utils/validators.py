import re

from spawn.core.exceptions import SpawnError


def validate_project_name(name: str) -> None:
    if not re.search(r"[a-zA-Z0-9]", name):
        raise SpawnError(
            "Project name must contain at least one letter or number."
        )

    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise SpawnError(
            "Project name can only contain letters, numbers, hyphens (-), and underscores (_)."
        )