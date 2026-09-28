import datetime
import json
import shutil
from pathlib import Path

from spawn import __version__
from spawn.core.exceptions import SpawnError
from spawn.core.models import ProjectConfig
from spawn.core.registry import instantiate_template
from spawn.generators.project_files import (
    add_mypy_config,
    write_changelog,
    write_license,
    write_precommit_config,
)
from spawn.templates.shared_content import (
    AGENTS_MD_CONTENT,
    GITIGNORE_CONTENT,
    README_CONTENT,
)
from spawn.utils.console import console
from spawn.utils.git import get_git_user_name, initialize_git
from spawn.utils.uv import initialize_uv, install_packages


class ProjectGenerator:
    def _apply_quality_extras(self, project_path: Path, extras: list[str]) -> None:
        dev_deps = []
        if "mypy" in extras:
            dev_deps.append("mypy")
        if "pre-commit" in extras:
            dev_deps.append("pre-commit")
        if dev_deps:
            console.print("[yellow]Installing dev tools...[/yellow]")
            install_packages(project_path, dev_deps, dev=True)
        if "mypy" in extras:
            add_mypy_config(project_path)
        if "pre-commit" in extras:
            write_precommit_config(project_path)

    def generate(self, config: ProjectConfig) -> Path:
        template = instantiate_template(config)

        if template is None:
            raise SpawnError(f"Unknown template: {config.template}")

        project_path = Path(config.name)

        if project_path.exists():
            raise SpawnError(f"Directory '{config.name}' already exists.")

        try:
            project_path.mkdir()

            context = {"project_name": config.name}
            template.generate(project_path, context)

            readme_content = template.get_readme_content(context)
            if readme_content is None:
                readme_content = README_CONTENT.format(project_name=config.name)

            readme_path = project_path / "README.md"
            readme_path.write_text(readme_content, encoding="utf-8")

            agents_md_content = template.get_agents_md_content(context)
            if agents_md_content is None:
                agents_md_content = AGENTS_MD_CONTENT.format(project_name=config.name)

            agents_md_path = project_path / "AGENTS.md"
            agents_md_path.write_text(agents_md_content, encoding="utf-8")

            if config.generate_claude_md:
                claude_md_path = project_path / "CLAUDE.md"
                claude_md_path.write_text(agents_md_content, encoding="utf-8")

            write_changelog(project_path)
            if config.license != "none":
                holder = get_git_user_name() or f"{config.name} contributors"
                write_license(project_path, config.license, holder)

            gitignore_path = project_path / ".gitignore"

            gitignore_path.write_text(
                GITIGNORE_CONTENT,
                encoding="utf-8",
            )

            if config.use_git:
                console.print("[yellow]Initializing Git...[/yellow]")
                initialize_git(project_path)

            initialize_uv(project_path)

            deps = template.get_dependencies()
            if deps:
                console.print("[yellow]Installing dependencies...[/yellow]")
                install_packages(project_path, deps)

            template.post_install(project_path)
            self._apply_quality_extras(project_path, config.extras)

            meta_dir = project_path / ".spawn"
            meta_dir.mkdir()
            meta_file = meta_dir / "meta.json"
            meta_file.write_text(
                json.dumps(
                    {
                        "intent": config.template,
                        "framework": config.framework,
                        "provider": config.provider,
                        "spawn_version": __version__,
                        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
                        "generator": "blueprint",
                        "git": config.use_git,
                        "uv": True,
                        "source": None,
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
