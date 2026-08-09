import typer
import questionary
from pathlib import Path
from rich.prompt import Confirm

from spawn.utils.console import console
from spawn.core.models import ProjectConfig
from spawn.core.registry import list_templates, get_metadata
from spawn.templates.chatbot import get_supported_providers as get_chatbot_providers
from spawn.templates.agent import get_supported_providers as get_agent_providers
from spawn.utils.validators import validate_project_name
from spawn.core.exceptions import SpawnError


# ---------------------------------------------------------------------------
# Questionary helpers
# ---------------------------------------------------------------------------

_QSTYLE = questionary.Style([
    ("qmark",       "fg:#2D5E8E bold"),
    ("question",    "bold"),
    ("pointer",     "fg:#2D5E8E bold"),
    ("highlighted", "fg:#2D5E8E bold"),
    ("selected",    "fg:#2D5E8E"),
])


def _select(message: str, choices: list[str], default: str | None = None) -> str:
    """Arrow-key single-select. Raises KeyboardInterrupt on Ctrl+C/Esc so the
    existing top-level abort handling in cli/app.py catches it uniformly."""
    answer = questionary.select(
        message, choices=choices, default=default, style=_QSTYLE
    ).ask()
    if answer is None:
        raise KeyboardInterrupt
    return answer


def _multiselect(message: str, choices: list[str]) -> list[str]:
    """Arrow-key + spacebar multi-select. Empty selection is valid (skip)."""
    answer = questionary.checkbox(
        message, choices=choices, style=_QSTYLE
    ).ask()
    if answer is None:
        raise KeyboardInterrupt
    return answer


# ---------------------------------------------------------------------------
# Custom Structure optional-setup multi-select
# ---------------------------------------------------------------------------

_OPTIONAL_SETUP_CHOICES = ["Ruff", "Pytest", "Pre-commit", "Dockerfile"]
_OPTIONAL_SETUP_KEY = {
    "Ruff":       "ruff",
    "Pytest":     "pytest",
    "Pre-commit": "precommit",
    "Dockerfile": "dockerfile",
}


def _prompt_optional_setup() -> list[str]:
    """Checkbox multi-select for optional dev tooling (Custom Structure flow)."""
    chosen = _multiselect("Optional Setup (space to toggle)", _OPTIONAL_SETUP_CHOICES)
    return [_OPTIONAL_SETUP_KEY[label] for label in chosen]


# ---------------------------------------------------------------------------
# Main interactive config builder
# ---------------------------------------------------------------------------

def get_project_config() -> ProjectConfig:
    # --- Project name ---
    while True:
        project_name = typer.prompt(
            typer.style("Project Name", fg=typer.colors.CYAN)
        )

        try:
            validate_project_name(project_name)
        except SpawnError as e:
            typer.secho(str(e), fg=typer.colors.RED)
            continue

        if Path(project_name).exists():
            typer.secho(
                f"A directory named '{project_name}' already exists. "
                "Choose a different name.",
                fg=typer.colors.RED,
            )
            continue

        break

    # --- Template selection ---
    templates = list_templates()
    display_names = [meta.display_name for meta in templates] + ["Custom Structure"]
    slug_by_display = {meta.display_name: meta.slug for meta in templates}
    slug_by_display["Custom Structure"] = "__custom_structure__"

    chosen_display = _select("Choose a template", display_names)
    chosen_slug = slug_by_display[chosen_display]

    if chosen_slug == "__custom_structure__":
        return _get_custom_structure_config(project_name)

    template = chosen_slug

    # --- Sub-selections ---
    selected_framework: str | None = None
    selected_cli_type: str | None = None
    selected_data_type: str | None = None
    selected_provider: str | None = None
    meta = get_metadata(template)

    # --- CLI type ---
    if meta and meta.available_cli_types:
        cli_types = meta.available_cli_types
        chosen = _select("Choose CLI Type", cli_types, default=cli_types[0])
        selected_cli_type = chosen

    # --- Data type ---
    if meta and meta.available_data_types:
        data_types = meta.available_data_types
        chosen = _select("Choose Project Type", data_types, default=data_types[0])
        selected_data_type = chosen

    # --- Framework ---
    if meta and meta.available_frameworks:
        frameworks = meta.available_frameworks
        chosen = _select("Choose Framework", frameworks, default=frameworks[0])
        selected_framework = chosen

    # --- Provider ---
    if meta and meta.available_providers and selected_framework:
        if meta.slug == "agent":
            provider_options = get_agent_providers(selected_framework)
        elif meta.slug == "chatbot":
            provider_options = get_chatbot_providers(selected_framework)
        else:
            provider_options = meta.available_providers
        chosen = _select("Choose Provider", provider_options, default=provider_options[0])
        selected_provider = chosen

    # --- Extras ---
    selected_extras: list[str] = []
    if meta and meta.available_extras:
        selected_extras = _multiselect(
            "Select extras (space to toggle, enter to confirm)",
            meta.available_extras,
        )

    # --- Git ---
    use_git = typer.confirm(
        typer.style("Initialize Git?", fg=typer.colors.CYAN),
        default=True,
    )
    generate_claude_md = Confirm.ask("Also generate CLAUDE.md for Claude Code?", default=False)

    return ProjectConfig(
        name=project_name,
        template=template,
        use_git=use_git,
        generate_claude_md=generate_claude_md,
        framework=selected_framework,
        extras=selected_extras,
        cli_type=selected_cli_type,
        data_type=selected_data_type,
        provider=selected_provider,
    )


def _get_custom_structure_config(project_name: str) -> ProjectConfig:
    """
    Interactive prompt for the Custom Structure path.

    Reads a pasted structure (tree, markdown, or indented format),
    previews detected folder/file counts, and collects Git/uv
    preferences, optional dependencies, optional dev tooling
    (ruff/pytest/pre-commit/dockerfile), and optional extra .gitignore
    patterns. Returns a fully populated ProjectConfig for the "custom"
    template.
    """
    import sys

    from spawn.core.exceptions import StructureParseError
    from spawn.generators.custom_structure import parse_structure, detect_format

    console.print()
    console.print(
        "[cyan]Paste your project structure.[/cyan]\n"
        "[dim]Supported formats: Tree (├──/└──), Markdown list (- item), "
        "Indented hierarchy[/dim]\n"
        "[dim]Finish with Ctrl+D (Ctrl+Z then Enter on Windows)[/dim]"
    )

    raw = sys.stdin.read()
    detected_format = detect_format(raw)

    try:
        entries = parse_structure(raw)
    except StructureParseError as e:
        typer.secho(str(e), fg=typer.colors.RED)
        raise SpawnError("Could not parse structure.") from e

    folders = [e for e in entries if not e.is_file]
    files   = [e for e in entries if e.is_file]

    console.print()
    console.print("[bold]Detected[/bold]")
    console.print(f"Folders : {len(folders)}")
    console.print(f"Files   : {len(files)}")
    console.print()

    use_git = typer.confirm(
        typer.style("Initialize Git?", fg=typer.colors.CYAN), default=True
    )
    generate_claude_md = Confirm.ask("Also generate CLAUDE.md for Claude Code?", default=False)
    use_uv = typer.confirm(
        typer.style("Initialize uv?", fg=typer.colors.CYAN), default=True
    )
    custom_dependencies: list[str] = []
    if use_uv:
        deps_raw = typer.prompt(
            typer.style(
                "Dependencies (comma separated, optional)",
                fg=typer.colors.CYAN,
            ),
            default="",
            show_default=False,
        )
        if deps_raw.strip():
            custom_dependencies = [
                d.strip() for d in deps_raw.split(",") if d.strip()
            ]
    custom_dev_setup = _prompt_optional_setup() if use_uv else []
    console.print()
    extra_ignores_raw = typer.prompt(
        typer.style(
            "Additional ignore patterns (optional, comma separated)",
            fg=typer.colors.CYAN,
        ),
        default="",
        show_default=False,
    )
    custom_gitignore_extra = [
        p.strip() for p in extra_ignores_raw.split(",") if p.strip()
    ]
    proceed = typer.confirm(
        typer.style("Proceed?", fg=typer.colors.CYAN), default=True
    )

    if not proceed:
        raise SpawnError("Cancelled.")

    return ProjectConfig(
        name=project_name,
        template="custom",
        use_git=use_git,
        generate_claude_md=generate_claude_md,
        use_uv=use_uv,
        custom_entries=entries,
        custom_dependencies=custom_dependencies,
        custom_dev_setup=custom_dev_setup,
        custom_gitignore_extra=custom_gitignore_extra,
        custom_source_format=detected_format,
    )
