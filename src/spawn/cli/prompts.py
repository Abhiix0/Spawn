import typer
from pathlib import Path
from rich.text import Text

from spawn.utils.console import console
from spawn.core.models import ProjectConfig
from spawn.core.registry import list_templates, get_metadata
from spawn.templates.chatbot import get_supported_providers as get_chatbot_providers
from spawn.templates.agent import get_supported_providers as get_agent_providers
from spawn.utils.validators import validate_project_name
from spawn.core.exceptions import SpawnError


def _print_list(items: list[str]) -> None:
    """Print a numbered list with dim numbers and bright item names."""
    console.print()
    for i, item in enumerate(items, start=1):
        line = Text()
        line.append(f"  {i}  ", style="dim")
        line.append(item, style="bold white")
        console.print(line)
    console.print()


def get_project_config() -> ProjectConfig:
    # --- Project name ---
    while True:
        project_name = typer.prompt(
            typer.style("Project Name", fg=typer.colors.CYAN)
        )

        try:
            validate_project_name(project_name)
        except SpawnError as e:
            typer.secho(str(e), fg=typer.colors.RED)
            continue

        if Path(project_name).exists():
            typer.secho(
                f"A directory named '{project_name}' already exists. "
                "Choose a different name.",
                fg=typer.colors.RED,
            )
            continue

        break

    # --- Template selection ---
    templates = list_templates()

    # registry templates in order, then the sentinel for Custom Structure
    choice_map = {
        str(i): meta.slug
        for i, meta in enumerate(templates, start=1)
    }
    custom_index = str(len(templates) + 1)
    choice_map[custom_index] = "__custom_structure__"

    display_names = [meta.display_name for meta in templates] + ["Custom Structure"]
    _print_list(display_names)

    valid_range = len(display_names)
    choice = typer.prompt(
        typer.style(f"Choose Template [1-{valid_range}]", fg=typer.colors.CYAN)
    )

    while choice not in choice_map:
        typer.secho("Invalid choice. Please select a valid number.", fg=typer.colors.RED)
        choice = typer.prompt(
            typer.style(f"Choose Template [1-{valid_range}]", fg=typer.colors.CYAN)
        )

    if choice_map[choice] == "__custom_structure__":
        return _get_custom_structure_config(project_name)

    template = choice_map[choice]

    # --- Framework selection ---
    selected_framework: str | None = None
    selected_cli_type: str | None = None
    selected_data_type: str | None = None
    selected_provider: str | None = None
    meta = get_metadata(template)

    # --- CLI type selection ---
    if meta and meta.available_cli_types:
        cli_types = meta.available_cli_types
        cli_type_map = {
            str(i): ct
            for i, ct in enumerate(cli_types, start=1)
        }

        _print_list(cli_types)

        valid_ct_range = len(cli_types)
        ct_choice = typer.prompt(
            typer.style(
                f"Choose CLI Type [1-{valid_ct_range}]",
                fg=typer.colors.CYAN,
            ),
            default="1",
        )

        while ct_choice not in cli_type_map:
            typer.secho(
                "Invalid choice. Please select a valid number.",
                fg=typer.colors.RED,
            )
            ct_choice = typer.prompt(
                typer.style(
                    f"Choose CLI Type [1-{valid_ct_range}]",
                    fg=typer.colors.CYAN,
                ),
                default="1",
            )

        selected_cli_type = cli_type_map[ct_choice]

    # --- Data type selection ---
    if meta and meta.available_data_types:
        data_types = meta.available_data_types
        data_type_map = {
            str(i): dt
            for i, dt in enumerate(data_types, start=1)
        }

        _print_list(data_types)

        valid_dt_range = len(data_types)
        dt_choice = typer.prompt(
            typer.style(
                f"Choose Project Type [1-{valid_dt_range}]",
                fg=typer.colors.CYAN,
            ),
            default="1",
        )

        while dt_choice not in data_type_map:
            typer.secho(
                "Invalid choice. Please select a valid number.",
                fg=typer.colors.RED,
            )
            dt_choice = typer.prompt(
                typer.style(
                    f"Choose Project Type [1-{valid_dt_range}]",
                    fg=typer.colors.CYAN,
                ),
                default="1",
            )

        selected_data_type = data_type_map[dt_choice]

    # --- Framework selection ---
    if meta and meta.available_frameworks:
        frameworks = meta.available_frameworks
        framework_map = {
            str(i): fw
            for i, fw in enumerate(frameworks, start=1)
        }

        _print_list(frameworks)

        valid_fw_range = len(frameworks)
        fw_choice = typer.prompt(
            typer.style(f"Choose Framework [1-{valid_fw_range}]", fg=typer.colors.CYAN),
            default="1",
        )

        while fw_choice not in framework_map:
            typer.secho("Invalid choice. Please select a valid number.", fg=typer.colors.RED)
            fw_choice = typer.prompt(
                typer.style(f"Choose Framework [1-{valid_fw_range}]", fg=typer.colors.CYAN),
                default="1",
            )

        selected_framework = framework_map[fw_choice]

    # --- Provider selection ---
    if meta and meta.available_providers and selected_framework:
        if meta.slug == "agent":
            provider_options = get_agent_providers(selected_framework)
        elif meta.slug == "chatbot":
            provider_options = get_chatbot_providers(selected_framework)
        else:
            provider_options = meta.available_providers
        provider_choice_map = {
            str(i): p for i, p in enumerate(provider_options, start=1)
        }

        _print_list(provider_options)

        valid_prov_range = len(provider_options)
        prov_choice = typer.prompt(
            typer.style(
                f"Choose Provider [1-{valid_prov_range}]",
                fg=typer.colors.CYAN,
            ),
            default="1",
        )

        while prov_choice not in provider_choice_map:
            typer.secho(
                "Invalid choice. Please select a valid number.",
                fg=typer.colors.RED,
            )
            prov_choice = typer.prompt(
                typer.style(
                    f"Choose Provider [1-{valid_prov_range}]",
                    fg=typer.colors.CYAN,
                ),
                default="1",
            )

        selected_provider = provider_choice_map[prov_choice]

    # --- Extras selection ---
    selected_extras: list[str] = []

    if meta and meta.available_extras:
        extras = meta.available_extras
        extras_map = {
            str(i): slug
            for i, slug in enumerate(extras, start=1)
        }

        _print_list(extras)

        typer.secho(
            "  Enter numbers separated by commas, or press Enter to skip",
            fg=typer.colors.CYAN,
        )

        raw = typer.prompt(
            typer.style("Extras", fg=typer.colors.CYAN),
            default="",
        )

        parsed: list[str] = []
        seen: set[str] = set()
        for token in raw.split(","):
            token = token.strip()
            if token in extras_map and token not in seen:
                parsed.append(extras_map[token])
                seen.add(token)

        selected_extras = parsed

    # --- Git ---
    use_git = typer.confirm(
        typer.style("Initialize Git?", fg=typer.colors.CYAN),
        default=True,
    )

    return ProjectConfig(
        name=project_name,
        template=template,
        use_git=use_git,
        framework=selected_framework,
        extras=selected_extras,
        cli_type=selected_cli_type,
        data_type=selected_data_type,
        provider=selected_provider,
    )

def _get_custom_structure_config(project_name: str) -> ProjectConfig:
    """
    Interactive prompt for the Custom Structure path.

    Reads a pasted structure, previews detected folders/files, confirms
    Git/uv preferences, then raises SpawnError until Phase 4 wires in
    the required ProjectConfig fields.
    """
    import sys

    from spawn.core.exceptions import StructureParseError
    from spawn.generators.custom_structure import parse_structure

    console.print()
    console.print(
        "[cyan]Paste your project structure.[/cyan]\n"
        "[dim]Supported formats: Tree (├──/└──), Markdown list (- item), "
        "Indented hierarchy[/dim]\n"
        "[dim]Finish with Ctrl+D (Ctrl+Z then Enter on Windows)[/dim]"
    )

    raw = sys.stdin.read()

    try:
        entries = parse_structure(raw)
    except StructureParseError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise SpawnError("Could not parse structure.") from e

    folders = [e for e in entries if not e.is_file]
    files   = [e for e in entries if e.is_file]

    console.print()
    console.print("[bold]Detected[/bold]")
    console.print(f"Folders : {len(folders)}")
    console.print(f"Files   : {len(files)}")
    console.print()

    use_git = typer.confirm(
        typer.style("Initialize Git?", fg=typer.colors.CYAN), default=True
    )
    use_uv = typer.confirm(
        typer.style("Initialize uv?", fg=typer.colors.CYAN), default=True
    )
    custom_dependencies: list[str] = []
    if use_uv:
        deps_raw = typer.prompt(
            typer.style(
                "Dependencies (comma separated, optional)",
                fg=typer.colors.CYAN,
            ),
            default="",
            show_default=False,
        )
        if deps_raw.strip():
            custom_dependencies = [
                d.strip() for d in deps_raw.split(",") if d.strip()
            ]
    proceed = typer.confirm(
        typer.style("Proceed?", fg=typer.colors.CYAN), default=True
    )

    if not proceed:
        raise SpawnError("Cancelled.")

    return ProjectConfig(
        name=project_name,
        template="custom",
        use_git=use_git,
        use_uv=use_uv,
        custom_entries=entries,
        custom_dependencies=custom_dependencies,
    )
