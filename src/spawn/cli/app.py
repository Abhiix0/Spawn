import typer

from rich.prompt import Confirm, Prompt

from spawn.cli.prompts import get_project_config
from spawn.generators.project_generator import ProjectGenerator
from spawn.github.publisher import GitHubPublisher
from spawn.github.exceptions import GitHubPublishError
from spawn.utils.banner import show_banner
from spawn.utils.success import show_success
from spawn.utils.console import console
from spawn.core.exceptions import SpawnError
from spawn.core.registry import get_template, instantiate_template

app = typer.Typer()


@app.command()
def create() -> None:
    show_banner()

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

    template_obj = instantiate_template(config)

    if template_obj is not None:
        show_success(
            project_name=config.name,
            template_name=template_obj.name,
            use_git=config.use_git,
            next_steps=template_obj.next_steps,
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
def doctor(
    path: str = typer.Argument(
        default=".",
        help="Path to the project directory to check. Defaults to current directory.",
    )
) -> None:
    """Check the health of a project directory."""
    from pathlib import Path

    from spawn.utils.doctor import run_health_check

    project_path = Path(path).resolve()
    if not project_path.exists():
        console.print(f"[red]❌ Path does not exist: {project_path}[/red]")
        raise typer.Exit(1)
    if not project_path.is_dir():
        console.print(f"[red]❌ Path is not a directory: {project_path}[/red]")
        raise typer.Exit(1)
    run_health_check(project_path)


def main():
    app()


if __name__ == "__main__":
    main()