import typer

from spawn.core.models import ProjectConfig


def get_project_config() -> ProjectConfig:
    project_name = typer.prompt("Project Name")

    TEMPLATE_CHOICES = {
    "1": "python",
    "2": "fastapi",
    "3": "data-science",
    "4": "ml",
    }
    menu = "\n".join([f" [{k}] {v}" for k, v in TEMPLATE_CHOICES.items()])
    print(f"\nAvailable Templates:\n{menu}\n")

    choice = typer.prompt("Choose template")

    while choice not in TEMPLATE_CHOICES:
        typer.secho(" Invalid choice. Please select a valid number.", fg=typer.colors.RED)
        choice = typer.prompt("Choose template")

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