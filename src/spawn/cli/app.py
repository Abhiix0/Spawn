from pathlib import Path

import typer
from rich.prompt import Confirm, Prompt

from spawn import __version__
from spawn.cli.noninteractive import build_config_from_args, build_config_from_file
from spawn.cli.prompts import get_project_config
from spawn.core.exceptions import SpawnError
from spawn.core.registry import instantiate_template
from spawn.generators.pipeline import generate_project
from spawn.github.exceptions import GitHubPublishError
from spawn.github.publisher import GitHubPublisher
from spawn.utils.banner import show_banner
from spawn.utils.console import console
from spawn.utils.success import show_success

app = typer.Typer()


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return

    show_banner()
    console.print(f"[dim]v{__version__}[/dim]\n")
    console.print("[bold]Commands[/bold]")
    console.print("  [cyan]create[/cyan]    Scaffold a new project")
    console.print("  [cyan]doctor[/cyan]    Check the health of a project directory")
    console.print("  [cyan]version[/cyan]   Show the installed version")
    console.print(
        "\n[dim]Run [cyan]spawn COMMAND --help[/cyan] for details on a command.[/dim]\n"
    )


def _display_info(config) -> tuple[str, list[str]] | None:
    if config.template == "custom":
        return "Custom Structure", [f"cd {config.name}", "Start building your project"]
    template_obj = instantiate_template(config)
    if template_obj is None:
        return None
    return template_obj.name, template_obj.next_steps


@app.command()
def create(
    name: str = typer.Option(
        None, "--name", help="Project name (enables non-interactive mode)"
    ),
    template: str = typer.Option(
        None,
        "--template",
        help="Template slug: backend-api, cli, automation, chatbot, agent, rag, data, mcp",
    ),
    framework: str = typer.Option(
        None, "--framework", help="Framework choice for templates that support it"
    ),
    provider: str = typer.Option(
        None, "--provider", help="AI provider choice for chatbot/agent templates"
    ),
    cli_type: str = typer.Option(
        None, "--cli-type", help="CLI type for the cli template: utility or interactive"
    ),
    data_type: str = typer.Option(
        None, "--data-type", help="Project type for the data template"
    ),
    extras: str = typer.Option(
        None, "--extras", help="Comma-separated list of extras, e.g. ruff,pytest"
    ),
    git: bool = typer.Option(
        True, "--git/--no-git", help="Initialize a Git repository"
    ),
    uv: bool = typer.Option(
        True,
        "--uv/--no-uv",
        help="Initialize a uv environment and install dependencies",
    ),
    claude_md: bool = typer.Option(
        False,
        "--claude-md/--no-claude-md",
        help="Also generate CLAUDE.md alongside AGENTS.md",
    ),
    license_kind: str = typer.Option(
        "mit",
        "--license",
        help="License for the new project: mit or none",
    ),
    config_file: str = typer.Option(
        None, "--config", help="Path to a JSON config file (overrides other flags)"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip the GitHub publish prompt"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate and print the resolved config without creating a project",
    ),
) -> None:
    try:
        non_interactive = config_file is not None or name is not None

        if non_interactive:
            try:
                if config_file is not None:
                    config = build_config_from_file(
                        Path(config_file),
                        use_claude_md=claude_md,
                        license_kind=license_kind,
                    )
                else:
                    if template is None:
                        raise SpawnError(
                            "--template is required when using --name without --config."
                        )
                    extras_list = (
                        [e.strip() for e in extras.split(",") if e.strip()]
                        if extras
                        else []
                    )
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
                        license=license_kind,
                    )

            except SpawnError as e:
                console.print(f"[red]❌ {e}[/red]")
                raise typer.Exit(1)

            if dry_run:
                console.print("[green]✓ Config valid[/green]")
                console.print(config)
                return
        else:
            config = get_project_config()

        try:
            project_path = generate_project(config)
            info = _display_info(config)
            if info is not None:
                template_name, next_steps = info
                show_success(
                    project_name=config.name,
                    template_name=template_name,
                    use_git=config.use_git,
                    next_steps=next_steps,
                    use_uv=config.use_uv,
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
    except (KeyboardInterrupt, EOFError, typer.Abort):
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(130)


@app.command()
def version():
    """Show application version."""
    typer.echo(f"Spawn v{__version__}")


@app.command()
def doctor(
    path: str = typer.Argument(
        default=".",
        help="Path to the project directory to check. Defaults to current directory.",
    ),
    fix: bool = typer.Option(
        False,
        "--fix",
        help="Create missing files and config. Never overwrites, never installs packages",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="With --fix: show what would change without writing",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="With --fix: skip the confirmation prompt",
    ),
    license_kind: str = typer.Option(
        None,
        "--license",
        help="With --fix: also add a LICENSE (mit)",
    ),
) -> None:
    """Check the health of a project directory."""
    try:
        if not fix:
            if dry_run:
                console.print("[red]❌ --dry-run requires --fix.[/red]")
                raise typer.Exit(1)
            if yes:
                console.print("[red]❌ --yes requires --fix.[/red]")
                raise typer.Exit(1)
            if license_kind is not None:
                console.print("[red]❌ --license requires --fix.[/red]")
                raise typer.Exit(1)

        if license_kind is not None and license_kind != "mit":
            console.print(
                f"[red]❌ Unsupported license: '{license_kind}'. Valid options: mit[/red]"
            )
            raise typer.Exit(1)

        project_path = Path(path).resolve()
        if not project_path.exists():
            console.print(f"[red]❌ Path does not exist: {project_path}[/red]")
            raise typer.Exit(1)
        if not project_path.is_dir():
            console.print(f"[red]❌ Path is not a directory: {project_path}[/red]")
            raise typer.Exit(1)

        from spawn.utils.doctor import ProjectHealthChecker, run_health_check

        if not fix:
            run_health_check(project_path)
            return

        from spawn.utils.doctor_fix import apply_fixes, plan_fixes, tool_hints

        checker = ProjectHealthChecker(project_path)
        checks = checker.run_all_checks()
        checker.format_report(checks)

        actions, manual = plan_fixes(project_path, checks, license_kind=license_kind)

        if not actions and not manual:
            console.print("[green]✓ Nothing to fix.[/green]")
            return

        if actions:
            console.print("[bold]Planned fixes:[/bold]")
            for a in actions:
                console.print(f"  • {a.description}")

        if manual:
            if actions:
                console.print()
            console.print("[bold]Needs manual action:[/bold]")
            for check_name, reason in manual:
                console.print(f"  • {check_name}: {reason}")

        if dry_run:
            return

        if not actions:
            return

        if not yes and not typer.confirm(f"Apply {len(actions)} fixes?", default=True):
            console.print("[yellow]Cancelled.[/yellow]")
            return

        score_before, max_before = checker.calculate_score(checks)
        pct_before = int((score_before / max_before * 100) if max_before > 0 else 0)

        results = apply_fixes(actions)
        console.print()
        for r in results:
            if r.status == "applied":
                console.print(f"[green]✓[/green] {r.action.description}")
            elif r.status == "skipped":
                detail_msg = f" ({r.detail})" if r.detail else ""
                console.print(f"[yellow]○[/yellow] {r.action.description}{detail_msg}")
            else:
                console.print(f"[red]✗[/red] {r.action.description}: {r.detail}")

        hints = tool_hints(results)
        if hints:
            console.print()
            for hint in hints:
                console.print(hint)

        new_checks = checker.run_all_checks()
        score_after, max_after = checker.calculate_score(new_checks)
        pct_after = int((score_after / max_after * 100) if max_after > 0 else 0)
        console.print(f"\n[bold]Score: {pct_before}% → {pct_after}%[/bold]")

    except (KeyboardInterrupt, EOFError, typer.Abort):
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(130)


def main():
    try:
        app()
    except (KeyboardInterrupt, EOFError, typer.Abort):
        console.print("\n[yellow]Cancelled.[/yellow]")
        raise typer.Exit(130)


if __name__ == "__main__":
    main()
