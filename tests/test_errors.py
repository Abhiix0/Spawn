"""Error hierarchy, exit-code contract, and redaction."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.core.exceptions import (
    ConfigError,
    FilesystemError,
    GenerationError,
    InvalidInputError,
    PublishError,
    SpawnError,
    StructureParseError,
    TemplateError,
    ToolchainError,
)
from spawn.core.models import ProjectConfig
from spawn.github.exceptions import GitHubPublishError
from spawn.utils.redact import redact_url

runner = CliRunner()


@pytest.mark.parametrize(
    "cls, code",
    [
        (SpawnError, 1),
        (InvalidInputError, 1),
        (ConfigError, 1),
        (FilesystemError, 3),
        (ToolchainError, 4),
        (GenerationError, 5),
        (TemplateError, 5),
        (PublishError, 6),
        (StructureParseError, 1),
        (GitHubPublishError, 6),
    ],
)
def test_exit_codes_and_base(cls, code):
    assert issubclass(cls, SpawnError)
    assert cls.exit_code == code


def test_hierarchy_relations():
    assert issubclass(GitHubPublishError, PublishError)
    assert issubclass(StructureParseError, InvalidInputError)
    assert issubclass(TemplateError, GenerationError)


def _no_traceback(result):
    assert "Traceback" not in result.output


def _create(*args, **kw):
    return runner.invoke(app, ["create", *args], **kw)


def test_unknown_template_exits_1():
    r = _create("--name", "x", "--template", "nope")
    assert r.exit_code == 1
    _no_traceback(r)


def test_bad_option_value_exits_1():
    r = _create("--name", "x", "--template", "cli", "--license", "gpl")
    assert r.exit_code == 1
    _no_traceback(r)


def test_dry_run_exits_0(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = _create("--name", "x", "--template", "cli", "--dry-run")
    assert r.exit_code == 0
    assert not (tmp_path / "x").exists()


def test_usage_error_exits_2():
    assert _create("--bogus").exit_code == 2


def test_directory_exists_maps_to_filesystem_3(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "demo").mkdir()
    r = _create("--name", "demo", "--template", "cli", "--no-git", "--no-uv")
    assert r.exit_code == 3
    assert "already exists" in r.output
    _no_traceback(r)


def test_git_missing_exits_4(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("spawn.utils.git.subprocess.run", side_effect=FileNotFoundError):
        r = _create("--name", "demo", "--template", "cli", "--no-uv")
    assert r.exit_code == 4
    assert "Git is not installed" in r.output
    _no_traceback(r)


def test_uv_failure_exits_4(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    err = subprocess.CalledProcessError(1, ["uv"], stderr="uv exploded")
    with patch("spawn.utils.uv.subprocess.run", side_effect=err):
        r = _create("--name", "demo", "--template", "cli", "--no-git")
    assert r.exit_code == 4
    assert "uv exploded" in r.output
    _no_traceback(r)


def test_template_failure_exits_5(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch(
        "spawn.generators.project_generator.instantiate_template", return_value=None
    ):
        r = _create("--name", "demo", "--template", "cli", "--no-git", "--no-uv")
    assert r.exit_code == 5
    _no_traceback(r)


def test_oserror_during_write_exits_3(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch(
        "spawn.generators.project_generator.write_project_meta",
        side_effect=OSError("disk full"),
    ):
        r = _create("--name", "demo", "--template", "cli", "--no-git", "--no-uv")
    assert r.exit_code == 3
    assert "disk full" in r.output
    _no_traceback(r)
    assert not (tmp_path / "demo").exists()


def test_publish_failure_exits_6():
    cfg = ProjectConfig(name="demo", template="cli", use_git=True)
    with (
        patch("spawn.cli.app.get_project_config", return_value=cfg),
        patch("spawn.cli.app.generate_project", return_value=Path("demo")),
        patch("spawn.cli.app.show_success"),
        patch("spawn.cli.app.Confirm.ask", return_value=True),
        patch("spawn.cli.app.Prompt.ask", return_value="https://github.com/a/b"),
        patch("spawn.cli.app.GitHubPublisher") as pub,
    ):
        pub.return_value.publish.side_effect = GitHubPublishError("rejected")
        r = _create()
    assert r.exit_code == 6
    assert "rejected" in r.output
    _no_traceback(r)


def test_cancel_exits_130():
    with patch("spawn.cli.app.get_project_config", side_effect=typer.Abort):
        r = _create()
    assert r.exit_code == 130
    assert "Cancelled." in r.output


def test_prompt_spawn_error_exits_with_its_code():
    with patch(
        "spawn.cli.app.get_project_config",
        side_effect=InvalidInputError("Could not parse structure."),
    ):
        r = _create()
    assert r.exit_code == 1
    _no_traceback(r)


def test_unexpected_error_exits_10_without_traceback(monkeypatch):
    monkeypatch.delenv("SPAWN_DEBUG", raising=False)
    with patch("spawn.cli.app.generate_project", side_effect=RuntimeError("boom")):
        r = _create("--name", "demo", "--template", "cli")
    assert r.exit_code == 10
    assert "Unexpected error (RuntimeError): boom" in r.output
    assert "SPAWN_DEBUG=1" in r.output
    _no_traceback(r)


def test_unexpected_error_propagates_with_spawn_debug(monkeypatch):
    monkeypatch.setenv("SPAWN_DEBUG", "1")
    with patch("spawn.cli.app.generate_project", side_effect=RuntimeError("boom")):
        r = _create("--name", "demo", "--template", "cli")
    assert isinstance(r.exception, RuntimeError)


def test_doctor_unexpected_error_exits_10(tmp_path, monkeypatch):
    monkeypatch.delenv("SPAWN_DEBUG", raising=False)
    with patch("spawn.utils.doctor.run_health_check", side_effect=RuntimeError("x")):
        r = runner.invoke(app, ["doctor", str(tmp_path)])
    assert r.exit_code == 10


def test_typer_exit_not_swallowed_by_generic_handler(tmp_path):
    r = runner.invoke(app, ["doctor", str(tmp_path / "missing")])
    assert r.exit_code == 1
    assert "Unexpected" not in r.output


def test_redact_url_strips_credentials():
    url = "https://user:ghp_SECRET@github.com/a/b.git"
    out = redact_url(f"fatal: unable to access '{url}': denied")
    assert "ghp_SECRET" not in out and "user:" not in out
    assert "https://github.com/a/b.git" in out
    assert redact_url("https://github.com/a/b") == "https://github.com/a/b"


def test_git_stderr_is_redacted():
    from spawn.utils.git import run_git_command

    err = subprocess.CalledProcessError(
        1, ["git"], stderr="fatal: https://u:tok123@github.com/a/b.git failed"
    )
    with patch("spawn.utils.git.subprocess.run", side_effect=err):
        with pytest.raises(ToolchainError) as ei:
            run_git_command(Path("."), "push")
    assert "tok123" not in str(ei.value)
