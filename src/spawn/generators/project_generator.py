from __future__ import annotations

import signal
import sys
from pathlib import Path

from spawn.core.exceptions import FilesystemError, TemplateError
from spawn.core.models import ProjectConfig
from spawn.core.registry import instantiate_template
from spawn.generators.destination import (
    assert_available,
    cleanup_created,
    record_ownership,
    resolve_destination,
)
from spawn.generators.metadata import write_project_meta
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

# Signals we want to handle for cleanup.  SIGHUP is not available on Windows;
# we guard with getattr so the module still imports cleanly there.
_CLEANUP_SIGNALS: list[signal.Signals] = [signal.SIGTERM]
if hasattr(signal, "SIGHUP"):
    _CLEANUP_SIGNALS.append(getattr(signal, "SIGHUP"))  # type: ignore[arg-type]


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

    def _apply_file_only_extras(self, project_path: Path, extras: list[str]) -> None:
        if "pre-commit" in extras:
            write_precommit_config(project_path)
        skipped = [e for e in extras if e != "pre-commit"]
        if skipped:
            console.print(
                f"[yellow]Skipped without uv: {', '.join(skipped)} "
                "(need pyproject.toml)[/yellow]"
            )

    def generate(self, config: ProjectConfig) -> Path:
        template = instantiate_template(config)

        if template is None:
            raise TemplateError(f"Unknown template: {config.template}")

        project_path = resolve_destination(config.name, config.destination)
        assert_available(project_path, f"Directory '{config.name}' already exists.")

        created = False
        token = None
        old_handlers: dict[signal.Signals, object] = {}

        def _signal_cleanup(signum: int, frame: object) -> None:
            """Clean up the partial project and exit with a non-zero status."""
            if created:
                cleanup_created(project_path, token=token)
            # Restore the original handler before re-raising so that callers
            # higher up the stack (e.g. shells) see the correct signal.
            sig = signal.Signals(signum)
            prev = old_handlers.get(sig, signal.SIG_DFL)
            signal.signal(sig, prev)  # type: ignore[arg-type]
            # Exit 128 + signum — standard Unix convention for signal termination.
            sys.exit(128 + signum)

        try:
            # Install cleanup handlers for SIGTERM (and SIGHUP on Unix).
            # We do this after assert_available but before any filesystem work
            # so the window where a signal could leave debris is as small as
            # possible.
            for sig in _CLEANUP_SIGNALS:
                try:
                    old_handlers[sig] = signal.signal(sig, _signal_cleanup)
                except (OSError, ValueError):
                    # signal() can fail in non-main threads or on platforms
                    # that don't support the signal; ignore and continue.
                    pass

            project_path.mkdir()
            created = True
            token = record_ownership(project_path)

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
            gitignore_path.write_text(GITIGNORE_CONTENT, encoding="utf-8")

            if config.use_git:
                console.print("[yellow]Initializing Git...[/yellow]")
                initialize_git(project_path)

            if not config.use_uv:
                self._apply_file_only_extras(project_path, config.extras)
            else:
                initialize_uv(project_path)

                deps = template.get_dependencies()
                if deps:
                    console.print("[yellow]Installing dependencies...[/yellow]")
                    install_packages(project_path, deps)

                template.post_install(project_path)
                self._apply_quality_extras(project_path, config.extras)

            write_project_meta(project_path, config, generator="blueprint")

        except OSError as e:
            if created:
                cleanup_created(project_path, token=token)
            raise FilesystemError(str(e)) from e

        except BaseException:
            if created:
                cleanup_created(project_path, token=token)
            raise

        finally:
            # Always restore the previous signal handlers.
            for sig, prev in old_handlers.items():
                try:
                    signal.signal(sig, prev)  # type: ignore[arg-type]
                except (OSError, ValueError):
                    pass

        return project_path
