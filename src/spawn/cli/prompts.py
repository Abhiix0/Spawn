import typer
from rich.table import Table

from spawn.utils.console import console
from spawn.core.models import ProjectConfig
from spawn.core.registry import list_templates, get_metadata
from spawn.utils.validators import validate_project_name
from spawn.core.exceptions import SpawnError


def get_project_config() -> ProjectConfig:
    while True:
        project_name = typer.prompt("Project Name")

        try:
            validate_project_name(project_name)
            break

        except SpawnError as e:
            typer.secho(
                str(e),
                fg=typer.colors.RED,
            )

    templates = list_templates()

    choice_map = {
        str(i): meta.slug
        for i, meta in enumerate(templates, start=1)
    }

    table = Table(title="Available Templates")

    table.add_column("#", justify="center")
    table.add_column("Template")
    table.add_column("Description")

    for i, meta in enumerate(templates, start=1):
        table.add_row(str(i), meta.display_name, meta.description)

    console.print(table)

    valid_range = len(templates)
    choice = typer.prompt(f"Choose Template [1-{valid_range}]")

    while choice not in choice_map:
        typer.secho(
            "Invalid choice. Please select a valid number.",
            fg=typer.colors.RED,
        )
        choice = typer.prompt(f"Choose Template [1-{valid_range}]")

    template = choice_map[choice]

    # --- Framework selection (only for templates that declare frameworks) ---
    selected_framework: str | None = None
    meta = get_metadata(template)

    if meta and meta.available_frameworks:
        frameworks = meta.available_frameworks
        framework_map = {
            str(i): fw
            for i, fw in enumerate(frameworks, start=1)
        }

        fw_table = Table(title="Available Frameworks")
        fw_table.add_column("#", justify="center")
        fw_table.add_column("Framework")

        for i, fw in enumerate(frameworks, start=1):
            fw_table.add_row(str(i), fw)

        console.print(fw_table)

        valid_fw_range = len(frameworks)
        fw_choice = typer.prompt(
            f"Choose Framework [1-{valid_fw_range}]",
            default="1",
        )

        while fw_choice not in framework_map:
            typer.secho(
                "Invalid choice. Please select a valid number.",
                fg=typer.colors.RED,
            )
            fw_choice = typer.prompt(
                f"Choose Framework [1-{valid_fw_range}]",
                default="1",
            )

        selected_framework = framework_map[fw_choice]

    # -----------------------------------------------------------------------

    use_git = typer.confirm(
        "Initialize Git?",
        default=True,
    )

    return ProjectConfig(
        name=project_name,
        template=template,
        use_git=use_git,
        framework=selected_framework,
    )
