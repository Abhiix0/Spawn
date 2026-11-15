"""Regression tests for Issue 2: rejection of option-like project names.

Covers:
- Single-hyphen prefix names like -lead, -rf are rejected.
- Double-hyphen prefix names like --help, --version are rejected.
- Multiple hyphens like --- are rejected.
- Valid names starting with a letter after a legal hyphen interior are still accepted.
- Validation fires before any filesystem or git side-effects.
"""

from __future__ import annotations

import pytest

from spawn.core.exceptions import InvalidInputError, SpawnError
from spawn.utils.validators import validate_project_name

_OPTION_MSG = "must not start with a hyphen"


# ---------------------------------------------------------------------------
# Option-like names — must be rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "-lead",
        "-rf",
        "--help",
        "--version",
        "---",
        "-a",
        "--output",
        "--index-url=https://evil.example/",
    ],
)
def test_option_like_name_rejected(name):
    with pytest.raises(InvalidInputError, match=_OPTION_MSG):
        validate_project_name(name)


# ---------------------------------------------------------------------------
# Valid names with internal hyphens — must still pass
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "my-project",
        "a-b-c",
        "project-1",
        "x",
    ],
)
def test_internal_hyphen_names_still_valid(name):
    validate_project_name(name)  # must not raise


# ---------------------------------------------------------------------------
# No filesystem or git side-effects on invalid names
# ---------------------------------------------------------------------------


def test_option_name_no_filesystem_side_effects(tmp_path, monkeypatch):
    """build_config_from_args must raise before creating any directory."""
    monkeypatch.chdir(tmp_path)

    from spawn.cli.noninteractive import build_config_from_args

    with pytest.raises(SpawnError):
        build_config_from_args(name="-lead", template="automation")

    # Nothing should have been created in cwd.
    assert list(tmp_path.iterdir()) == []


def test_double_hyphen_no_filesystem_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    from spawn.cli.noninteractive import build_config_from_args

    with pytest.raises(SpawnError):
        build_config_from_args(name="--help", template="automation")

    assert list(tmp_path.iterdir()) == []
