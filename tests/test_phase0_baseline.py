"""Security, read-only, golden CLI and large-tree baseline regressions."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.inspection import AnalysisStatus, from_json, run_inspection, to_json
from fixtures import inspection_corpus

runner = CliRunner()
EXIT_CODES = json.loads(
    (Path(__file__).parent / "fixtures/static/inspect_exit_codes.json").read_text(
        encoding="utf-8"
    )
)


def _snapshot(root: Path) -> tuple[tuple[str, str, bytes | str], ...]:
    """Capture names and content without following symbolic links."""
    entries: list[tuple[str, str, bytes | str]] = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        directories.sort()
        filenames.sort()
        current_path = Path(current)
        for name in (*directories, *filenames):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                entries.append((relative, "symlink", os.readlink(path)))
            elif path.is_dir():
                entries.append((relative, "directory", ""))
            else:
                entries.append((relative, "file", path.read_bytes()))
    return tuple(entries)


def test_secret_canary_fixture_is_read_only_and_never_executed(tmp_path):
    root = inspection_corpus.materialize("secret_canary", tmp_path)
    before = _snapshot(root)

    report = run_inspection(root)
    serialized = to_json(report)

    assert "do-not-leak-90b73ce9" not in serialized
    assert not (root / "spawn-phase0-executed.marker").exists()
    assert _snapshot(root) == before


def test_symlink_to_external_canary_is_not_followed_or_modified(tmp_path):
    root = inspection_corpus.materialize("secret_canary", tmp_path)
    external = tmp_path / "external-canary.txt"
    external.write_text("external-secret-1cb4042b", encoding="utf-8")
    link = root / "external.txt"
    try:
        os.symlink(external, link)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    before_root = _snapshot(root)
    before_external = external.read_bytes()
    report = run_inspection(root)

    assert "external-secret-1cb4042b" not in to_json(report)
    assert _snapshot(root) == before_root
    assert external.read_bytes() == before_external


def test_large_tree_fixture_is_deterministic_and_valid(tmp_path):
    root = inspection_corpus.materialize("large_tree", tmp_path)
    source_files = sorted((root / "src").rglob("*.py"))
    assert len(source_files) == 2_000

    report = run_inspection(root)
    assert report.status == AnalysisStatus.COMPLETE


def test_inspection_json_matches_golden_sample_report(monkeypatch, tmp_path):
    sample = Path(__file__).parent / "fixtures/static/sample_report.json"
    report = from_json(sample.read_text(encoding="utf-8"))
    monkeypatch.setattr("spawn.inspection.run_inspection", lambda _path: report)

    result = runner.invoke(app, ["inspect", str(tmp_path), "--json"])

    assert result.exit_code == EXIT_CODES["partial_report"]
    assert result.stdout == sample.read_text(encoding="utf-8")
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (("inspect", ".", "--json"), "valid_json"),
        (("inspect", "path-that-does-not-exist", "--json"), "missing_path"),
        (("inspect", "--unknown"), "unknown_option"),
    ],
)
def test_inspect_cli_exit_codes_match_golden(tmp_path, monkeypatch, args, expected):
    if expected == "valid_json":
        monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, list(args))

    assert result.exit_code == EXIT_CODES[expected]
