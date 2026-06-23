import typer
from rich.text import Text

from spawn.utils.console import console
from spawn.core.models import ProjectConfig
from spawn.core.registry import list_templates, get_metadata
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
            break

        except SpawnError as e:
            typer.secho(str(e), fg=typer.colors.RED)

    # --- Template selection ---
    templates = list_templates()

    choice_map = {
        str(i): meta.slug
        for i, meta in enumerate(templates, start=1)
    }

    _print_list([meta.display_name for meta in templates])

    valid_range = len(templates)
    choice = typer.prompt(
        typer.style(f"Choose Template [1-{valid_range}]", fg=typer.colors.CYAN)
    )

    while choice not in choice_map:
        typer.secho("Invalid choice. Please select a valid number.", fg=typer.colors.RED)
        choice = typer.prompt(
            typer.style(f"Choose Template [1-{valid_range}]", fg=typer.colors.CYAN)
        )

    template = choice_map[choice]

    # --- Framework selection ---
    selected_framework: str | None = None
    meta = get_metadata(template)

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
    )
