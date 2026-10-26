"""Tests for `spawn inspect` (cli/app.py + cli/inspect_render.py)."""

import ast
import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spawn.cli import app as app_module
from spawn.cli.app import app
from spawn.inspection import (
    AnalysisStatus,
    Diagnostic,
    InspectionError,
    run_inspection,
    to_json,
)

runner = CliRunner()


@pytest.fixture
def repo(tmp_path):
    d = tmp_path / "my repo"
    d.mkdir()
    (d / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["fastapi", "httpx"]\n',
        encoding="utf-8",
    )
    (d / "main.py").write_text("print(1)\n", encoding="utf-8")
    return d


def _stable(report_dict):
    report_dict.pop("generated_at")
    return report_dict


def test_explicit_path_human(repo, monkeypatch):
    monkeypatch.chdir(repo.parent)
    result = runner.invoke(app, ["inspect", "my repo"])
    assert result.exit_code == 0
    for heading in (
        "SPAWN / INSPECT",
        "PROJECT OVERVIEW",
        "TECHNOLOGY",
        "REPOSITORY STRUCTURE",
        "DIAGNOSTICS",
        "No warnings detected",
        "Inspection complete",
    ):
        assert heading in result.output
    assert "detected" in result.output
    assert "fastapi" in result.output
    assert str(repo) not in result.output.replace("\n", "")


def test_default_path_is_cwd(repo, monkeypatch):
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["inspect"])
    assert result.exit_code == 0
    assert "SPAWN / INSPECT" in result.output
    assert str(repo) not in result.output.replace("\n", "")


def test_help():
    result = runner.invoke(app, ["inspect", "--help"])
    assert result.exit_code == 0
    assert "--json" in result.output
    assert "read-only" in result.output.lower()


def test_unknown_option_exit_2():
    assert runner.invoke(app, ["inspect", "--nope"]).exit_code == 2


def test_json_is_exactly_the_report(repo):
    result = runner.invoke(app, ["inspect", str(repo), "--json"])
    assert result.exit_code == 0
    assert result.stdout.startswith("{")
    data = json.loads(result.stdout)
    assert "schema_version" in data
    expected = run_inspection(str(repo)).to_dict()
    assert _stable(data) == _stable(expected)


def test_json_error_goes_to_stderr(tmp_path):
    result = runner.invoke(app, ["inspect", str(tmp_path / "missing"), "--json"])
    assert result.exit_code == 7
    assert result.stdout == ""
    assert "missing" in result.stderr


def test_human_error_exit_7(tmp_path):
    result = runner.invoke(app, ["inspect", str(tmp_path / "missing")])
    assert result.exit_code == 7
    assert "❌" in result.output


def test_file_instead_of_directory(repo):
    result = runner.invoke(app, ["inspect", str(repo / "main.py"), "--json"])
    assert result.exit_code == 7
    assert result.stdout == ""


def test_empty_directory(tmp_path):
    result = runner.invoke(app, ["inspect", str(tmp_path)])
    assert result.exit_code == 0
    assert "0 files" in result.output and "Inspection complete" in result.output


def test_partial_report_exit_0_and_warning_shown(repo):
    (repo / "pyproject.toml").write_text("[project\nbroken", encoding="utf-8")
    result = runner.invoke(app, ["inspect", str(repo)])
    assert result.exit_code == 0
    assert "Inspection partial" in result.output
    assert "malformed" in result.output.lower()


def test_failed_report_prints_then_exit_7(repo, monkeypatch):
    real = run_inspection(str(repo))
    from dataclasses import replace

    failed = replace(
        real,
        status=AnalysisStatus.FAILED,
        diagnostics=(Diagnostic("x.boom", "it broke", "error", "x", fatal=True),),
    )
    monkeypatch.setattr("spawn.inspection.run_inspection", lambda p: failed)
    human = runner.invoke(app, ["inspect", str(repo)])
    assert human.exit_code == 7
    assert "x.boom" in human.output and "Inspection failed" in human.output
    js = runner.invoke(app, ["inspect", str(repo), "--json"])
    assert js.exit_code == 7
    assert json.loads(js.stdout)["status"] == "failed"


def test_inferred_and_unknown_show_detail(repo, monkeypatch):
    from dataclasses import replace

    from spawn.inspection import DetectionState, Evidence, Finding, FindingCategory

    real = run_inspection(str(repo))
    inferred = Finding(
        FindingCategory.FRAMEWORK,
        "flask",
        DetectionState.INFERRED,
        (Evidence("req.txt", "flask"),),
        "guessed from requirements",
    )
    unknown = Finding(
        FindingCategory.TOOL, "mystery", DetectionState.UNKNOWN, (), "cannot tell"
    )
    rep = replace(
        real,
        findings=(inferred, unknown),
        summary=replace(real.summary, primary_framework="flask"),
    )
    monkeypatch.setattr("spawn.inspection.run_inspection", lambda p: rep)
    out = " ".join(runner.invoke(app, ["inspect", str(repo)]).output.split())
    assert "inferred" in out and "guessed from requirements" in out
    assert "unknown" in out and "cannot tell" in out
    assert "flask · inferred" in out


def test_dependency_list_capped_human_complete_json(repo):
    deps = ", ".join(f'"pkg{i}"' for i in range(50))
    (repo / "pyproject.toml").write_text(
        f'[project]\nname = "d"\ndependencies = [{deps}]\n', encoding="utf-8"
    )
    human = " ".join(runner.invoke(app, ["inspect", str(repo)]).output.split())
    assert "more (--verbose)" in human and "pkg49" not in human
    full = " ".join(
        runner.invoke(app, ["inspect", str(repo), "--verbose"]).output.split()
    )
    assert "pkg49" in full and "more (--verbose)" not in full
    data = json.loads(runner.invoke(app, ["inspect", str(repo), "--json"]).stdout)
    assert sum(f["category"] == "dependency" for f in data["findings"]) >= 50


def test_hostile_filenames_render_literally(repo):
    try:
        (repo / "[red]x").write_text("", encoding="utf-8")
        (repo / "a\x1b[31mb.txt").write_text("", encoding="utf-8")
    except OSError:
        pytest.skip("filesystem rejects filename")
    result = runner.invoke(app, ["inspect", str(repo)])
    assert result.exit_code == 0
    assert "\x1b" not in result.output
    assert "[red]x" in result.output


def test_safe_strips_controls_and_escapes_markup():
    from spawn.cli.inspect_render import safe

    assert "\x1b" not in safe("a\x1bb")
    assert safe("[red]x") == "\\[red]x"
    assert safe("a\udcffb") == "a?b"


def test_json_non_ascii_filename(repo):
    try:
        (repo / "héllo_日本.txt").write_text("", encoding="utf-8")
    except OSError:
        pytest.skip("filesystem rejects filename")
    result = runner.invoke(app, ["inspect", str(repo), "--json"])
    assert result.exit_code == 0
    assert "héllo_日本.txt" in json.loads(result.stdout)["structure"]["top_level_files"]


def test_unexpected_error_json_mode(repo, monkeypatch):
    def boom(p):
        raise RuntimeError("kaboom")

    monkeypatch.setattr("spawn.inspection.run_inspection", boom)
    monkeypatch.delenv("SPAWN_DEBUG", raising=False)
    result = runner.invoke(app, ["inspect", str(repo), "--json"])
    assert result.exit_code == 10
    assert result.stdout == ""
    assert "kaboom" in result.stderr


def test_inspection_error_message_json(monkeypatch, repo):
    def bad(p):
        raise InspectionError("nope")

    monkeypatch.setattr("spawn.inspection.run_inspection", bad)
    result = runner.invoke(app, ["inspect", str(repo), "--json"])
    assert (result.exit_code, result.stdout, result.stderr.strip()) == (7, "", "nope")


def test_no_args_lists_inspect_and_keeps_existing_lines():
    result = runner.invoke(app, [])
    for line in (
        "create    Scaffold a new project",
        "doctor    Check the health of a project directory",
        "version   Show the installed version",
        "inspect   Inspect a repository (read-only)",
    ):
        assert line in result.output


def test_cli_uses_only_run_inspection_entry():
    for mod in ("app", "inspect_render"):
        src = Path(app_module.__file__).with_name(f"{mod}.py").read_text("utf-8")
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("spawn.inspection"):
                    assert node.module == "spawn.inspection", node.module
    src = Path(app_module.__file__).read_text("utf-8")
    assert not re.search(
        r"inspection\.(discovery|dependencies|frameworks|languages|tooling)", src
    )


def test_to_json_roundtrip_matches_stdout(repo, monkeypatch):
    rep = run_inspection(str(repo))
    monkeypatch.setattr("spawn.inspection.run_inspection", lambda p: rep)
    assert runner.invoke(app, ["inspect", str(repo), "--json"]).stdout == to_json(rep)


def _render(report, width=40, verbose=False, color=False):
    import io

    from rich.console import Console

    from spawn.cli import inspect_render

    buf = io.StringIO()
    c = Console(
        file=buf, width=width, force_terminal=color, no_color=not color, record=False
    )
    old = inspect_render.console
    inspect_render.console = c
    try:
        inspect_render.render_report(report, "p", verbose)
    finally:
        inspect_render.console = old
    return buf.getvalue()


def test_render_narrow_no_color_no_overflow_and_semantics(repo):
    from dataclasses import replace

    from spawn.inspection import DetectionState, Evidence, Finding, FindingCategory

    real = run_inspection(str(repo))
    long_name = "x" * 120
    fs = (
        Finding(
            FindingCategory.TOOL,
            "git",
            DetectionState.DETECTED,
            (Evidence(".git", "d"),),
        ),
        Finding(FindingCategory.CONTAINER, "docker", DetectionState.NOT_DETECTED, ()),
        Finding(
            FindingCategory.PACKAGE_MANAGER,
            "pip",
            DetectionState.INFERRED,
            (Evidence("requirements.txt", "f"),),
            "requirements file",
        ),
    )
    rep = replace(
        real,
        findings=fs,
        summary=replace(real.summary, name=long_name, primary_framework=None),
    )
    out = _render(rep)
    assert "\x1b" not in out
    assert all(len(line) <= 40 for line in out.splitlines())
    flat = out.replace("\n", "")
    assert long_name in flat
    assert "pip · inferred" in out.replace("\n", " ")
    assert "not detected" in out and "Not detected" in out  # docker; framework
    assert "WARN" not in out.upper().replace("WARNINGS", "")  # no invented warnings


def test_render_verbose_shows_evidence_and_error_diagnostic(repo):
    from dataclasses import replace

    from spawn.inspection import DetectionState, Evidence, Finding, FindingCategory

    real = run_inspection(str(repo))
    rep = replace(
        real,
        findings=(
            Finding(
                FindingCategory.TOOL,
                "git",
                DetectionState.DETECTED,
                (Evidence("deep/evidence.cfg", "d"),),
            ),
        ),
        diagnostics=(Diagnostic("a.err", "bad thing", "error", "a"),),
    )
    assert "deep/evidence.cfg" not in _render(rep, width=100)
    verbose = _render(rep, width=100, verbose=True)
    assert "deep/evidence.cfg" in verbose
    assert "error a.err: bad thing" in verbose


def test_verbose_flag_json_unchanged(repo):
    plain = runner.invoke(app, ["inspect", str(repo), "--json"]).stdout
    both = runner.invoke(app, ["inspect", str(repo), "--json", "-v"]).stdout
    assert "\x1b" not in both
    assert _stable(json.loads(plain)) == _stable(json.loads(both))
