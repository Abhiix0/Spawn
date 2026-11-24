"""CLI and terminal compatibility tests for the onboarding report."""

from __future__ import annotations

import io
import json
import re
import warnings
from pathlib import Path

import pytest
from fixtures.onboard_repository import materialize
from rich.cells import cell_len
from rich.console import Console
from typer.testing import CliRunner

from spawn.cli import onboard_render
from spawn.cli.app import app
from spawn.inspection import InspectionError
from spawn.inspection import onboarding as composition
from spawn.onboarding import build_onboarding_report

runner = CliRunner()
GOLDENS = Path(__file__).parent / "fixtures/static/onboarding"


@pytest.fixture
def repo(tmp_path):
    return materialize(tmp_path)


def test_default_path_and_listing(repo, monkeypatch):
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["onboard"])
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.startswith("SPAWN / ONBOARD\napi-demo\n")
    assert "python -m uvicorn app.main:app" in result.stdout
    assert str(repo) not in result.stdout
    assert (
        "onboard   Find entry points and developer commands"
        in runner.invoke(app, []).stdout
    )


def test_help_and_bad_flag():
    help_result = runner.invoke(app, ["onboard", "--help"])
    assert help_result.exit_code == 0
    for option in ("--json", "--verbose", "--no-color"):
        assert option in help_result.stdout
    bad = runner.invoke(app, ["onboard", "--bogus"])
    assert bad.exit_code == 2
    assert "--bogus" in bad.stderr


@pytest.mark.parametrize("name", ["missing", "README.md"])
@pytest.mark.parametrize("options", [[], ["--json"]])
def test_invalid_root_stderr_only(repo, name, options):
    result = runner.invoke(app, ["onboard", str(repo / name), *options])
    assert result.exit_code == 7
    assert result.stdout == ""
    assert "readable directory" in result.stderr
    assert str(repo) not in result.stderr


@pytest.mark.parametrize(
    ("error", "code", "message"),
    [
        (InspectionError("private diagnostic"), 7, "readable directory"),
        (PermissionError("private diagnostic"), 10, "Unexpected error"),
        (KeyboardInterrupt(), 130, "Cancelled."),
    ],
)
def test_runtime_errors_suppress_details(repo, monkeypatch, error, code, message):
    def fail(*args):
        raise error

    monkeypatch.setattr("spawn.onboarding.build_onboarding_report", fail)
    result = runner.invoke(app, ["onboard", str(repo), "--json"])
    assert result.exit_code == code
    assert result.stdout == ""
    assert message in result.stderr
    assert "private diagnostic" not in result.stderr


def test_fatal_discovery_exits_7(repo, monkeypatch):
    def fail(*args):
        raise InspectionError(f"Cannot scan {repo}")

    monkeypatch.setattr(composition, "discover_repository", fail)
    result = runner.invoke(app, ["onboard", str(repo), "--json"])
    assert result.exit_code == 7
    assert result.stdout == ""
    assert str(repo) not in result.stderr


def test_unreadable_root_exits_7(repo, monkeypatch):
    import os

    scandir = os.scandir

    def deny(path):
        if path == repo.resolve():
            raise PermissionError("private permission detail")
        return scandir(path)

    with monkeypatch.context() as guard:
        guard.setattr(os, "scandir", deny)
        result = runner.invoke(app, ["onboard", str(repo), "--json"])
    assert result.exit_code == 7
    assert result.stdout == ""
    assert "readable directory" in result.stderr
    assert "private permission detail" not in result.stderr


def test_empty_root_offers_next_step(tmp_path):
    human = runner.invoke(app, ["onboard", str(tmp_path)])
    assert human.exit_code == 0
    assert "No supported commands found." in human.stdout
    assert "Not detected" in human.stdout
    assert "No supported entry point found" in human.stdout
    assert "PROJECT STRUCTURE" not in human.stdout
    assert "NOTES" not in human.stdout
    machine = runner.invoke(app, ["onboard", str(tmp_path), "--json"])
    report = json.loads(machine.stdout)
    assert report["status"] == "complete"
    assert report["entry_points"] == []
    assert all(
        row["status"] == "unknown" and row["argv"] is None for row in report["commands"]
    )


def test_partial_report_sends_diagnostics_to_stderr(repo):
    secret = "SPAWN_ONBOARD_FAKE_SECRET"
    (repo / "pyproject.toml").write_text(f"[project\n{secret}", encoding="utf-8")
    args = ["onboard", str(repo), "--json"]
    result = runner.invoke(app, args)
    detailed = runner.invoke(app, [*args, "--verbose"])
    assert result.exit_code == detailed.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "partial"
    assert payload["diagnostic_counts"]["warning"] > 0
    assert "Use --verbose" in result.stderr
    assert "onboard.entry_points.file_skipped (pyproject.toml)" in detailed.stderr
    assert secret not in result.output + detailed.output
    assert str(repo) not in result.output + detailed.output
    assert "\x1b" not in detailed.stdout
    terminal = runner.invoke(app, ["onboard", str(repo)])
    assert terminal.exit_code == 0
    assert "~ Repository onboarding partial" in terminal.stdout
    assert "Repository onboarding complete" not in terminal.stdout


def test_source_parser_warnings_do_not_escape_as_raw_diagnostics(repo):
    (repo / "app" / "backslashes.py").write_text(
        r"pattern = '\q'" + "\n", encoding="utf-8"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", SyntaxWarning)
        result = runner.invoke(app, ["onboard", str(repo), "--json", "--verbose"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "complete"
    assert result.stderr == ""


def test_json_golden_roundtrip_and_one_discovery(repo, monkeypatch):
    calls = []
    real = composition.discover_repository

    def discover(target):
        calls.append(target)
        return real(target)

    monkeypatch.setattr(composition, "discover_repository", discover)
    monkeypatch.setenv("FORCE_COLOR", "1")
    result = runner.invoke(app, ["onboard", str(repo), "--json"], color=True)
    assert result.exit_code == 0
    assert len(calls) == 1
    assert not result.stderr
    assert "\x1b" not in result.stdout and str(repo) not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["generated_at"]
    payload["generated_at"] = "2000-01-01T00:00:00+00:00"
    assert json.dumps(payload, indent=2) + "\n" == (
        GOLDENS / "api-demo.json"
    ).read_text(encoding="utf-8")
    json.dumps(payload).encode("utf-8")
    for group in ("entry_points", "commands", "languages", "frameworks"):
        for row in payload[group]:
            assert all("\\" not in item["path"] for item in row["evidence"])


def test_verbose_preserves_alternatives_and_supporting_evidence(repo):
    compact = runner.invoke(app, ["onboard", str(repo)])
    verbose = runner.invoke(app, ["onboard", str(repo), "--verbose"])
    assert compact.exit_code == verbose.exit_code == 0
    assert "uv sync --locked" in compact.stdout
    assert "pip install ." not in compact.stdout
    assert "pip install ." in verbose.stdout
    assert "Evidence" in verbose.stdout and "app/main.py:2" in verbose.stdout


@pytest.mark.parametrize("width", [60, 80, 120])
def test_terminal_capture(repo, width, monkeypatch):
    monkeypatch.setenv("COLUMNS", str(width))
    result = runner.invoke(app, ["onboard", str(repo), "--no-color"], color=True)
    assert result.exit_code == 0
    assert result.stdout == (GOLDENS / f"terminal-{width}.txt").read_text(
        encoding="utf-8"
    )
    assert "\x1b" not in result.stdout
    assert all(cell_len(line) <= width for line in result.stdout.splitlines())


def test_color_and_plain_terminal_share_text(repo, monkeypatch):
    report = build_onboarding_report(repo)
    stream = io.StringIO()
    onboard_render.render_onboarding(
        report,
        Console(file=stream, width=80, force_terminal=True, color_system="truecolor"),
    )
    styled = stream.getvalue()
    assert "\x1b[" in styled
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("NO_COLOR", "1")
    result = runner.invoke(app, ["onboard", str(repo)], color=True)
    assert "\x1b" not in result.stdout
    assert result.stdout == re.sub(r"\x1b\[[0-9;]*m", "", styled)
    monkeypatch.delenv("NO_COLOR")
    redirected = runner.invoke(app, ["onboard", str(repo)], color=True)
    assert redirected.stdout == result.stdout


def test_long_module_command_remains_copyable(repo, monkeypatch):
    module = "long_" + "service_" * 9 + "api"
    (repo / "app" / f"{module}.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8"
    )
    monkeypatch.setenv("COLUMNS", "60")
    result = runner.invoke(app, ["onboard", str(repo), "--verbose"])
    assert result.exit_code == 0
    assert f"python -m uvicorn app.{module}:app\n" in result.stdout


def test_wrapped_paths_remain_visible_while_compact_lists_show_counts(
    repo, monkeypatch
):
    monkeypatch.setenv("COLUMNS", "60")
    for index in range(5):
        (repo / f"folder-{index}").mkdir()
    nested = repo / ("service" * 10)
    nested.mkdir()
    (nested / "requirements.txt").write_text("pytest\n", encoding="utf-8")

    compact = runner.invoke(app, ["onboard", str(repo), "--no-color"])
    verbose = runner.invoke(app, ["onboard", str(repo), "--no-color", "--verbose"])
    assert compact.exit_code == verbose.exit_code == 0
    assert "more results with --verbose." in compact.stdout
    assert "folder-4/" not in compact.stdout
    assert "folder-4/" in verbose.stdout
    unwrapped = re.sub(r"\n {19}", "", verbose.stdout)
    assert f"{nested.name}/requirements.txt" in unwrapped
    assert all(cell_len(line) <= 60 for line in verbose.stdout.splitlines())


def test_declared_and_candidate_commands_show_distinct_markers(repo):
    manifest = repo / "pyproject.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + '\n[project.scripts]\nserve = "app.main:main"\n',
        encoding="utf-8",
    )
    (repo / "app/main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\ndef main():\n    pass\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["onboard", str(repo), "--no-color"])
    assert result.exit_code == 0
    assert re.search(r"^  \+ Run +serve$", result.stdout, re.MULTILINE)
    assert re.search(r"^  ~ Install +uv sync --locked$", result.stdout, re.MULTILINE)
    assert "Runtime not checked." in result.stdout


def test_django_compact_run_prefers_server_without_reordering_json(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\ndependencies = ["django"]\n', encoding="utf-8"
    )
    (tmp_path / "manage.py").write_text(
        "import os\nimport sys\n"
        "from django.core.management import execute_from_command_line\n"
        'os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")\n'
        'if __name__ == "__main__":\n    execute_from_command_line(sys.argv)\n',
        encoding="utf-8",
    )
    (tmp_path / "config").mkdir()
    (tmp_path / "config/settings.py").write_text(
        "INSTALLED_APPS = []\n", encoding="utf-8"
    )

    args = ["onboard", str(tmp_path)]
    compact = runner.invoke(app, args)
    verbose = runner.invoke(app, [*args, "--verbose"])
    machine = runner.invoke(app, [*args, "--json"])
    assert compact.exit_code == verbose.exit_code == machine.exit_code == 0
    assert re.search(
        r"^  ~ Run +python manage.py runserver$", compact.stdout, re.MULTILINE
    )
    assert "python -m manage" not in compact.stdout
    assert "python -m manage" in verbose.stdout
    assert "python manage.py runserver" in verbose.stdout
    assert [
        command["argv"]
        for command in json.loads(machine.stdout)["commands"]
        if command["category"] == "start"
    ] == [["python", "-m", "manage"], ["python", "manage.py", "runserver"]]


def test_offline_no_execution_no_writes_and_secret_values(repo, monkeypatch):
    canary = "SPAWN_ONBOARD_FAKE_CREDENTIAL"
    (repo / ".env").write_text(f"SECRET={canary}\n", encoding="utf-8")
    (repo / "Makefile").write_text(
        f"test:\n\tpytest; echo {canary}\n", encoding="utf-8"
    )
    (repo / "app" / "side_effect.py").write_text(
        'from pathlib import Path\nPath(__file__).with_name("ran").touch()\n',
        encoding="utf-8",
    )
    before = {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    }

    def forbidden(*args, **kwargs):
        pytest.fail("Inspection attempted network access or execution")

    with monkeypatch.context() as guard:
        for name in ("subprocess.Popen", "socket.create_connection", "os.system"):
            guard.setattr(name, forbidden)
        result = runner.invoke(app, ["onboard", str(repo), "--json", "--verbose"])
    assert result.exit_code == 0
    assert canary not in result.output and "pytest; echo" not in result.output
    assert {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file()
    } == before


def test_symlink_target_does_not_appear(repo):
    outside = repo.parent / "outside.py"
    outside.write_text(
        "from flask import Flask\napp = Flask(__name__)\n", encoding="utf-8"
    )
    try:
        (repo / "linked.py").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    result = runner.invoke(app, ["onboard", str(repo), "--json", "--verbose"])
    assert result.exit_code == 0
    assert "flask" not in result.stdout and "linked.py" not in result.stdout
    assert "discovery.symlink_skipped (linked.py)" in result.stderr
    assert str(outside) not in result.output
