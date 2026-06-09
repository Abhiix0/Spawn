from pathlib import Path

from spawn.github.validators import (
    is_valid_github_url,
)
from spawn.github.exceptions import (
    GitHubPublishError,
)
from spawn.core.exceptions import SpawnError

from spawn.utils.git import (
    add_all,
    commit,
    rename_main_branch,
    add_remote,
    push_origin_main,
    remote_exists,
    is_git_repository,
)


class GitHubPublisher:
    def publish(
        self,
        project_path: Path,
        repo_url: str,
    ) -> None:

        if not project_path.exists():
            raise GitHubPublishError(
                f"Project path does not exist: {project_path}"
            )

        if not is_valid_github_url(repo_url):
            raise GitHubPublishError(
                "Invalid GitHub repository URL."
            )

        if not is_git_repository(project_path):
            raise GitHubPublishError(
                "Project is not a Git repository."
            )

        if remote_exists(project_path):
            raise GitHubPublishError(
                "Origin remote already exists."
            )

        try:
            add_all(project_path)

            commit(
                project_path,
                "Initial commit",
            )

            rename_main_branch(project_path)

            add_remote(
                project_path,
                repo_url,
            )

            push_origin_main(project_path)

        except SpawnError as exc:
            raise GitHubPublishError(
                str(exc)
            ) from exc