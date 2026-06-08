import pytest

from spawn.utils.validators import validate_project_name
from spawn.core.exceptions import SpawnError


def test_valid_project_name():
    validate_project_name("my-project")


def test_valid_project_name_with_underscore():
    validate_project_name("my_project")


def test_valid_project_name_with_numbers():
    validate_project_name("project123")


def test_invalid_project_name_with_slash():
    with pytest.raises(SpawnError):
        validate_project_name("my/project")


def test_invalid_project_name_with_space():
    with pytest.raises(SpawnError):
        validate_project_name("my project")


def test_invalid_project_name_with_special_character():
    with pytest.raises(SpawnError):
        validate_project_name("my*project")


def test_invalid_project_name_empty_string():
    with pytest.raises(SpawnError):
        validate_project_name("")


def test_invalid_project_name_single_hyphen():
    with pytest.raises(SpawnError):
        validate_project_name("-")


def test_invalid_project_name_only_hyphens():
    with pytest.raises(SpawnError):
        validate_project_name("--")