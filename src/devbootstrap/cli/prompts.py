import typer

from devbootstrap.core.models import ProjectConfig


def get_project_config() -> ProjectConfig:
    project_name = typer.prompt("Project Name")

    template = typer.prompt(
        "Template (python, fastapi, data-science, ml)"
    )

    use_git = typer.confirm(
        "Initialize Git?",
        default=True,
    )

    return ProjectConfig(
        name=project_name,
        template=template,
        use_git=use_git,
    )