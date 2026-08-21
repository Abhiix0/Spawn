import re

from spawn.core.exceptions import SpawnError

_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def validate_project_name(name: str) -> None:
    # Check for Windows reserved device names (case-insensitive, strip any
    # extension so e.g. "NUL.txt" is caught too).
    stem = name.split(".")[0].upper()
    if stem in _WINDOWS_RESERVED:
        raise SpawnError(
            f"'{name}' is a reserved Windows device name and can't be used as a project name."
        )

    if not re.search(r"[a-zA-Z0-9]", name):
        raise SpawnError(
            "Project name must contain at least one letter or number."
        )

    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise SpawnError(
            "Project name can only contain letters, numbers, hyphens (-), and underscores (_)."
        )
