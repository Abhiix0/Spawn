from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from spawn.core.exceptions import ConfigError


@dataclass(frozen=True)
class ProjectMetadata:
    """Historical metadata recorded in ``.spawn/meta.json`` at generation time.

    This is NOT verified current state: the repo may have changed since Spawn
    wrote it. It holds only recorded fields (each ``None`` if omitted) and
    deliberately does not record name, extras, license, cli_type, data_type or
    claude_md.
    """

    intent: str | None = None
    framework: str | None = None
    provider: str | None = None
    spawn_version: str | None = None
    created_at: str | None = None
    generator: str | None = None
    git: bool | None = None
    uv: bool | None = None
    source: str | None = None


def read_project_metadata(path: Path) -> ProjectMetadata | None:
    """Read ``<path>/.spawn/meta.json`` without interpreting or validating it.

    Returns ``None`` when the file is absent (not a Spawn-generated project).
    Raises ``ConfigError`` if the file is unreadable or not a JSON object. The
    intent is not validated against the registry, so projects from other Spawn
    versions still load; unknown keys are ignored. Read-only.
    """
    meta_file = Path(path) / ".spawn" / "meta.json"
    if not meta_file.is_file():
        return None
    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"Cannot read {meta_file}: {exc}") from exc
    if not isinstance(meta, dict):
        raise ConfigError(f"Invalid {meta_file}: expected a JSON object")

    return ProjectMetadata(
        intent=meta.get("intent"),
        framework=meta.get("framework"),
        provider=meta.get("provider"),
        spawn_version=meta.get("spawn_version"),
        created_at=meta.get("created_at"),
        generator=meta.get("generator"),
        git=meta.get("git"),
        uv=meta.get("uv"),
        source=meta.get("source"),
    )
