from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spawn.generators.custom_structure import ParsedEntry


@dataclass
class ProjectConfig:
    name: str
    template: str
    use_git: bool
    framework: str | None = None
    extras: list[str] = field(default_factory=list)
    cli_type: str | None = None
    data_type: str | None = None
    provider: str | None = None
    use_uv: bool = True
    generate_claude_md: bool = False
    license: str = "mit"
    custom_entries: list[ParsedEntry] | None = None  # set when template == "custom"
    custom_dependencies: list[str] = field(default_factory=list)
    custom_dev_setup: list[str] = field(default_factory=list)
    # subset of ["ruff", "pytest", "precommit", "dockerfile"]
    custom_gitignore_extra: list[str] = field(default_factory=list)
    custom_source_format: str | None = None  # "tree" | "markdown" | "indented"
    destination: Path | None = field(default=None, compare=False)

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict of this config."""
        return {
            "name": self.name,
            "template": self.template,
            "use_git": self.use_git,
            "framework": self.framework,
            "extras": list(self.extras),
            "cli_type": self.cli_type,
            "data_type": self.data_type,
            "provider": self.provider,
            "use_uv": self.use_uv,
            "generate_claude_md": self.generate_claude_md,
            "license": self.license,
            "custom_entries": (
                None
                if self.custom_entries is None
                else [
                    {"path": e.path, "is_file": e.is_file} for e in self.custom_entries
                ]
            ),
            "custom_dependencies": list(self.custom_dependencies),
            "custom_dev_setup": list(self.custom_dev_setup),
            "custom_gitignore_extra": list(self.custom_gitignore_extra),
            "custom_source_format": self.custom_source_format,
            "destination": None if self.destination is None else str(self.destination),
        }
