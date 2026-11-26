"""Release checks at the Diagnose command boundary."""

import os
import socket
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.diagnostics import service

_PROJECT = '[project]\nname = "security"\n'
_CANARY = "diagnose-release-private-canary"


@pytest.mark.parametrize("flags", [[], ["--json"]])
def test_diagnose_rejects_substituted_repository(tmp_path, monkeypatch, flags):
    root, outside = tmp_path / "repo", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    for item in (root, outside):
        (item / "pyproject.toml").write_text(_PROJECT, encoding="utf-8")
    (outside / "requirements.txt").write_text(f"-r {_CANARY}\n", encoding="utf-8")
    (root / "requirements.txt").write_text("flask\n", encoding="utf-8")
    discover = service.discover_repository

    def substitute(*args, **kwargs):
        inventory = discover(*args, **kwargs)
        root.rename(tmp_path / "original")
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(root), str(outside)],
                capture_output=True,
            )
            if result.returncode or not root.is_junction():
                pytest.skip("Junction creation unavailable")
        else:
            root.symlink_to(outside, target_is_directory=True)
        return inventory

    monkeypatch.setattr(service, "discover_repository", substitute)
    result = CliRunner().invoke(app, ["diagnose", str(root), "--verbose", *flags])
    assert result.exit_code == 9
    assert _CANARY not in result.stdout + result.stderr
    assert "Requirements include is missing" not in result.stdout
    assert (outside / "requirements.txt").read_text(
        encoding="utf-8"
    ) == f"-r {_CANARY}\n"


@pytest.mark.parametrize("flags", [[], ["--json"]])
def test_hostile_inputs_are_inert_and_private(tmp_path, monkeypatch, flags):
    (tmp_path / "pyproject.toml").write_text(_PROJECT, encoding="utf-8")
    (tmp_path / ".env").write_text(_CANARY, encoding="utf-8")
    (tmp_path / "Makefile").write_text(
        f"test:\n\tpytest -c $({_CANARY})\n", encoding="utf-8"
    )
    (tmp_path / f"[red]{_CANARY}.py").write_text(
        f"raise Exception({_CANARY!r})", encoding="utf-8"
    )
    if os.name != "nt":
        (tmp_path / os.fsdecode(b"invalid-\xff-\x1b.py")).touch()
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    def forbidden(*args, **kwargs):
        pytest.fail("Diagnose attempted forbidden activity")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    result = CliRunner().invoke(app, ["diagnose", str(tmp_path), "--verbose", *flags])
    assert result.exit_code == 9
    assert _CANARY not in result.stdout + result.stderr
    assert b"\x1b" not in result.stdout_bytes
    result.stdout_bytes.decode("utf-8", errors="strict")
    assert before == {path.name: path.read_bytes() for path in tmp_path.iterdir()}


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions required")
def test_unreadable_project_directory_abstains(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("Permission check requires a non-root UID")
    (tmp_path / "pyproject.toml").write_text(
        _PROJECT + '[tool.pytest.ini_options]\ntestpaths=["private/qa"]\n',
        encoding="utf-8",
    )
    private = tmp_path / "private"
    private.mkdir()
    (private / "qa").mkdir()
    private.chmod(0)
    try:
        result = CliRunner().invoke(app, ["diagnose", str(tmp_path), "--json"])
        assert result.exit_code == 9
        assert "Pytest testpaths entry is missing" not in result.stdout
    finally:
        private.chmod(0o700)
