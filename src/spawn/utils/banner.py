from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.align import Align

from spawn.utils.console import console


LINES = [
    " ███████╗██████╗  █████╗ ██╗    ██╗███╗  ██╗",
    " ██╔════╝██╔══██╗██╔══██╗██║    ██║████╗ ██║",
    " ███████╗██████╔╝███████║██║ █╗ ██║██╔██╗██║",
    " ╚════██║██╔═══╝ ██╔══██║██║███╗██║██║╚████║",
    " ███████║██║     ██║  ██║╚███╔███╔╝██║ ╚███║",
    " ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚══╝╚══╝ ╚═╝  ╚══╝",
]

COLORS = ["#B9D6F2", "#94B8D9", "#6F9AC0", "#4A7CA7", "#2D5E8E", "#0F2D52"]


def show_banner() -> None:
    logo_lines = []
    for line_text, color in zip(LINES, COLORS):
        t = Text(line_text)
        t.stylize(f"bold {color}")
        logo_lines.append(t)

    logo_group = Group(*logo_lines)

    console.print()
    console.print(
        Align.center(
            Panel(
                logo_group,
                border_style="#2D5E8E",
                padding=(1, 4),
                expand=False,
            )
        )
    )
    console.print()