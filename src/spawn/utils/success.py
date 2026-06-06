from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from spawn.utils.console import console
from spawn.utils.next_steps import show_next_steps


def show_success(
    project_name: str,
    template_name: str,
    use_git: bool,
    template: str,
) -> None:

    git_status = "[green]✓ Enabled[/green]" if use_git else "[yellow]○ Disabled[/yellow]"

    table = Table.grid(padding=(0, 2))
    table.add_row("[bold cyan]Project[/bold cyan]", project_name)
    table.add_row("[bold cyan]Template[/bold cyan]", template_name)
    table.add_row("[bold cyan]Git[/bold cyan]", git_status)
    table.add_row("[bold cyan]UV[/bold cyan]", "[green]✓ Initialized[/green]")
    table.add_row("[bold cyan]Virtual Env[/bold cyan]", "[green]✓ Created[/green]")

    next_steps_content = show_next_steps(project_name, template)

    next_steps_text = Text()
    next_steps_text.append("\n Next Steps\n", style="bold cyan")
    for line in next_steps_content.splitlines():
        next_steps_text.append(f"  {line}\n")

    combined = Group(table, next_steps_text)

    console.print()

    console.print(
        Panel.fit(
            combined,
            title="[bold green]✨ Project Created Successfully[/bold green]",
            border_style="green",
        )
    )
