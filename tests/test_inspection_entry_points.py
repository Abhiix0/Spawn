"""Fixture-backed tests for the internal Python entry-point projection."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from spawn.inspection import entry_points
from spawn.inspection._reading import MAX_FILE_SIZE
from spawn.inspection.discovery import discover_repository, validate_inspection_root
from spawn.inspection.models import DetectionState


@pytest.fixture
def repository(tmp_path):
    def build(files):
        for name, content in files.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode() if isinstance(content, str) else content)
        target = validate_inspection_root(tmp_path)
        return target, discover_repository(target)

    return build


def _analyze(repository, files):
    return entry_points.discover_python_entry_points(*repository(files))


def _rows(result):
    return [(row.kind, row.target, row.state) for row in result.entries]


D = DetectionState.DETECTED
U = DetectionState.UNKNOWN


def test_asgi_aliases_nested_apps_and_multiple_targets(repository):
    result = _analyze(
        repository,
        {
            "src/acme/api.py": "from fastapi import FastAPI as Web\nweb = Web()\nadmin = Web()\n",
            "src/acme/nested/service.py": "import starlette.applications as s\napp: object = s.Starlette()\n",
        },
    )
    assert _rows(result) == [
        ("asgi", "acme.api:admin", D),
        ("asgi", "acme.api:web", D),
        ("asgi", "acme.nested.service:app", D),
    ]
    assert result.entries[0].evidence[0].path == "src/acme/api.py"
    assert result.entries[0].evidence[0].detail == "line 3"
    with pytest.raises(FrozenInstanceError):
        result.entries[0].target = "other"


def test_flask_instances_factories_and_dynamic_results(repository):
    result = _analyze(
        repository,
        {
            "web/__init__.py": """
from flask import Flask as App
app = App(__name__)

def create_app():
    from flask import Flask
    instance = Flask(__name__)
    instance.config.update(TESTING=True)
    return instance

def wrapped():
    instance = App(__name__)
    return wrap(instance)

def shadowed(App):
    return App()
""",
        },
    )
    assert _rows(result) == [
        ("flask_app", "web:app", D),
        ("flask_factory", "web:create_app", D),
        ("flask_factory", "web:wrapped", U),
    ]


def test_django_settings_manage_and_server_conventions(repository):
    setup = 'import os\nos.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")\n'
    result = _analyze(
        repository,
        {
            "backend/pyproject.toml": "[project]\nname = 'backend'\n",
            "backend/config/settings.py": "INSTALLED_APPS = []\n",
            "backend/config/asgi.py": setup
            + "from django.core.asgi import get_asgi_application as boot\napplication = boot()\n",
            "backend/config/wsgi.py": setup
            + "from django.core.wsgi import get_wsgi_application\napplication = get_wsgi_application()\n",
            "backend/manage.py": """
import os
import sys

def main():
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        raise
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
""",
        },
    )
    assert _rows(result) == [
        ("django_asgi", "config.asgi:application", D),
        ("django_manage", "backend/manage.py", D),
        ("django_wsgi", "config.wsgi:application", D),
        ("module", "-m manage", D),
    ]
    assert all(
        entry.evidence[-1].path == "backend/config/settings.py"
        for entry in result.entries[:3]
    )


def test_django_missing_dynamic_and_conflicting_settings_are_unknown(repository):
    result = _analyze(
        repository,
        {
            "service/asgi.py": "import os\nfrom django.core.asgi import get_asgi_application\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', choose())\napplication = get_asgi_application()\n",
            "other/wsgi.py": "import os\nfrom django.core.wsgi import get_wsgi_application\nos.environ['DJANGO_SETTINGS_MODULE'] = 'missing.settings'\napplication = get_wsgi_application()\n",
            "manage.py": "# django management\nprint('execute_from_command_line')\n",
        },
    )
    assert _rows(result) == [
        ("django_asgi", "service.asgi:application", U),
        ("django_wsgi", "other.wsgi:application", U),
    ]


def test_console_scripts_and_explicit_module_execution(repository):
    result = _analyze(
        repository,
        {
            "pyproject.toml": """
[project.scripts]
hello = "my.ns.cli:main"
missing = "my.missing:main"
shadowed = "my.ns.cli:rebound"
wrong = "../outside:main"
""",
            "src/my/ns/cli.py": """
def main():
    pass

def rebound():
    pass

rebound = load()
if "__main__" == __name__:
    main()
""",
            "src/my/ns/__main__.py": 'from .cli import main\nif __name__ == "__main__":\n    main()\n',
        },
    )
    assert _rows(result) == [
        ("console_script", "hello -> my.ns.cli:main", D),
        ("console_script", "missing -> my.missing:main", U),
        ("console_script", "shadowed -> my.ns.cli:rebound", U),
        ("console_script", "wrong", U),
        ("module", "-m my.ns", D),
        ("module", "-m my.ns.cli", D),
    ]
    assert len(result.entries[-2].evidence) == 2


def test_ambiguity_ignores_text_and_does_not_crown_a_winner(repository):
    result = _analyze(
        repository,
        {
            "app.py": """
from fastapi import FastAPI
from flask import Flask
app = FastAPI() if flag else Flask(__name__)
rebound = FastAPI()
rebound = load()
broken = Starlette()
# phantom = FastAPI()
example = "if __name__ == '__main__': fake = FastAPI()"
""",
            "src/app.py": "from fastapi import FastAPI\nrebound = FastAPI()\n",
        },
    )
    assert _rows(result) == [
        ("asgi", "app:app", U),
        ("asgi", "app:rebound", U),
        ("asgi", "app:rebound", D),
        ("flask_app", "app:app", U),
    ]


def test_skips_broken_large_unreadable_and_excluded_files(repository, monkeypatch):
    target, inventory = repository(
        {
            "pyproject.toml": "[project.scripts\n",
            "bad.py": "def broken(:\n",
            "invalid.py": b"\xff\xff",
            "large.py": b" " * (MAX_FILE_SIZE + 1),
            "unreadable.py": "from flask import Flask\napp = Flask(__name__)\n",
            "good.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            **{
                f"{directory}/ignored.py": "from fastapi import FastAPI\nignored = FastAPI()\n"
                for directory in (".venv", "node_modules", ".git", "vendor")
            },
        }
    )
    original = entry_points.read_inventory_text
    attempted = []

    def read(root, path):
        attempted.append(path)
        if path == "unreadable.py":
            raise PermissionError
        return original(root, path)

    monkeypatch.setattr(entry_points, "read_inventory_text", read)
    result = entry_points.discover_python_entry_points(target, inventory)
    assert _rows(result) == [("asgi", "good:app", D)]
    assert result.skipped == (
        "bad.py",
        "invalid.py",
        "large.py",
        "pyproject.toml",
        "unreadable.py",
    )
    assert len(set(attempted)) == len(attempted) == 6
    monkeypatch.setattr(entry_points, "_MAX_FILES", 1)
    assert entry_points.discover_python_entry_points(target, inventory).truncated
    monkeypatch.setattr(entry_points, "_MAX_TEXT", 1)
    assert entry_points.discover_python_entry_points(target, inventory).truncated


def test_no_execution_network_writes_or_second_walk(repository, monkeypatch):
    target, inventory = repository(
        {
            "app.py": """
from fastapi import FastAPI
from pathlib import Path
Path(__file__).with_name("executed").write_text("unexpected")
app = FastAPI()
""",
            "other.py": "from flask import Flask\napp = Flask(__name__)\n",
        }
    )

    def forbidden(*args, **kwargs):
        pytest.fail("unexpected execution, network access or traversal")

    before = {name: (target.path / name).read_bytes() for name in inventory.files}
    with monkeypatch.context() as guard:
        for name in ("os.scandir", "subprocess.Popen", "socket.create_connection"):
            guard.setattr(name, forbidden)
        original_open = Path.open

        def read_only(path, mode="r", *args, **kwargs):
            assert mode == "rb"
            return original_open(path, mode, *args, **kwargs)

        guard.setattr(Path, "open", read_only)
        first = entry_points.discover_python_entry_points(target, inventory)
        reversed_files = replace(inventory, files=tuple(reversed(inventory.files)))
        assert (
            entry_points.discover_python_entry_points(target, reversed_files) == first
        )
    assert [row.state for row in first.entries] == [D, D]
    assert {p.name: p.read_bytes() for p in target.path.iterdir()} == before


def test_link_replaced_after_discovery_is_not_read(repository):
    target, inventory = repository({"nested/app.py": "pass\n"})
    app = target.path / "nested/app.py"
    external = target.path / "external"
    external.write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    app.unlink()
    try:
        app.symlink_to(external)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    result = entry_points.discover_python_entry_points(target, inventory)
    assert result.entries == ()
    assert result.skipped == ("nested/app.py",)


def test_empty_repository(repository):
    assert _analyze(repository, {}) == entry_points.PythonEntryPoints((), (), False)
