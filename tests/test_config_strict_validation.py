"""Regression tests for Issue 11: strict config file validation.

Covers:
- Unknown keys in the JSON object are rejected with a clear message.
- Boolean fields that receive strings ("false", "true") are rejected.
- Boolean fields that receive integers (0, 1) are rejected.
- Directory path supplied instead of a file is rejected.
- Invalid UTF-8 bytes are rejected.
- All existing valid paths continue to work.
"""

from __future__ import annotations

import json

import pytest

from spawn.cli.noninteractive import build_config_from_file
from spawn.core.exceptions import ConfigError


# ---------------------------------------------------------------------------
# Unknown keys
# ---------------------------------------------------------------------------


def test_unknown_key_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "cfg.json"
    f.write_text(
        json.dumps({"name": "demo", "template": "automation", "typo_key": True}),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="unknown key"):
        build_config_from_file(f)


def test_multiple_unknown_keys_listed_in_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "cfg.json"
    f.write_text(
        json.dumps(
            {
                "name": "demo",
                "template": "automation",
                "foo": 1,
                "bar": 2,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="unknown key"):
        build_config_from_file(f)


# ---------------------------------------------------------------------------
# Boolean fields: string values rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("git", "false"),
        ("git", "true"),
        ("git", "False"),
        ("uv", "false"),
        ("uv", "0"),
        ("claude_md", "true"),
    ],
)
def test_string_boolean_rejected(tmp_path, monkeypatch, field, value):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "cfg.json"
    f.write_text(
        json.dumps({"name": "demo", "template": "automation", field: value}),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="must be a boolean"):
        build_config_from_file(f)


@pytest.mark.parametrize(
    "field,value",
    [
        ("git", 0),
        ("git", 1),
        ("uv", 1),
        ("claude_md", 0),
    ],
)
def test_integer_boolean_rejected(tmp_path, monkeypatch, field, value):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "cfg.json"
    f.write_text(
        json.dumps({"name": "demo", "template": "automation", field: value}),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="must be a boolean"):
        build_config_from_file(f)


# ---------------------------------------------------------------------------
# Directory path supplied instead of file
# ---------------------------------------------------------------------------


def test_directory_path_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # tmp_path itself is a directory.
    with pytest.raises(ConfigError, match="directory"):
        build_config_from_file(tmp_path)


def test_subdirectory_path_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    subdir = tmp_path / "myconfig"
    subdir.mkdir()
    with pytest.raises(ConfigError, match="directory"):
        build_config_from_file(subdir)


# ---------------------------------------------------------------------------
# Invalid UTF-8
# ---------------------------------------------------------------------------


def test_invalid_utf8_rejected(tmp_path):
    f = tmp_path / "bad.json"
    # Write raw bytes that are not valid UTF-8.
    f.write_bytes(b'{"name": "demo", "template": "automation"}\xff\xfe')
    with pytest.raises(ConfigError, match="UTF-8"):
        build_config_from_file(f)


# ---------------------------------------------------------------------------
# Valid paths still work (regression guard)
# ---------------------------------------------------------------------------


def test_valid_true_boolean_accepted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "cfg.json"
    f.write_text(
        json.dumps(
            {"name": "demo", "template": "automation", "git": True, "uv": False}
        ),
        encoding="utf-8",
    )
    config = build_config_from_file(f)
    assert config.use_git is True
    assert config.use_uv is False


def test_valid_false_boolean_accepted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "cfg.json"
    f.write_text(
        json.dumps({"name": "demo", "template": "automation", "git": False}),
        encoding="utf-8",
    )
    config = build_config_from_file(f)
    assert config.use_git is False


def test_all_known_keys_accepted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "cfg.json"
    f.write_text(
        json.dumps(
            {
                "name": "demo",
                "template": "automation",
                "framework": None,
                "provider": None,
                "cli_type": None,
                "data_type": None,
                "extras": [],
                "git": True,
                "uv": False,
                "claude_md": False,
                "license": "mit",
            }
        ),
        encoding="utf-8",
    )
    config = build_config_from_file(f)
    assert config.name == "demo"
