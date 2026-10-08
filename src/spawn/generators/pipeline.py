from pathlib import Path

from spawn.core.models import ProjectConfig
from spawn.generators.custom_structure import CustomStructureGenerator
from spawn.core.exceptions import SpawnError
from spawn.generators.destination import cleanup_created
from spawn.generators.metadata import write_project_meta
from spawn.generators.project_generator import ProjectGenerator


def generate_project(config: ProjectConfig) -> Path:
    """Single entry point: generate a project (custom or template) from config."""
    if config.template == "custom":
        project_path = CustomStructureGenerator().generate(
            project_name=config.name,
            entries=config.custom_entries or [],
            use_git=config.use_git,
            use_uv=config.use_uv,
            dependencies=config.custom_dependencies,
            dev_setup=config.custom_dev_setup,
            gitignore_extra=config.custom_gitignore_extra,
            generate_claude_md=config.generate_claude_md,
            destination=config.destination,
        )
        try:
            write_project_meta(project_path, config, generator="custom")
        except OSError as e:
            cleanup_created(project_path)
            raise SpawnError(str(e)) from e
        return project_path

    return ProjectGenerator().generate(config)
