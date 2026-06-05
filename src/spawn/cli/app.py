import typer
from spawn.cli.prompts import get_project_config
from spawn.generators.project_generator import ProjectGenerator

app = typer.Typer()


@app.command()
def create() -> None:
    config = get_project_config()

    generator = ProjectGenerator()
    generator.generate(config)


@app.command()
def version():
    """Show application version."""
    typer.echo("Spawn v0.1.0")


def main():
    app()


if __name__ == "__main__":
    main()