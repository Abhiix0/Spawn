from spawn.github.validators import (
    is_valid_github_url,
)


def test_valid_https_url():
    assert is_valid_github_url("https://github.com/user/repo")


def test_valid_https_git_url():
    assert is_valid_github_url("https://github.com/user/repo.git")


def test_valid_ssh_url():
    assert is_valid_github_url("git@github.com:user/repo.git")


def test_empty_url():
    assert not is_valid_github_url("")


def test_invalid_url():
    assert not is_valid_github_url("hello world")


def test_non_github_url():
    assert not is_valid_github_url("https://google.com")


def test_rejects_dot_only_username():
    assert not is_valid_github_url("https://github.com/.../repo")


def test_rejects_leading_dot_username():
    assert not is_valid_github_url("https://github.com/.user/repo")


def test_rejects_leading_hyphen_username():
    assert not is_valid_github_url("https://github.com/-user/repo")


def test_valid_url_with_dots_in_repo():
    assert is_valid_github_url("https://github.com/user/my.repo.git")


def test_valid_ssh_url_with_underscores():
    assert is_valid_github_url("git@github.com:org_name/repo_name.git")
