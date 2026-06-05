import typer
from devbootstrap.cli.prompts import get_project_config
from devbootstrap.generators.project_generator import ProjectGenerator

app = typer.Typer()


@app.command()
def create() -> None:
    config = get_project_config()

    generator = ProjectGenerator()
    generator.generate(config)


@app.command()
def version():
    """Show application version."""
    typer.echo("DevBootstrap v0.1.0")


def main():
    app()


if __name__ == "__main__":
    main()