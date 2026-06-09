from pathlib import Path
from unittest.mock import patch

import pytest

from spawn.github.exceptions import (
    GitHubPublishError,
)
from spawn.github.publisher import (
    GitHubPublisher,
)
from spawn.core.exceptions import SpawnError


def test_missing_project_path():
    publisher = GitHubPublisher()

    with pytest.raises(
        GitHubPublishError
    ):
        publisher.publish(
            Path("missing"),
            "https://github.com/user/repo",
        )


def test_invalid_repo_url(tmp_path):
    publisher = GitHubPublisher()

    with pytest.raises(
        GitHubPublishError
    ):
        publisher.publish(
            tmp_path,
            "not-a-url",
        )


@patch("spawn.github.publisher.is_git_repository")
def test_not_git_repository(
    mock_is_git_repository,
    tmp_path,
):
    mock_is_git_repository.return_value = False

    publisher = GitHubPublisher()

    with pytest.raises(
        GitHubPublishError
    ):
        publisher.publish(
            tmp_path,
            "https://github.com/user/repo",
        )


@patch("spawn.github.publisher.is_git_repository")
@patch("spawn.github.publisher.remote_exists")
def test_remote_already_exists(
    mock_remote_exists,
    mock_is_git_repository,
    tmp_path,
):
    mock_is_git_repository.return_value = True
    mock_remote_exists.return_value = True

    publisher = GitHubPublisher()

    with pytest.raises(
        GitHubPublishError
    ):
        publisher.publish(
            tmp_path,
            "https://github.com/user/repo",
        )


@patch("spawn.github.publisher.push_origin_main")
@patch("spawn.github.publisher.add_remote")
@patch("spawn.github.publisher.rename_main_branch")
@patch("spawn.github.publisher.commit")
@patch("spawn.github.publisher.add_all")
@patch("spawn.github.publisher.remote_exists")
@patch("spawn.github.publisher.is_git_repository")
def test_publish_success(
    mock_is_git_repository,
    mock_remote_exists,
    mock_add_all,
    mock_commit,
    mock_rename_main_branch,
    mock_add_remote,
    mock_push_origin_main,
    tmp_path,
):
    mock_is_git_repository.return_value = True
    mock_remote_exists.return_value = False

    publisher = GitHubPublisher()

    publisher.publish(
        tmp_path,
        "https://github.com/user/repo",
    )

    mock_add_all.assert_called_once_with(
        tmp_path
    )

    mock_commit.assert_called_once_with(
        tmp_path,
        "Initial commit",
    )

    mock_rename_main_branch.assert_called_once_with(
        tmp_path
    )

    mock_add_remote.assert_called_once_with(
        tmp_path,
        "https://github.com/user/repo",
    )

    mock_push_origin_main.assert_called_once_with(
        tmp_path
    )


@patch("spawn.github.publisher.is_git_repository")
@patch("spawn.github.publisher.remote_exists")
@patch("spawn.github.publisher.add_all")
def test_git_not_installed_raises_error(
    mock_add_all,
    mock_remote_exists,
    mock_is_git_repository,
    tmp_path,
):
    mock_is_git_repository.return_value = True
    mock_remote_exists.return_value = False
    mock_add_all.side_effect = SpawnError(
        "Git is not installed or not available in PATH."
    )

    publisher = GitHubPublisher()

    with pytest.raises(GitHubPublishError):
        publisher.publish(
            tmp_path,
            "https://github.com/user/repo",
        )
