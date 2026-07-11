import datetime
import json

import typer
from rich.prompt import Confirm, Prompt

from spawn import __version__
from spawn.cli.prompts import get_project_config
from spawn.generators.project_generator import ProjectGenerator
from spawn.github.publisher import GitHubPublisher
from spawn.github.exceptions import GitHubPublishError
from spawn.utils.banner import show_banner
from spawn.utils.success import show_success
from spawn.utils.console import console
from spawn.core.exceptions import SpawnError
from spawn.core.registry import instantiate_template

app = typer.Typer()


def _write_custom_metadata(project_path, config) -> None:
    meta_dir = project_path / ".spawn"
    meta_dir.mkdir(exist_ok=True)
    (meta_dir / "meta.json").write_text(
        json.dumps(
            {
                "intent": "custom",
                "framework": None,
                "provider": None,
                "spawn_version": __version__,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "generator": "custom",
                "git": config.use_git,
                "uv": config.use_uv,
                # detect_format() result not yet threaded through ProjectConfig;
                # "tree" is a known placeholder — tracked as follow-up for Phase 5
                "source": "tree",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


@app.command()
def create() -> None:
    show_banner()

    config = get_project_config()

    try:
        if config.template == "custom":
            from spawn.generators.custom_structure import CustomStructureGenerator
            project_path = CustomStructureGenerator().generate(
                project_name=config.name,
                entries=config.custom_entries or [],
                use_git=config.use_git,
                use_uv=config.use_uv,
            )
            _write_custom_metadata(project_path, config)
            next_steps = [
                f"cd {config.name}",
                "Start building your project",
            ]
            show_success(
                project_name=config.name,
                template_name="Custom Structure",
                use_git=config.use_git,
                next_steps=next_steps,
            )
        else:
            project_path = ProjectGenerator().generate(config)
            template_obj = instantiate_template(config)
            if template_obj is not None:
                show_success(
                    project_name=config.name,
                    template_name=template_obj.name,
                    use_git=config.use_git,
                    next_steps=template_obj.next_steps,
                )

    except SpawnError as e:
        console.print(f"[red]❌ {e}[/red]")
        return

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

    repo_url = Prompt.ask("Repository URL")

    publisher = GitHubPublisher()

    try:
        publisher.publish(project_path, repo_url)
        console.print("[green]🚀 Published successfully![/green]")

    except GitHubPublishError as e:
        console.print(f"[red]❌ {e}[/red]")


@app.command()
def version():
    """Show application version."""
    typer.echo(f"Spawn v{__version__}")


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
