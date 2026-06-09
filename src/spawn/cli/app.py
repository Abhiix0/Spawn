import typer

from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from spawn.cli.prompts import get_project_config
from spawn.generators.project_generator import ProjectGenerator
from spawn.github.publisher import GitHubPublisher
from spawn.github.exceptions import GitHubPublishError
from spawn.utils.success import show_success
from spawn.utils.console import console
from spawn.core.exceptions import SpawnError
from spawn.core.registry import get_template

app = typer.Typer()


@app.command()
def create() -> None:
    console.print(
        Panel.fit(
            "Create development environments in seconds",
            title="🚀 Spawn",
        )
    )

    config = get_project_config()

    generator = ProjectGenerator()

    try:
        project_path = generator.generate(
            config
        )

    except SpawnError as e:
        console.print(
            f"[red]❌ {e}[/red]"
        )
        return

    template = get_template(
        config.template
    )

    if template is not None:
        show_success(
            project_name=config.name,
            template_name=template.name,
            use_git=config.use_git,
            template=config.template,
        )

    if not config.use_git:
        console.print(
            "\n[yellow]ℹ GitHub publishing requires Git. Skipping.[/yellow]"
        )
        return

    publish_to_github = Confirm.ask(
        "\nPublish to GitHub?",
        default=False,
    )

    if not publish_to_github:
        return

    repo_url = Prompt.ask(
        "Repository URL"
    )

    publisher = GitHubPublisher()

    try:
        publisher.publish(
            project_path,
            repo_url,
        )

        console.print(
            "[green]🚀 Published successfully![/green]"
        )

    except GitHubPublishError as e:
        console.print(
            f"[red]❌ {e}[/red]"
        )


@app.command()
def version():
    """Show application version."""
    from spawn import __version__

    typer.echo(
        f"Spawn v{__version__}"
    )


@app.command()
def doctor():
    """Check project health and best practices."""
    from spawn.utils.doctor import (
        run_health_check,
    )

    run_health_check()


def main():
    app()


if __name__ == "__main__":
    main()