from __future__ import annotations

import json
from pathlib import Path

from spawn.core.exceptions import ConfigError
from spawn.core.models import ProjectConfig


def load_project(path: Path) -> ProjectConfig | None:
    """Reconstruct a best-effort ``ProjectConfig`` from ``<path>/.spawn/meta.json``.

    Returns ``None`` when the project has no ``.spawn/meta.json`` (not a
    Spawn-generated project). Raises ``ConfigError`` if the file is unreadable
    or is not a JSON object.

    The result is LOSSY: ``meta.json`` does not record ``cli_type``,
    ``data_type``, ``extras``, ``license`` or ``generate_claude_md``, so those
    keep their defaults; ``name`` is taken from the directory name. The intent
    is not validated against the registry, so projects from other Spawn
    versions still load. Read-only: nothing is written.
    """
    root = Path(path).resolve()
    meta_file = root / ".spawn" / "meta.json"
    if not meta_file.is_file():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"Cannot read {meta_file}: {exc}") from exc
    if not isinstance(meta, dict):
        raise ConfigError(f"Invalid {meta_file}: expected a JSON object")

    custom = meta.get("generator") == "custom"
    return ProjectConfig(
        name=root.name,
        template=meta.get("intent") or ("custom" if custom else ""),
        use_git=meta.get("git", False),
        framework=meta.get("framework"),
        provider=meta.get("provider"),
        use_uv=meta.get("uv", True),
        custom_source_format=meta.get("source") if custom else None,
        destination=root,
    )
