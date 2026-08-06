import datetime
import json
from pathlib import Path

import typer
from rich.prompt import Confirm, Prompt

from spawn import __version__
from spawn.cli.noninteractive import build_config_from_args, build_config_from_file
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
                "source": config.custom_source_format or "tree",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


@app.command()
def create(
    name: str = typer.Option(None, "--name", help="Project name (enables non-interactive mode)"),
    template: str = typer.Option(None, "--template", help="Template slug: backend-api, cli, automation, chatbot, agent, rag, data"),
    framework: str = typer.Option(None, "--framework", help="Framework choice for templates that support it"),
    provider: str = typer.Option(None, "--provider", help="AI provider choice for chatbot/agent templates"),
    cli_type: str = typer.Option(None, "--cli-type", help="CLI type for the cli template: utility or interactive"),
    data_type: str = typer.Option(None, "--data-type", help="Project type for the data template"),
    extras: str = typer.Option(None, "--extras", help="Comma-separated list of extras, e.g. ruff,pytest"),
    git: bool = typer.Option(True, "--git/--no-git", help="Initialize a Git repository"),
    uv: bool = typer.Option(True, "--uv/--no-uv", help="Initialize a uv environment and install dependencies"),
    claude_md: bool = typer.Option(False, "--claude-md/--no-claude-md", help="Also generate CLAUDE.md alongside AGENTS.md"),
    config_file: str = typer.Option(None, "--config", help="Path to a JSON config file (overrides other flags)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the GitHub publish prompt"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and print the resolved config without creating a project"),
) -> None:
    non_interactive = config_file is not None or name is not None

    if non_interactive:
        try:
            if config_file is not None:
                config = build_config_from_file(Path(config_file), use_claude_md=claude_md)
            else:
                if template is None:
                    raise SpawnError("--template is required when using --name without --config.")
                extras_list = [e.strip() for e in extras.split(",") if e.strip()] if extras else []
                config = build_config_from_args(
                    name=name,
                    template=template,
                    framework=framework,
                    provider=provider,
                    cli_type=cli_type,
                    data_type=data_type,
                    extras=extras_list,
                    use_git=git,
                    use_uv=uv,
                    use_claude_md=claude_md,
                )
        except SpawnError as e:
            console.print(f"[red]❌ {e}[/red]")
            raise typer.Exit(1)

        if dry_run:
            console.print("[green]✓ Config valid[/green]")
            console.print(config)
            return
    else:
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
                dependencies=config.custom_dependencies,
                dev_setup=config.custom_dev_setup,
                gitignore_extra=config.custom_gitignore_extra,
                generate_claude_md=config.generate_claude_md,
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

    if non_interactive or yes:
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
