import typer

from devbootstrap.core.models import ProjectConfig


def get_project_config() -> ProjectConfig:
    project_name = typer.prompt("Project Name")

    return ProjectConfig(
        name=project_name,
        template="python",
        use_git=True,
    )