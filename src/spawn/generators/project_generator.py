import json
import shutil
from pathlib import Path

from spawn import __version__
from spawn.templates.shared_content import (
    README_CONTENT,
    GITIGNORE_CONTENT,
)
from spawn.core.models import ProjectConfig
from spawn.core.registry import get_template, instantiate_template
from spawn.utils.git import initialize_git
from spawn.utils.uv import initialize_uv, install_packages
from spawn.core.exceptions import SpawnError
from spawn.utils.console import console


class ProjectGenerator:
    def generate(self, config: ProjectConfig) -> Path:
        template = instantiate_template(config)

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

            context = {"project_name": config.name}
            template.generate(project_path, context)

            readme_content = template.get_readme_content(context)
            if readme_content is None:
                readme_content = README_CONTENT.format(project_name=config.name)

            readme_path = project_path / "README.md"
            readme_path.write_text(readme_content, encoding="utf-8")

            gitignore_path = project_path / ".gitignore"

            gitignore_path.write_text(
                GITIGNORE_CONTENT,
                encoding="utf-8",
            )

            if config.use_git:
                console.print(
                    "[yellow]Initializing Git...[/yellow]"
                )
                initialize_git(project_path)

            initialize_uv(project_path)

            deps = template.get_dependencies()
            if deps:
                console.print(
                    "[yellow]Installing dependencies...[/yellow]"
                )
                install_packages(project_path, deps)

            template.post_install(project_path)

            meta_dir = project_path / ".spawn"
            meta_dir.mkdir()
            meta_file = meta_dir / "meta.json"
            meta_file.write_text(
                json.dumps(
                    {
                        "intent": config.template,
                        "framework": config.framework,
                        "spawn_version": __version__,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

        except OSError as e:
            shutil.rmtree(project_path, ignore_errors=True)
            raise SpawnError(str(e)) from e

        except BaseException:
            shutil.rmtree(project_path, ignore_errors=True)
            raise

        return project_path