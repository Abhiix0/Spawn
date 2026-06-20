import shutil
from pathlib import Path

from spawn.templates.files import (
    README_CONTENT,
    GITIGNORE_CONTENT,
)
from spawn.core.models import ProjectConfig
from spawn.core.registry import get_template
from spawn.utils.git import initialize_git
from spawn.utils.uv import initialize_uv
from spawn.core.exceptions import SpawnError
from spawn.utils.console import console


class ProjectGenerator:
    def generate(self, config: ProjectConfig) -> Path:
        template = get_template(config.template)

        if template is None:
            raise SpawnError(
                f"Unknown template: {config.template}"
            )

        project_path = Path(config.name)

        if project_path.exists():
            raise SpawnError(
                f"Directory '{config.name}' already exists."
            )

        try:
            project_path.mkdir()

            for folder in template.folders:
                (project_path / folder).mkdir(
                    parents=True,
                    exist_ok=True,
                )

            readme_path = project_path / "README.md"

            readme_path.write_text(
                README_CONTENT.format(
                    project_name=config.name
                ),
                encoding="utf-8",
            )

            gitignore_path = project_path / ".gitignore"

            gitignore_path.write_text(
                GITIGNORE_CONTENT,
                encoding="utf-8",
            )

            for relative_path, content_template in template.starter_files:
                file_path = project_path / relative_path
                file_path.write_text(
                    content_template.format(project_name=config.name),
                    encoding="utf-8",
                )

            if config.use_git:
                console.print(
                    "[yellow]Initializing Git...[/yellow]"
                )
                initialize_git(project_path)

            initialize_uv(project_path)

        except OSError as e:
            shutil.rmtree(project_path, ignore_errors=True)
            raise SpawnError(str(e)) from e

        except BaseException:
            shutil.rmtree(project_path, ignore_errors=True)
            raise

        return project_path