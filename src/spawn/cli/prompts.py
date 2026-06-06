import typer
from rich.table import Table

from spawn.utils.console import console
from spawn.core.models import ProjectConfig
from spawn.utils.validators import validate_project_name
from spawn.core.exceptions import SpawnError


TEMPLATE_CHOICES = {
    "1": "python",
    "2": "fastapi",
    "3": "data-science",
    "4": "ml",
}


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

    table = Table(title="Available Templates")

    table.add_column("#", justify="center")
    table.add_column("Template")

    table.add_row("1", "Python Script")
    table.add_row("2", "FastAPI")
    table.add_row("3", "Data Science")
    table.add_row("4", "ML Project")

    console.print(table)

    choice = typer.prompt("Choose Template [1-4]")

    while choice not in TEMPLATE_CHOICES:
        typer.secho(
            "Invalid choice. Please select a valid number.",
            fg=typer.colors.RED,
        )
        choice = typer.prompt("Choose Template [1-4]")

    template = TEMPLATE_CHOICES[choice]

    use_git = typer.confirm(
        "Initialize Git?",
        default=True,
    )

    return ProjectConfig(
        name=project_name,
        template=template,
        use_git=use_git,
    )