"""Processing regressions checked without timing-sensitive assertions."""

import hashlib
import struct

import pytest

from spawn.inspection import _reading
from spawn.inspection.discovery import discover_repository
from spawn.onboarding import build_onboarding_report


def test_onboarding_opens_shared_sources_once_per_report(tmp_path, monkeypatch):
    source = tmp_path / "app.py"
    source.write_text("import flask\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
    opened = []
    read = _reading._read_from_root

    def record(handle, parts, limit):
        opened.append("/".join(parts))
        return read(handle, parts, limit)

    monkeypatch.setattr(_reading, "_read_from_root", record)
    report = build_onboarding_report(tmp_path)
    assert {item.name for item in report.frameworks} == {"flask"}
    assert sorted(opened) == ["app.py", "pyproject.toml"]

    source.write_text("import fastapi\n", encoding="utf-8")
    report = build_onboarding_report(tmp_path)
    assert {item.name for item in report.frameworks} == {"fastapi"}
    assert opened.count("app.py") == 2


def _index(root, name: bytes | None) -> None:
    body = struct.pack(">4sII", b"DIRC", 2, int(name is not None))
    if name is not None:
        record = struct.pack(">10I20sH", *([0] * 10), b"\x01" * 20, len(name))
        record += name + b"\0"
        body += record.ljust((len(record) + 7) & ~7, b"\0")
    (root / ".git/index").write_bytes(
        body + hashlib.sha1(body, usedforsecurity=False).digest()
    )


@pytest.mark.parametrize("case", ["literal", "tracked", "negated", "bad-index"])
def test_local_git_exclusions_prune_only_proven_untracked_directories(tmp_path, case):
    (tmp_path / ".git/info").mkdir(parents=True)
    (tmp_path / ".git/info/exclude").write_text(
        "# Local configuration\n/scratch/\n*.cache/\n", encoding="utf-8"
    )
    if case == "negated":
        (tmp_path / ".gitignore").write_text("!/scratch/\n", encoding="utf-8")
    _index(tmp_path, b"scratch/app.py" if case == "tracked" else None)
    if case == "bad-index":
        (tmp_path / ".git/index").write_bytes(b"DIRC")
    for name in ("scratch", "retained.cache", "node_modules"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "app.py").touch()
    inventory = discover_repository(tmp_path)
    assert "node_modules" in inventory.skipped
    assert "retained.cache/app.py" in inventory.files
    assert ("scratch" in inventory.skipped) == (case == "literal")
    assert ("scratch/app.py" in inventory.files) == (case != "literal")
    assert (
        "scratch/app.py"
        in discover_repository(tmp_path, excluded_directories={".git"}).files
    )
