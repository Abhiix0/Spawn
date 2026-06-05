from rich.panel import Panel
from rich.table import Table

from spawn.utils.console import console


def show_success(
    project_name: str,
    template_name: str,
    use_git: bool,
) -> None:

    git_status = "[green]✓ Enabled[/green]" if use_git else "[yellow]○ Disabled[/yellow]"

    table = Table.grid(padding=(0, 2))
    table.add_row("[bold cyan]Project[/bold cyan]", project_name)
    table.add_row("[bold cyan]Template[/bold cyan]", template_name)
    table.add_row("[bold cyan]Git[/bold cyan]", git_status)
    table.add_row("[bold cyan]UV[/bold cyan]", "[green]✓ Initialized[/green]")
    table.add_row("[bold cyan]Virtual Env[/bold cyan]", "[green]✓ Created[/green]")

    console.print()

    console.print(
        Panel.fit(
            table,
            title="[bold green]✨ Project Created Successfully[/bold green]",
            border_style="green",
        )
    )

    console.print()

    console.print("[bold]Next Steps[/bold]")
    console.print(f"  [cyan]cd[/cyan] {project_name}")
    console.print("  [cyan]code .[/cyan]")
    console.print("  [cyan]git status[/cyan]")

    console.print()
    console.print("[bold green]🚀 Ready to build something awesome.[/bold green]")
    console.print()