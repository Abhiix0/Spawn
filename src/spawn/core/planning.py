"""
Shared project planning: option validation and normalization.

plan_project is the single place where template/option rules are applied
(defaults, framework -> provider lookup, extras de-duplication, license).
"""

from __future__ import annotations

from pathlib import Path

from spawn.core.exceptions import InvalidInputError
from spawn.core.models import ProjectConfig
from spawn.core.registry import get_metadata, list_templates
from spawn.generators.destination import assert_available
from spawn.generators.project_files import SUPPORTED_LICENSES
from spawn.templates.agent import get_supported_providers as get_agent_providers
from spawn.templates.chatbot import get_supported_providers as get_chatbot_providers
from spawn.utils.validators import validate_project_name


def supported_providers(slug: str, framework: str, declared: list[str]) -> list[str]:
    """Providers valid for *slug* with *framework* (falls back to *declared*)."""
    if slug == "agent":
        return get_agent_providers(framework)
    if slug == "chatbot":
        return get_chatbot_providers(framework)
    return declared


def plan_project(
    name: str,
    template: str,
    *,
    framework: str | None = None,
    provider: str | None = None,
    cli_type: str | None = None,
    data_type: str | None = None,
    extras: list[str] | None = None,
    use_git: bool = True,
    use_uv: bool = True,
    generate_claude_md: bool = False,
    license: str = "mit",
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
    assert_available(Path(name), f"A directory named '{name}' already exists.")

    # 3. Template.
    metadata = get_metadata(template)
    if metadata is None:
        valid = ", ".join(m.slug for m in list_templates())
        raise InvalidInputError(
            f"Unknown template: '{template}'. Valid templates: {valid}"
        )

    # 4. cli_type.
    if metadata.available_cli_types:
        if cli_type is None:
            cli_type = metadata.available_cli_types[0]
        elif cli_type not in metadata.available_cli_types:
            valid = ", ".join(metadata.available_cli_types)
            raise InvalidInputError(
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
            raise InvalidInputError(
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
            raise InvalidInputError(
                f"Invalid framework: '{framework}'. "
                f"Valid options for '{template}': {valid}"
            )
    else:
        framework = None

    # 7. provider — only when the template declares providers AND a framework resolved.
    if metadata.available_providers and framework is not None:
        valid_providers = supported_providers(
            metadata.slug, framework, metadata.available_providers
        )

        if provider is None:
            provider = valid_providers[0]
        elif provider not in valid_providers:
            valid = ", ".join(valid_providers)
            raise InvalidInputError(
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
                raise InvalidInputError(
                    f"Invalid extra: '{item}'. Valid options for '{template}': {valid}"
                )
        # Build de-duplicated result preserving input order.
        seen: set[str] = set()
        validated_extras = []
        for item in input_extras:
            if item not in seen:
                validated_extras.append(item)
                seen.add(item)

    if license not in SUPPORTED_LICENSES:
        raise InvalidInputError(
            f"Invalid license: '{license}'. Valid options: mit, none"
        )

    return ProjectConfig(
        name=name,
        template=template,
        use_git=use_git,
        license=license,
        framework=framework,
        extras=validated_extras,
        cli_type=cli_type,
        data_type=data_type,
        provider=provider,
        use_uv=use_uv,
        generate_claude_md=generate_claude_md,
    )
