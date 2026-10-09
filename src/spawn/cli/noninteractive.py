"""
Non-interactive configuration builders for Spawn.

Provides two public functions:

- build_config_from_args: build a validated ProjectConfig from keyword arguments
- build_config_from_file: build a validated ProjectConfig from a JSON config file
"""

from __future__ import annotations

import json
from pathlib import Path

from spawn.core.exceptions import ConfigError
from spawn.core.models import ProjectConfig
from spawn.core.planning import plan_project
from spawn.core.registry import get_metadata, list_templates  # noqa: F401
from spawn.generators.project_files import SUPPORTED_LICENSES  # noqa: F401
from spawn.templates.agent import (  # noqa: F401
    get_supported_providers as get_agent_providers,
)
from spawn.templates.chatbot import (  # noqa: F401
    get_supported_providers as get_chatbot_providers,
)
from spawn.utils.validators import validate_project_name  # noqa: F401


def build_config_from_args(
    name: str,
    template: str,
    framework: str | None = None,
    provider: str | None = None,
    cli_type: str | None = None,
    data_type: str | None = None,
    extras: list[str] | None = None,
    use_git: bool = True,
    use_uv: bool = True,
    use_claude_md: bool = False,
    license: str = "mit",
) -> ProjectConfig:
    """
    Build and return a validated ProjectConfig from explicit arguments.

    Raises SpawnError for any invalid input; see spawn.core.planning.plan_project.
    """
    return plan_project(
        name,
        template,
        framework=framework,
        provider=provider,
        cli_type=cli_type,
        data_type=data_type,
        extras=extras,
        use_git=use_git,
        use_uv=use_uv,
        generate_claude_md=use_claude_md,
        license=license,
    )


def build_config_from_file(
    path: Path,
    use_claude_md: bool = False,
    license_kind: str = "mit",
) -> ProjectConfig:
    """
    Build and return a validated ProjectConfig from a JSON config file.

    The file must be a JSON object with at least "name" and "template" fields.
    All other validation is delegated to build_config_from_args.

    Raises SpawnError for missing file, invalid JSON, or any field errors.
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config file: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a JSON object.")

    name = data.get("name", "")
    if not name:
        raise ConfigError("Config file must include a 'name' field.")

    template = data.get("template", "")
    if not template:
        raise ConfigError("Config file must include a 'template' field.")

    framework: str | None = data.get("framework", None)
    provider: str | None = data.get("provider", None)
    cli_type: str | None = data.get("cli_type", None)
    data_type: str | None = data.get("data_type", None)

    extras_raw = data.get("extras", [])
    if not isinstance(extras_raw, list) or not all(
        isinstance(e, str) for e in extras_raw
    ):
        raise ConfigError("'extras' in config file must be a list of strings.")
    extras: list[str] = extras_raw

    git: bool = data.get("git", True)
    uv: bool = data.get("uv", True)
    claude_md: bool = data.get("claude_md", use_claude_md)
    license_val = data.get("license", license_kind)
    if not isinstance(license_val, str):
        raise ConfigError("'license' in config file must be a string.")

    return build_config_from_args(
        name=name,
        template=template,
        framework=framework,
        provider=provider,
        cli_type=cli_type,
        data_type=data_type,
        extras=extras,
        use_git=git,
        use_uv=uv,
        use_claude_md=claude_md,
        license=license_val,
    )
