import pytest

from spawn.core.exceptions import SpawnError
from spawn.utils.validators import validate_project_name

# Shorthand message constants so assertions are readable and DRY
_NO_ALNUM = "must contain at least one letter or number"
_BAD_CHARS = "can only contain letters, numbers, hyphens"


# ---------------------------------------------------------------------------
# Valid names — must not raise
# ---------------------------------------------------------------------------


def test_valid_project_name():
    validate_project_name("my-project")


def test_valid_project_name_with_underscore():
    validate_project_name("my_project")


def test_valid_project_name_with_numbers():
    validate_project_name("project123")


def test_valid_single_letter():
    validate_project_name("a")


def test_valid_mixed_separators():
    validate_project_name("my_cool-project123")


# ---------------------------------------------------------------------------
# No alphanumeric character → "must contain at least one letter or number"
# ---------------------------------------------------------------------------


def test_empty_string_gives_no_alnum_message():
    with pytest.raises(SpawnError, match=_NO_ALNUM):
        validate_project_name("")


def test_single_hyphen_gives_no_alnum_message():
    with pytest.raises(SpawnError, match=_NO_ALNUM):
        validate_project_name("-")


def test_only_hyphens_gives_no_alnum_message():
    with pytest.raises(SpawnError, match=_NO_ALNUM):
        validate_project_name("--")


def test_only_underscores_gives_no_alnum_message():
    with pytest.raises(SpawnError, match=_NO_ALNUM):
        validate_project_name("___")


def test_hyphens_and_underscores_only_gives_no_alnum_message():
    with pytest.raises(SpawnError, match=_NO_ALNUM):
        validate_project_name("-_-")


# ---------------------------------------------------------------------------
# Disallowed characters present → "can only contain letters, numbers, hyphens…"
# ---------------------------------------------------------------------------


def test_slash_gives_bad_chars_message():
    with pytest.raises(SpawnError, match=_BAD_CHARS):
        validate_project_name("my/project")


def test_space_gives_bad_chars_message():
    with pytest.raises(SpawnError, match=_BAD_CHARS):
        validate_project_name("my project")


def test_asterisk_gives_bad_chars_message():
    with pytest.raises(SpawnError, match=_BAD_CHARS):
        validate_project_name("my*project")


def test_dot_gives_bad_chars_message():
    with pytest.raises(SpawnError, match=_BAD_CHARS):
        validate_project_name("my.project")


def test_at_sign_gives_bad_chars_message():
    with pytest.raises(SpawnError, match=_BAD_CHARS):
        validate_project_name("my@project")
