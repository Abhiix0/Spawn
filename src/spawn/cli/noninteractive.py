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

# Keys accepted in a JSON config file.  Any key not in this set is rejected.
_KNOWN_CONFIG_KEYS: frozenset[str] = frozenset(
    {
        "name",
        "template",
        "framework",
        "provider",
        "cli_type",
        "data_type",
        "extras",
        "git",
        "uv",
        "claude_md",
        "license",
    }
)


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

    The file must be a JSON object containing at least "name" and "template".
    Unknown keys are rejected.  Boolean fields must be actual JSON booleans
    (true/false), not strings.  All other validation is delegated to
    build_config_from_args.

    Raises SpawnError for missing file, directory path, invalid UTF-8,
    invalid JSON, unknown keys, wrong types, or any field errors.
    """
    # Reject directory paths supplied instead of files.
    if path.is_dir():
        raise ConfigError(f"Config path is a directory, not a file: {path}")

    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    # Read as bytes first so we can give a clear UTF-8 error.
    try:
        raw_bytes = path.read_bytes()
    except OSError as e:
        raise ConfigError(f"Cannot read config file: {e}") from e

    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ConfigError(f"Config file is not valid UTF-8: {e}") from e

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config file: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a JSON object.")

    # Reject unknown keys so typos don't silently go unnoticed.
    unknown = set(data.keys()) - _KNOWN_CONFIG_KEYS
    if unknown:
        sorted_unknown = ", ".join(sorted(unknown))
        raise ConfigError(
            f"Config file contains unknown key(s): {sorted_unknown}. "
            f"Allowed keys: {', '.join(sorted(_KNOWN_CONFIG_KEYS))}."
        )

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

    # Strictly require JSON booleans for boolean fields.
    # String values like "false" or "true" are rejected to avoid ambiguity.
    git_raw = data.get("git", True)
    if not isinstance(git_raw, bool):
        raise ConfigError(
            f"'git' in config file must be a boolean (true or false), got {git_raw!r}."
        )
    git: bool = git_raw

    uv_raw = data.get("uv", True)
    if not isinstance(uv_raw, bool):
        raise ConfigError(
            f"'uv' in config file must be a boolean (true or false), got {uv_raw!r}."
        )
    uv: bool = uv_raw

    claude_md_raw = data.get("claude_md", use_claude_md)
    if not isinstance(claude_md_raw, bool):
        raise ConfigError(
            f"'claude_md' in config file must be a boolean (true or false), "
            f"got {claude_md_raw!r}."
        )
    claude_md: bool = claude_md_raw

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
