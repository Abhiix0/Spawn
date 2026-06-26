from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.cli_application.content import (
    INIT_CONTENT,
    TYPER_MAIN_CONTENT,
    TYPER_COMMANDS_INIT_CONTENT,
    TYPER_UTILS_INIT_CONTENT,
    TYPER_TEST_CONTENT,
    TYPER_README_CONTENT,
    CLICK_MAIN_CONTENT,
    CLICK_TEST_CONTENT,
    CLICK_README_CONTENT,
    ARGPARSE_MAIN_CONTENT,
    ARGPARSE_TEST_CONTENT,
    ARGPARSE_README_CONTENT,
)

# ---------------------------------------------------------------------------
# Folder structure (identical for all frameworks)
# ---------------------------------------------------------------------------

UTILITY_FOLDERS = [
    "src/commands",
    "src/utils",
    "tests",
]

# ---------------------------------------------------------------------------
# Starter file lists
# ---------------------------------------------------------------------------

TYPER_UTILITY_FILES = [
    ("src/__init__.py", INIT_CONTENT),
    ("src/commands/__init__.py", TYPER_COMMANDS_INIT_CONTENT),
    ("src/utils/__init__.py", TYPER_UTILS_INIT_CONTENT),
    ("src/main.py", TYPER_MAIN_CONTENT),
    ("tests/__init__.py", INIT_CONTENT),
    ("tests/test_cli.py", TYPER_TEST_CONTENT),
]

CLICK_UTILITY_FILES = [
    ("src/__init__.py", INIT_CONTENT),
    ("src/commands/__init__.py", INIT_CONTENT),
    ("src/utils/__init__.py", INIT_CONTENT),
    ("src/main.py", CLICK_MAIN_CONTENT),
    ("tests/__init__.py", INIT_CONTENT),
    ("tests/test_cli.py", CLICK_TEST_CONTENT),
]

ARGPARSE_UTILITY_FILES = [
    ("src/__init__.py", INIT_CONTENT),
    ("src/commands/__init__.py", INIT_CONTENT),
    ("src/utils/__init__.py", INIT_CONTENT),
    ("src/main.py", ARGPARSE_MAIN_CONTENT),
    ("tests/__init__.py", INIT_CONTENT),
    ("tests/test_cli.py", ARGPARSE_TEST_CONTENT),
]


class CLITemplate(BaseTemplate):
    def __init__(
        self,
        framework: str | None = None,
        extras: list[str] | None = None,
    ) -> None:
        self.framework = framework or "typer"
        self.extras = extras or []

        if self.framework == "click":
            folders = list(UTILITY_FOLDERS)
            starter_files = list(CLICK_UTILITY_FILES)
        elif self.framework == "argparse":
            folders = list(UTILITY_FOLDERS)
            starter_files = list(ARGPARSE_UTILITY_FILES)
        else:
            folders = list(UTILITY_FOLDERS)
            starter_files = list(TYPER_UTILITY_FILES)

        super().__init__(
            name="CLI Application",
            folders=folders,
            starter_files=starter_files,
            next_steps=[
                "cd {project_name}",
                "uv run python -m src.main hello",
            ],
        )

    def get_readme_content(self, context: dict) -> str | None:
        if self.framework == "click":
            return CLICK_README_CONTENT.format_map(context)
        if self.framework == "argparse":
            return ARGPARSE_README_CONTENT.format_map(context)
        return TYPER_README_CONTENT.format_map(context)

    def get_dependencies(self) -> list[str]:
        if self.framework == "click":
            return ["click"]
        if self.framework == "argparse":
            return []
        return ["typer"]

    def post_install(self, project_path: Path) -> None:
        pass
