import datetime
import json
from pathlib import Path

from spawn import __version__
from spawn.core.models import ProjectConfig


def write_project_meta(
    project_path: Path, config: ProjectConfig, *, generator: str
) -> None:
    """Write ``.spawn/meta.json`` for a generated project.

    ``generator`` is "blueprint" (template projects) or "custom".
    """
    if generator == "custom":
        intent, framework, provider = "custom", None, None
        source = config.custom_source_format or "tree"
    else:
        intent, framework, provider = (
            config.template,
            config.framework,
            config.provider,
        )
        source = None

    meta_dir = project_path / ".spawn"
    meta_dir.mkdir(exist_ok=True)
    (meta_dir / "meta.json").write_text(
        json.dumps(
            {
                "intent": intent,
                "framework": framework,
                "provider": provider,
                "spawn_version": __version__,
                "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "generator": generator,
                "git": config.use_git,
                "uv": config.use_uv,
                "source": source,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
