from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BaseTemplate:
    name: str
    folders: list[str]
    starter_files: list[tuple[str, str]] = field(default_factory=list)
    # Each tuple: (relative_path_string, content_template_string)

    def get_readme_content(self, context: dict) -> str | None:
        """
        Return custom README content for this template, or None to use the
        shared README. Subclasses override this to provide template-specific
        README content.
        """
        return None

    def generate(self, project_path: Path, context: dict) -> None:
        """
        Create the template's folder structure and starter files.

        project_path: the already-created root project directory (Path object)
        context: dict with at minimum {"project_name": str}

        Subclasses may override this in future phases.
        The default implementation creates folders and writes starter_files.
        """
        for folder in self.folders:
            (project_path / folder).mkdir(parents=True, exist_ok=True)

        for relative_path, content_template in self.starter_files:
            file_path = project_path / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                content_template.format_map(context),
                encoding="utf-8",
            )
