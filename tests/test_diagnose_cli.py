"""Diagnose CLI exit, output, and terminal contracts."""

import json
from io import StringIO

import pytest
from rich.console import Console
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.cli.diagnose_render import render_diagnose
from spawn.diagnostics import service
from spawn.diagnostics.models import (
    Coverage,
    DiagnosticsReport,
    Evidence,
    IssueDescription,
    Outcome,
    Reason,
    RepositoryIdentity,
    RepositoryIssue,
    RuleOutcome,
    Severity,
)
from spawn.diagnostics.serialization import from_json
from spawn.inspection import InspectionError

runner = CliRunner()
_MANIFEST = (
    '[project]\nname = "example"\n[tool.pytest.ini_options]\ntestpaths = ["{}"]\n'
)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "example-api"
    root.mkdir()
    (root / "pyproject.toml").write_text(_MANIFEST.format("tests"), encoding="utf-8")
    (root / "tests").mkdir()
    return root


def test_default_path_one_call_and_no_mutation(repo, monkeypatch):
    monkeypatch.chdir(repo)
    calls = []
    original = service.run_diagnostics

    def run(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(service, "run_diagnostics", run)
    before = {p: p.read_bytes() if p.is_file() else None for p in repo.rglob("*")}
    result = runner.invoke(app, ["diagnose", "--json"])
    assert (result.exit_code, result.stderr, calls) == (0, "", ["."])
    assert from_json(result.stdout_bytes).is_clean
    assert before == {
        p: p.read_bytes() if p.is_file() else None for p in repo.rglob("*")
    }


@pytest.mark.parametrize(
    "flags,code", [([], 0), (["--fail-on", "warning"], 8), (["--fail-on", "error"], 0)]
)
def test_real_warning_thresholds(repo, flags, code):
    (repo / "pyproject.toml").write_text(_MANIFEST.format("missing"), encoding="utf-8")
    result = runner.invoke(app, ["diagnose", str(repo), "--json", *flags])
    assert (result.exit_code, result.stderr) == (code, "")
    report = json.loads(result.stdout_bytes)
    assert report["severity_counts"]["warning"] == 1
    assert report["status"] == "complete"


def test_partial_precedes_threshold_and_json_flags_are_inert(repo):
    manifest = _MANIFEST.format("missing") + '\n[tool.example]\nvalue = "unused"\n'
    (repo / "pyproject.toml").write_text(manifest, encoding="utf-8")
    (repo / "Makefile").write_text("test:\n\tpytest -c $(VARIABLE)\n", encoding="utf-8")
    args = ["diagnose", str(repo), "--json", "--fail-on", "warning"]
    plain = runner.invoke(app, args)
    flags = runner.invoke(app, [*args, "--verbose", "--no-color"])
    assert plain.exit_code == flags.exit_code == 9
    assert plain.stderr == flags.stderr == ""
    assert plain.stdout_bytes == flags.stdout_bytes
    assert plain.stdout_bytes.endswith(b"\n") and not plain.stdout_bytes.endswith(
        b"\n\n"
    )
    assert b"\x1b" not in plain.stdout_bytes
    report = json.loads(plain.stdout_bytes)
    assert report["status"] == "partial"
    assert report["severity_counts"]["warning"] == 1
    assert report["outcome_counts"]["unknown"] == 1


def test_invalid_root_and_usage(tmp_path):
    for flags in ([], ["--json"]):
        result = runner.invoke(
            app, ["diagnose", str(tmp_path / "private-canary"), *flags]
        )
        assert (result.exit_code, result.stdout) == (7, "")
        assert "readable directory" in result.stderr
        assert "private-canary" not in result.stderr
    result = runner.invoke(app, ["diagnose", "--json", "--fail-on", "info"])
    assert (result.exit_code, result.stdout) == (2, "")
    assert result.stderr


@pytest.mark.parametrize(
    "failure,code",
    [
        (RuntimeError("private-canary"), 10),
        (InspectionError("private-canary"), 7),
        (KeyboardInterrupt(), 130),
        (EOFError(), 130),
    ],
)
def test_failures_are_generic_and_stderr_only(monkeypatch, failure, code):
    def run(path):
        raise failure

    monkeypatch.setattr(service, "run_diagnostics", run)
    result = runner.invoke(app, ["diagnose", "--json"], env={"SPAWN_DEBUG": "1"})
    assert (result.exit_code, result.stdout) == (code, "")
    assert result.stderr and "private-canary" not in result.stderr


def test_fatal_discovery_report_is_not_emitted(repo, monkeypatch):
    def fail(*args, **kwargs):
        raise InspectionError("private-canary")

    monkeypatch.setattr(service, "discover_repository", fail)
    result = runner.invoke(app, ["diagnose", str(repo), "--json"])
    assert (result.exit_code, result.stdout) == (7, "")
    assert "private-canary" not in result.stderr


def test_serialization_failure_does_not_fall_back(repo, monkeypatch):
    def fail(report):
        raise ValueError("private-canary")

    monkeypatch.setattr("spawn.diagnostics.serialization.to_json", fail)
    result = runner.invoke(app, ["diagnose", str(repo), "--json"])
    assert (result.exit_code, result.stdout) == (10, "")
    assert "private-canary" not in result.stderr


def _report(count=1, *, severity=Severity.ERROR):
    findings = tuple(
        RepositoryIssue(
            "example-rule",
            "testing",
            IssueDescription(
                "example",
                severity,
                "Review configuration",
                "The configured local file is missing.",
                "Restore the file or correct the configured path.",
            ),
            (Evidence("subdir/" * 18 + "données.ini", line=number),),
        )
        for number in range(1, count + 1)
    )
    row = RuleOutcome(
        "example-rule", "testing", Outcome.FINDING, Reason.CONDITION_PROVED, findings
    )
    return DiagnosticsReport(RepositoryIdentity("a" * 64), Coverage.COMPLETE, (row,))


@pytest.mark.parametrize(
    "severity,threshold,code",
    [
        (Severity.ERROR, "error", 8),
        (Severity.ERROR, "warning", 8),
        (Severity.INFO, "warning", 0),
    ],
)
def test_thresholds_and_unicode_json(monkeypatch, severity, threshold, code):
    monkeypatch.setattr(
        service, "run_diagnostics", lambda path: _report(severity=severity)
    )
    result = runner.invoke(app, ["diagnose", "--json", "--fail-on", threshold])
    assert result.exit_code == code
    assert "données.ini".encode() in result.stdout_bytes
    assert from_json(result.stdout_bytes).findings[0].description.severity == severity


@pytest.mark.parametrize("width", [60, 80, 120])
def test_terminal_width_many_findings_and_unsafe_name(monkeypatch, width):
    report = _report(35)
    monkeypatch.setattr(service, "run_diagnostics", lambda path: report)
    result = runner.invoke(
        app,
        ["diagnose", "[red]private\x1b\u202e", "--verbose", "--no-color"],
        env={"COLUMNS": str(width), "FORCE_COLOR": "1"},
    )
    assert (result.exit_code, result.stderr) == (0, "")
    assert "SPAWN / DIAGNOSE" in result.stdout and "Repository" in result.stdout
    assert "private" not in result.stdout and "\x1b" not in result.stdout
    assert result.stdout.count("Review configuration") == 35
    assert "subdir/" * 18 + "données.ini:35" in result.stdout
    assert "example-rule: finding (condition proved)" in result.stdout
    assert all(
        len(line) <= width
        for line in result.stdout.splitlines()
        if "données.ini:" not in line
    )
    if width == 60:
        assert "━" not in result.stdout


def test_legacy_encoding_and_no_findings(monkeypatch, repo):
    class AsciiStream(StringIO):
        encoding = "ascii"

    stream = AsciiStream()
    render_diagnose(_report(), "données", Console(file=stream, width=80))
    assert "donn\\xe9es" in stream.getvalue()
    clean = runner.invoke(
        app, ["diagnose", str(repo)], env={"NO_COLOR": "1", "FORCE_COLOR": "1"}
    )
    assert clean.exit_code == 0 and "\x1b" not in clean.stdout
    assert "0 findings | 1 check evaluated" in clean.stdout
    empty = DiagnosticsReport(RepositoryIdentity("a" * 64), Coverage.COMPLETE)
    monkeypatch.setattr(service, "run_diagnostics", lambda path: empty)
    result = runner.invoke(app, ["diagnose", "--no-color"])
    assert result.exit_code == 0
    assert "No applicable checks were evaluated" in result.stdout


def test_non_python_is_partial(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    result = runner.invoke(app, ["diagnose", str(tmp_path), "--verbose"])
    assert result.exit_code == 9
    assert "PARTIAL ANALYSIS" in result.stdout
    assert "5 unknown" in result.stdout and "scope unclear" in result.stdout
    assert "No checks could be evaluated" in result.stdout
