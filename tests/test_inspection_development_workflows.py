"""Fixture coverage for offline workflow discovery and legacy compatibility."""

from dataclasses import asdict, replace
import json

import pytest

from fixtures import inspection_corpus
from spawn.inspection import onboarding, run_inspection, to_json
from spawn.inspection import development_workflows as workflows
from spawn.inspection._reading import MAX_FILE_SIZE
from spawn.inspection.discovery import discover_repository, validate_inspection_root
from spawn.inspection.entry_points import PythonEntryPoints


@pytest.fixture
def repository(tmp_path):
    def build(files):
        for name, content in files.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode() if isinstance(content, str) else content)
        return tmp_path

    return build


def _commands(root):
    return onboarding.inspect_python_onboarding(root).workflows.commands


def _rows(commands, category):
    return [
        (row.argv, row.status, row.cwd) for row in commands if row.category == category
    ]


def test_explicit_wrappers_rank_before_candidates_and_preserve_alternatives(repository):
    root = repository(
        {
            "Makefile": ".PHONY: test lint\ntest:\n\t@uv run pytest -q\nlint:\n\truff check .\n",
            "pytest.ini": "[pytest]\naddopts = -q\n",
            "pyproject.toml": """
[tool.ruff]
[tool.hatch.envs.default.scripts]
test = "pytest tests"
format = ["ruff format ."]
""",
            "tox.ini": """
[tox]
envlist = py312
[testenv]
commands = pytest {posargs}
[testenv:py312]
commands =
    python -m pytest -q tests
""",
        }
    )
    commands = _commands(root)
    assert _rows(commands, "test") == [
        (("hatch", "run", "test"), "explicit", "."),
        (("make", "-f", "Makefile", "test"), "explicit", "."),
        (("tox", "-e", "py312"), "explicit", "."),
        (("python", "-m", "pytest"), "candidate", "."),
        (("tox",), "candidate", "."),
    ]
    assert _rows(commands, "lint") == [
        (("make", "-f", "Makefile", "lint"), "explicit", "."),
        (("ruff", "check", "."), "candidate", "."),
    ]
    assert _rows(commands, "format")[0] == (("hatch", "run", "format"), "explicit", ".")
    assert (
        next(
            item for item in commands if item.argv == ("make", "-f", "Makefile", "test")
        )
        .evidence[0]
        .detail
        == "line 2"
    )


def test_several_managers_and_nested_working_directories(repository):
    root = repository(
        {
            "uv.lock": "contents are not parsed",
            "poetry.lock": "",
            "Pipfile.lock": "",
            "requirements-dev.txt": "pytest>=7\nruff~=0.5\n",
            "pyproject.toml": """
[project]
name = "project"
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
[tool.uv]
[tool.poetry]
""",
            "services/worker/requirements.txt": "pytest\n",
        }
    )
    commands = _commands(root)
    assert set(_rows(commands, "install")) == {
        (("uv", "sync", "--locked"), "candidate", "."),
        (("poetry", "install"), "candidate", "."),
        (("pipenv", "sync"), "candidate", "."),
        (("python", "-m", "pip", "install", "."), "candidate", "."),
        (
            ("python", "-m", "pip", "install", "-r", "requirements-dev.txt"),
            "candidate",
            ".",
        ),
        (
            ("python", "-m", "pip", "install", "-r", "requirements.txt"),
            "candidate",
            "services/worker",
        ),
    }
    uv = next(item for item in commands if item.argv == ("uv", "sync", "--locked"))
    assert {e.path for e in uv.evidence} == {"pyproject.toml", "uv.lock"}
    assert _rows(commands, "test") == [
        (("python", "-m", "pytest"), "candidate", "."),
        (("python", "-m", "pytest"), "candidate", "services/worker"),
    ]
    assert _rows(commands, "lint") == [(("ruff", "check", "."), "candidate", ".")]


def test_console_and_src_layout_framework_candidates(repository):
    root = repository(
        {
            "services/backend/pyproject.toml": """
[project]
name = "backend"
[project.scripts]
serve-local = "web.cli:main"
missing = "web.cli:no_such_object"
""",
            "services/backend/src/web/api.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "services/backend/src/web/flask_app.py": "from flask import Flask\ndef create_app():\n    return Flask(__name__)\n",
            "services/backend/src/web/cli.py": "def main():\n    pass\n",
            "services/backend/src/web/__main__.py": "from .cli import main\nmain()\n",
        }
    )
    assert set(_rows(_commands(root), "start")) == {
        (("serve-local",), "explicit", "services/backend"),
        (
            ("python", "-m", "uvicorn", "web.api:app", "--app-dir", "src"),
            "candidate",
            "services/backend",
        ),
        (
            ("python", "-m", "flask", "--app", "web.flask_app:create_app", "run"),
            "candidate",
            "services/backend",
        ),
        (("python", "-m", "web"), "candidate", "services/backend/src"),
        (None, "unknown", "services/backend"),
    }


def test_django_manage_and_wsgi_alternatives(repository):
    setup = 'import os\nos.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")\n'
    root = repository(
        {
            "backend/pyproject.toml": '[project]\ndependencies = ["gunicorn"]\n',
            "backend/manage.py": setup
            + 'from django.core.management import execute_from_command_line\nif __name__ == "__main__":\n    execute_from_command_line()\n',
            "backend/config/settings.py": "INSTALLED_APPS = []\n",
            "backend/config/wsgi.py": setup
            + "from django.core.wsgi import get_wsgi_application\napplication = get_wsgi_application()\n",
        }
    )
    assert (("python", "manage.py", "runserver"), "candidate", "backend") in _rows(
        _commands(root), "start"
    )
    assert (("gunicorn", "config.wsgi:application"), "candidate", "backend") in _rows(
        _commands(root), "start"
    )


def test_dynamic_recipes_and_credential_values_stay_inert(repository, monkeypatch):
    secret = "SPAWN_PHASE1B_NONREAL_CANARY"
    root = repository(
        {
            "Makefile": f"test:\n\tpytest; echo {secret} > marker\nlint:\n\t$(shell echo {secret})\n",
            "pyproject.toml": f"""
[tool.hatch.envs.default.scripts]
test = "pytest --token={secret}"
format = ["ruff format .", "echo {secret}"]
""",
            "requirements.txt": f"example @ https://user:{secret}@example.invalid/package\n",
            ".env": f"SECRET={secret}",
            "app.py": 'from pathlib import Path\nPath(__file__).with_name("marker").write_text("ran")\n',
        }
    )
    before = {path.name: path.read_bytes() for path in root.iterdir()}

    def forbidden(*args, **kwargs):
        pytest.fail("inspection attempted process or network access")

    with monkeypatch.context() as guard:
        for name in ("os.system", "socket.create_connection", "subprocess.Popen"):
            guard.setattr(name, forbidden)
        result = onboarding.inspect_python_onboarding(root)
    output = json.dumps(asdict(result.workflows))
    assert secret not in output and "example.invalid" not in output
    assert "shell echo" not in output and "> marker" not in output
    assert not (root / "marker").exists()
    assert {path.name: path.read_bytes() for path in root.iterdir()} == before
    for category in ("test", "lint", "format"):
        assert _rows(result.workflows.commands, category) == [(None, "unknown", ".")]


@pytest.mark.parametrize(
    "makefile",
    [
        "test: setup\n\tpytest\n",
        "test:\n\tpytest\ntest:\n\tpytest -q\n",
        "include other.mk\ntest:\n\tpytest\n",
        "VALUE := $(shell echo inert)\ntest:\n\tpytest\n",
        "SHELL := custom-shell\ntest:\n\tpytest\n",
        "test: ; pytest\n",
    ],
)
def test_nonstatic_make_targets_are_unknown(repository, makefile):
    assert _rows(_commands(repository({"Makefile": makefile})), "test") == [
        (None, "unknown", "."),
    ]


def test_malformed_inputs_and_large_configs_are_skipped(repository, monkeypatch):
    root = repository(
        {
            "pyproject.toml": "[project\n",
            "pytest.ini": "invalid ini",
            "tox.ini": "[testenv]\ncommands = pytest\ncommands = echo repeat",
            "Makefile": b"#" * (MAX_FILE_SIZE + 1),
            "uv.lock": "lock contents are intentionally unread",
            ".venv/requirements.txt": "pytest\n",
            ".git/Makefile": "lint:\n\truff check .\n",
        }
    )
    target = validate_inspection_root(root)
    inventory = discover_repository(target)
    seen = []
    real = workflows.read_inventory_text

    def reader(root, rel):
        seen.append(rel)
        return real(root, rel)

    monkeypatch.setattr(workflows, "read_inventory_text", reader)
    empty = PythonEntryPoints((), (), False)
    result = workflows.discover_development_workflows(target, inventory, empty)
    assert (
        result.skipped
        == tuple(seen)
        == ("Makefile", "pyproject.toml", "pytest.ini", "tox.ini")
    )
    assert _rows(result.commands, "install") == [
        (("uv", "sync", "--locked"), "candidate", ".")
    ]
    assert all(
        row.status == "unknown" for row in result.commands if row.category != "install"
    )
    monkeypatch.setattr(workflows, "_MAX_CONFIGS", 2)
    assert workflows.discover_development_workflows(target, inventory, empty).truncated


def test_no_config_reports_unknown_for_each_category(repository):
    commands = _commands(repository({"app.py": "value = 1\n"}))
    assert [item.category for item in commands] == list(workflows.CommandCategory)
    assert all(
        item.status == "unknown" and item.argv is None and not item.evidence
        for item in commands
    )


def test_single_inventory_and_legacy_json_equivalence(tmp_path, monkeypatch):
    root = inspection_corpus.materialize("python_project", tmp_path)
    legacy = run_inspection(root)
    found = []
    real = onboarding.discover_repository
    real_commands = onboarding.discover_development_workflows
    real_entries = onboarding.discover_python_entry_points

    def discover(target):
        inventory = real(target)
        found.append(inventory)
        return inventory

    def entries(target, inventory):
        assert inventory is found[0]
        return real_entries(target, inventory)

    def commands(target, inventory, entry_points):
        assert inventory is found[0]
        first = real_commands(target, inventory, entry_points)
        reversed_inventory = replace(inventory, files=tuple(reversed(inventory.files)))
        assert real_commands(target, reversed_inventory, entry_points) == first
        return first

    monkeypatch.setattr(onboarding, "discover_repository", discover)
    monkeypatch.setattr(onboarding, "discover_python_entry_points", entries)
    monkeypatch.setattr(onboarding, "discover_development_workflows", commands)
    result = onboarding.inspect_python_onboarding(root)
    assert len(found) == 1
    assert to_json(
        replace(result.inspection, generated_at=legacy.generated_at)
    ) == to_json(legacy)
