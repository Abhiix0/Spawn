"""Shared color palette for Spawn's CLI output.

All Rich/Typer styling across the CLI should import from here
instead of hardcoding color names, so the brand gradient introduced
in banner.py is consistent everywhere.
"""

# Raw gradient (matches banner.py exactly — do not diverge)
SPAWN_LIGHT = "#B9D6F2"
SPAWN_LIGHT_MID = "#94B8D9"
SPAWN_MID = "#6F9AC0"
SPAWN_MID_DARK = "#4A7CA7"
SPAWN_DARK = "#2D5E8E"
SPAWN_DARKEST = "#0F2D52"

# Semantic aliases — use these in application code
PROMPT_COLOR = SPAWN_LIGHT_MID  # interactive prompts (was typer.colors.CYAN)
BORDER_COLOR = SPAWN_DARK  # panel borders (matches banner border)
ACCENT_COLOR = SPAWN_MID  # spinners, in-progress status text
SUCCESS_COLOR = "green"  # unchanged — success stays green, not blue
WARNING_COLOR = "yellow"  # unchanged
ERROR_COLOR = "red"  # unchanged

# Prompt prefix glyph (see Phase 3)
PROMPT_GLYPH = "▸"
