"""
Non-interactive configuration builders for Spawn.

Provides two public functions:

- build_config_from_args: build a validated ProjectConfig from keyword arguments
- build_config_from_file: build a validated ProjectConfig from a JSON config file
"""

from __future__ import annotations

import json
from pathlib import Path

from spawn.core.exceptions import SpawnError
from spawn.core.models import ProjectConfig
from spawn.core.registry import get_metadata, list_templates
from spawn.templates.agent import get_supported_providers as get_agent_providers
from spawn.templates.chatbot import get_supported_providers as get_chatbot_providers
from spawn.utils.validators import validate_project_name


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
) -> ProjectConfig:
    """
    Build and return a validated ProjectConfig from explicit arguments.

    Raises SpawnError for any invalid input.  Validation runs in this order:
    project name, directory existence, template, cli_type, data_type,
    framework, provider, extras.
    """
    # 1. Project name — let validate_project_name raise naturally.
    validate_project_name(name)

    # 2. Directory existence.
    if Path(name).exists():
        raise SpawnError(f"A directory named '{name}' already exists.")

    # 3. Template.
    metadata = get_metadata(template)
    if metadata is None:
        valid = ", ".join(m.slug for m in list_templates())
        raise SpawnError(f"Unknown template: '{template}'. Valid templates: {valid}")

    # 4. cli_type.
    if metadata.available_cli_types:
        if cli_type is None:
            cli_type = metadata.available_cli_types[0]
        elif cli_type not in metadata.available_cli_types:
            valid = ", ".join(metadata.available_cli_types)
            raise SpawnError(
                f"Invalid cli_type: '{cli_type}'. "
                f"Valid options for '{template}': {valid}"
            )
    else:
        cli_type = None

    # 5. data_type.
    if metadata.available_data_types:
        if data_type is None:
            data_type = metadata.available_data_types[0]
        elif data_type not in metadata.available_data_types:
            valid = ", ".join(metadata.available_data_types)
            raise SpawnError(
                f"Invalid data_type: '{data_type}'. "
                f"Valid options for '{template}': {valid}"
            )
    else:
        data_type = None

    # 6. framework.
    if metadata.available_frameworks:
        if framework is None:
            framework = metadata.available_frameworks[0]
        elif framework not in metadata.available_frameworks:
            valid = ", ".join(metadata.available_frameworks)
            raise SpawnError(
                f"Invalid framework: '{framework}'. "
                f"Valid options for '{template}': {valid}"
            )
    else:
        framework = None

    # 7. provider — only when the template declares providers AND a framework resolved.
    if metadata.available_providers and framework is not None:
        if metadata.slug == "agent":
            valid_providers = get_agent_providers(framework)
        elif metadata.slug == "chatbot":
            valid_providers = get_chatbot_providers(framework)
        else:
            valid_providers = metadata.available_providers

        if provider is None:
            provider = valid_providers[0]
        elif provider not in valid_providers:
            valid = ", ".join(valid_providers)
            raise SpawnError(
                f"Invalid provider: '{provider}'. "
                f"Valid options for '{template}' with framework '{framework}': {valid}"
            )
    else:
        provider = None

    # 8. extras — fail-fast on first invalid item, then de-duplicate preserving order.
    input_extras: list[str] = extras if extras is not None else []
    if not metadata.available_extras:
        validated_extras: list[str] = []
    else:
        # Validate first (fail-fast on first bad item in input order).
        for item in input_extras:
            if item not in metadata.available_extras:
                valid = ", ".join(metadata.available_extras)
                raise SpawnError(
                    f"Invalid extra: '{item}'. "
                    f"Valid options for '{template}': {valid}"
                )
        # Build de-duplicated result preserving input order.
        seen: set[str] = set()
        validated_extras = []
        for item in input_extras:
            if item not in seen:
                validated_extras.append(item)
                seen.add(item)

    return ProjectConfig(
        name=name,
        template=template,
        use_git=use_git,
        framework=framework,
        extras=validated_extras,
        cli_type=cli_type,
        data_type=data_type,
        provider=provider,
        use_uv=use_uv,
    )


def build_config_from_file(path: Path) -> ProjectConfig:
    """
    Build and return a validated ProjectConfig from a JSON config file.

    The file must be a JSON object with at least "name" and "template" fields.
    All other validation is delegated to build_config_from_args.

    Raises SpawnError for missing file, invalid JSON, or any field errors.
    """
    if not path.exists():
        raise SpawnError(f"Config file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SpawnError(f"Invalid JSON in config file: {e}") from e

    if not isinstance(data, dict):
        raise SpawnError("Config file must contain a JSON object.")

    name = data.get("name", "")
    if not name:
        raise SpawnError("Config file must include a 'name' field.")

    template = data.get("template", "")
    if not template:
        raise SpawnError("Config file must include a 'template' field.")

    framework: str | None = data.get("framework", None)
    provider: str | None = data.get("provider", None)
    cli_type: str | None = data.get("cli_type", None)
    data_type: str | None = data.get("data_type", None)

    extras_raw = data.get("extras", [])
    if not isinstance(extras_raw, list) or not all(
        isinstance(e, str) for e in extras_raw
    ):
        raise SpawnError("'extras' in config file must be a list of strings.")
    extras: list[str] = extras_raw

    git: bool = data.get("git", True)
    uv: bool = data.get("uv", True)

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
    )
