import typer

from rich.panel import Panel

from spawn.cli.prompts import get_project_config
from spawn.generators.project_generator import ProjectGenerator
from spawn.utils.console import console
from spawn.core.exceptions import SpawnError

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
        generator.generate(config)

    except SpawnError as e:
        console.print(
            f"[red]❌ {e}[/red]"
        )


@app.command()
def version():
    """Show application version."""
    from spawn import __version__
    typer.echo(f"Spawn v{__version__}")


@app.command()
def doctor():
    """Check project health and best practices."""
    from spawn.utils.doctor import run_health_check
    run_health_check()


def main():
    app()


if __name__ == "__main__":
    main()