"""Exercise the shipping registry against repositories treated strictly as data."""

import hashlib
import os
import socket
import struct
import subprocess
from pathlib import Path

import pytest

from spawn.diagnostics import service
from spawn.diagnostics.models import Evidence, Outcome, Severity
from spawn.diagnostics.serialization import to_json
from spawn.inspection import _reading
from tests.fixtures.onboard_repository import FILES

_PROJECT = '[project]\nname = "demo"\n'
_FLASK = _PROJECT + 'dependencies = ["flask"]\n'
_CLI = """\
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
[tool.setuptools]
py-modules = ["cli"]
[project]
name = "cli"
[project.scripts]
cli = "cli:main"
"""
_PATHS = "[tool.pytest.ini_options]\ntestpaths = "
_CASES = [
    (
        "py-entry-001",
        {"pyproject.toml": _CLI, "cli.py": "def other(): pass\n"},
        {"cli.py": "def main(): pass\n"},
        {"cli.py": "from external import main\n"},
        {"cli.py": "def main(\n"},
        {"pyproject.toml": _PROJECT},
        (Evidence("pyproject.toml", key="project.scripts"), Evidence("cli.py")),
        "Correct the script target",
    ),
    (
        "py-test-001",
        {**FILES, "pyproject.toml": _PROJECT + _PATHS + '["lost"]'},
        {"pyproject.toml": FILES["pyproject.toml"]},
        {"pyproject.toml": _PROJECT + _PATHS + '["lost", "tests/*"]'},
        {"pyproject.toml": _PROJECT + _PATHS + "["},
        {"pyproject.toml": _PROJECT},
        (Evidence("pyproject.toml", key="tool.pytest.ini-options.testpaths"),),
        "Check the testpaths list",
    ),
    (
        "py-test-002",
        {
            "pyproject.toml": _PROJECT + 'dependencies = ["django"]\n',
            "manage.py": "import django\n",
            "Makefile": "test:\n\tpytest -c unit.ini\n",
        },
        {"unit.ini": "[pytest]\n"},
        {"Makefile": "test:\n\tcd tests && pytest -c unit.ini\n"},
        {"Makefile": "test:\npytest -c unit.ini\n"},
        {"Makefile": "test:\n\tpytest\n"},
        (Evidence("Makefile", line=2),),
        "Restore the configuration file",
    ),
    (
        "py-deps-001",
        {"pyproject.toml": _FLASK, "requirements.txt": "-r req/dev.txt\n"},
        {"req/dev.txt": "pytest\n"},
        {"requirements.txt": "-r ${DYNAMIC}\n"},
        {"requirements.txt": "-r\n"},
        {"requirements.txt": "pytest\n"},
        (Evidence("requirements.txt", line=1),),
        "Restore the included requirements file",
    ),
    (
        "py-container-001",
        {
            "pyproject.toml": _PROJECT + 'dependencies = ["starlette"]\n',
            "Dockerfile": "FROM python:3.12 AS build\nUSER app\nFROM python:3.12-slim\nUSER root\n",
        },
        {"Dockerfile": "FROM python:3.12\nUSER 0\nUSER app\n"},
        {"Dockerfile": "FROM python:3.12\nUSER $RUN_AS\n"},
        {"Dockerfile": "FROM\nUSER root\n"},
        {"Dockerfile": None},
        (Evidence("Dockerfile", line=4),),
        "Set the final USER",
    ),
]


def materialize(root, files):
    for name, content in files.items():
        if content is None:
            continue
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")


def outcome(root, rule):
    return next(
        item for item in service.run_diagnostics(root).outcomes if item.rule_id == rule
    )


@pytest.mark.parametrize(
    "rule,positive,negative,ambiguous,malformed,irrelevant,evidence,remedy", _CASES
)
@pytest.mark.parametrize(
    "state", ["positive", "negative", "ambiguous", "malformed", "irrelevant"]
)
def test_catalog(
    tmp_path,
    rule,
    positive,
    negative,
    ambiguous,
    malformed,
    irrelevant,
    evidence,
    remedy,
    state,
):
    patch, expected = {
        "positive": ({}, Outcome.FINDING),
        "negative": (negative, Outcome.PASS),
        "ambiguous": (ambiguous, Outcome.UNKNOWN),
        "malformed": (malformed, Outcome.UNKNOWN),
        "irrelevant": (irrelevant, Outcome.NOT_APPLICABLE),
    }[state]
    materialize(tmp_path, positive | patch)
    row = outcome(tmp_path, rule)
    assert row.outcome is expected
    if expected is Outcome.FINDING:
        (issue,) = row.findings
        assert set(issue.evidence) == set(evidence)
        assert issue.description.severity is Severity.WARNING
        assert issue.description.recommendation.startswith(remedy)
    else:
        assert not row.findings
        assert bool(row.scope_evidence) == (expected is Outcome.NOT_APPLICABLE)


@pytest.mark.parametrize(
    "extra",
    [
        {"nested/pyproject.toml": _PROJECT},
        {"pytest.ini": "[pytest]\n"},
        {"pyproject.toml": _PROJECT + _PATHS + '[".venv/missing"]'},
        {"pyproject.toml": _PROJECT + _PATHS + '["Tests"]', "tests/sample.py": ""},
        {"pyproject.toml": _PROJECT + _PATHS + '["missing"]\n' + "#" * (64 * 1024)},
    ],
)
def test_testpaths_abstains_on_incomplete_scope(tmp_path, extra):
    materialize(tmp_path, {"pyproject.toml": _PROJECT + _PATHS + '["missing"]'} | extra)
    assert outcome(tmp_path, "py-test-001").outcome is Outcome.UNKNOWN


@pytest.mark.parametrize(
    "source",
    [
        "def __getattr__(name): return lambda: None\n",
        "if True:\n    def main(): pass\n",
        "def other():\n    break\n",
        "def other(x=exec('do not execute')): pass\n",
    ],
)
def test_entry_rejects_dynamic_and_invalid_source(tmp_path, source):
    materialize(tmp_path, {"pyproject.toml": _CLI, "cli.py": source})
    assert outcome(tmp_path, "py-entry-001").outcome is Outcome.UNKNOWN


def test_determinism_and_no_execution_or_secret_output(tmp_path, monkeypatch, capsys):
    canary = "private-test-canary"
    files = {
        "pyproject.toml": _FLASK + _PATHS + '["absent"]',
        "requirements.txt": "-r one.txt\n--requirement=two.txt\n",
        "Makefile": f"test:\n\tpytest -c $(curl https://user:{canary}@example.org)\n",
        "Dockerfile": "FROM python:3.12\nUSER 0\n",
        ".env": canary,
        "app.py": f"raise RuntimeError({canary!r})\n",
    }
    materialize(tmp_path, files)

    def forbidden(*args, **kwargs):
        pytest.fail("Diagnostics attempted forbidden I/O")

    real = _reading._read_from_root

    def only_expected_reads(handle, parts, limit):
        assert parts in {(name,) for name in files if name not in {".env", "app.py"}}
        return real(handle, parts, limit)

    monkeypatch.setattr(_reading, "_read_from_root", only_expected_reads)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    report = service.run_diagnostics(tmp_path)
    assert to_json(report) == to_json(service.run_diagnostics(tmp_path))
    assert [row.rule_id for row in report.findings] == [
        "py-container-001",
        "py-deps-001",
        "py-deps-001",
        "py-test-001",
    ]
    assert [row.evidence[0].line for row in report.findings[1:3]] == [1, 2]
    assert outcome(tmp_path, "py-test-002").outcome is Outcome.UNKNOWN
    assert canary not in repr(report) + to_json(report)
    assert capsys.readouterr() == ("", "")


def test_repository_swap_before_shipping_rule_read(tmp_path, monkeypatch):
    root, outside = tmp_path / "repo", tmp_path / "outside"
    materialize(root, {"pyproject.toml": _FLASK, "requirements.txt": "flask\n"})
    materialize(
        outside,
        {"pyproject.toml": _FLASK, "requirements.txt": "-r private-canary.txt\n"},
    )
    discover = service.discover_repository
    attempts = []
    open_root = _reading._open_root

    def observed_open(path):
        attempts.append(path)
        return open_root(path)

    def swap(*args, **kwargs):
        inventory = discover(*args, **kwargs)
        root.rename(tmp_path / "previous")
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(root), str(outside)],
                capture_output=True,
            )
            if result.returncode or not root.is_junction():
                pytest.skip("Windows junction unavailable")
        else:
            root.symlink_to(outside, target_is_directory=True)
        return inventory

    monkeypatch.setattr(service, "discover_repository", swap)
    monkeypatch.setattr(_reading, "_open_root", observed_open)
    report = service.run_diagnostics(root)
    assert attempts
    assert all(row.outcome is Outcome.UNKNOWN for row in report.outcomes)
    assert not report.findings
    assert "private-canary" not in repr(report) + to_json(report)


def test_git_excluded_target_stays_unknown(tmp_path):
    materialize(
        tmp_path,
        {
            "pyproject.toml": _PROJECT + _PATHS + '["private/tests"]',
            "private/tests/test_unit.py": "",
            ".git/info/exclude": "/private/\n",
        },
    )
    empty_index = struct.pack(">4sII", b"DIRC", 2, 0)
    (tmp_path / ".git/index").write_bytes(
        empty_index + hashlib.sha1(empty_index, usedforsecurity=False).digest()
    )
    item = outcome(tmp_path, "py-test-001")
    assert item.outcome is Outcome.UNKNOWN
    assert not item.findings


def test_valid_cached_requests_charge_aggregate_once(tmp_path):
    from spawn.diagnostics.models import Coverage, Reason
    from spawn.diagnostics.rules import WorkLimits

    materialize(tmp_path, {"pyproject.toml": _PROJECT})
    rules = service.RULES
    allowance = len(rules) * (64 * 1024 + 1)
    report = service._run(
        tmp_path, rules, analyzers=(), limits=WorkLimits(len(rules), allowance, 1000)
    )
    assert report.coverage is Coverage.COMPLETE
    assert all(row.outcome is Outcome.NOT_APPLICABLE for row in report.outcomes)
    report = service._run(
        tmp_path,
        rules,
        analyzers=(),
        limits=WorkLimits(len(rules), allowance - 1, 1000),
    )
    assert report.coverage is Coverage.LIMIT_REACHED
    assert report.outcomes[-1].reason is Reason.LIMIT_REACHED
    assert not report.is_clean
