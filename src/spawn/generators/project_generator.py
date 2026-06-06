from pathlib import Path
from spawn.templates.files import (
    README_CONTENT,
    GITIGNORE_CONTENT,
)
from spawn.core.models import ProjectConfig
from spawn.core.registry import get_template
from spawn.utils.git import initialize_git
from spawn.utils.uv import initialize_uv
from spawn.utils.success import show_success
from spawn.utils.next_steps import show_next_steps
from spawn.core.exceptions import SpawnError

class ProjectGenerator:
    def generate(self, config: ProjectConfig) -> None:
        template = get_template(config.template)

        if template is None:
            raise SpawnError(f"Unknown template: {config.template}")

        project_path = Path(config.name)

        project_path.mkdir(exist_ok=True)

        for folder in template.folders:
            (project_path / folder).mkdir(exist_ok=True)

        readme_path = project_path / "README.md"

        readme_path.write_text(
          README_CONTENT.format(project_name=config.name)
        )

        gitignore_path = project_path / ".gitignore"

        gitignore_path.write_text(
          GITIGNORE_CONTENT
        )

        if config.use_git:
            print("Initializing Git...")
            initialize_git(project_path)
        initialize_uv(project_path)

        show_success(
          project_name=config.name,
          template_name=template.name,
          use_git=config.use_git,
        )

        show_next_steps(
          config.name,
          config.template,
        )
