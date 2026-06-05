import typer

app = typer.Typer()


@app.command()
def create():
    """Create a new project."""
    typer.echo("Project creation coming soon...")


@app.command()
def version():
    """Show application version."""
    typer.echo("DevBootstrap v0.1.0")


def main():
    app()


if __name__ == "__main__":
    main()