"""Generated-at-test-time inspection corpus (#60).

Trees are materialised into ``tmp_path`` and never committed: ``.gitignore``
swallows ``env/ build/ dist/ .env*``, pytest would collect ``test_*.py``
inside committed trees, ruff would lint fixture ``.py`` and the sdist ships
``tests/``.  A spec is ``{relative path: str | bytes}``; archetypes that need
symlinks, permissions or big files are built by a function instead.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

Spec = dict[str, "str | bytes"]

MAX_FILE_SIZE = 1_000_000  # mirrors spawn.inspection._reading.MAX_FILE_SIZE

PYPROJECT = """\
[project]
name = "demo"
requires-python = ">=3.12"
dependencies = ["httpx"]

[tool.ruff]
line-length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]
"""

PACKAGE_JSON = """\
{"name": "web", "dependencies": {"react": "^18.0.0"},
 "devDependencies": {"typescript": "^5.0.0", "eslint": "^9.0.0"}}
"""

SPAWN_META = (
    '{"intent": "cli", "framework": null, "provider": null,'
    ' "spawn_version": "1.0.9", "created_at": "2026-01-01T00:00:00+00:00",'
    ' "generator": "blueprint", "git": true, "uv": true, "source": null}'
)

SPECS: dict[str, Spec] = {
    "python_project": {
        "pyproject.toml": PYPROJECT,
        "uv.lock": "version = 1\n",
        "src/demo/__init__.py": "VALUE = 1\n",
        "tests/test_demo.py": "def test_x():\n    assert True\n",
        ".github/workflows/ci.yml": "name: ci\non: push\njobs: {}\n",
        "Dockerfile": "FROM python:3.12\n",
    },
    "node_project": {
        "package.json": PACKAGE_JSON,
        "package-lock.json": "{}",
        "tsconfig.json": "{}",
        "src/App.tsx": "import React from 'react';\nexport const App = () => null;\n",
        "src/index.tsx": "export {};\n",
    },
    "monorepo": {
        "services/api/pyproject.toml": PYPROJECT,
        "services/api/app.py": "x = 1\n",
        "web/package.json": PACKAGE_JSON,
        "web/src/main.ts": "export {};\n",
        "tools/go.mod": "module example.com/tools\n\ngo 1.22\n",
        "tools/main.go": "package main\n",
    },
    "empty": {},
    "unknown": {"notes.txt": "hello\n", "data.bin": b"\x00\x01\x02"},
    "config_only": {
        "ruff.toml": "line-length = 100\n",
        ".pre-commit-config.yaml": "repos: []\n",
        "Dockerfile": "FROM scratch\n",
    },
    "malformed": {
        "pyproject.toml": "[project\nname = ",
        "package.json": "{not json",
        "requirements.txt": b"\xff\xfe\x00\x80broken",
        "services/requirements.txt": "flask\n".encode("utf-16"),
        "main.py": "print(1)\n",
        "app.ts": "export {};\n",
    },
    "lockfiles": {
        "package.json": PACKAGE_JSON,
        "yarn.lock": "# yarn lockfile v1\n",
        "package-lock.json": "{}",
        "uv.lock": "version = 1\n",
        "pyproject.toml": PYPROJECT,
    },
    "spawn_generated": {
        ".spawn/meta.json": SPAWN_META,
        "pyproject.toml": PYPROJECT,
        "src/demo/__init__.py": "",
    },
    "spawn_meta_malformed": {
        ".spawn/meta.json": "{oops",
        "pyproject.toml": PYPROJECT,
    },
    "ambiguous_frameworks": {
        "package.json": '{"dependencies": {"express": "^4.0.0"}}',
        "pyproject.toml": '[project]\nname = "m"\ndependencies = ["flask", "fastapi"]\n',
        "server.js": "const express = require('express');\n",
        "app.py": "from flask import Flask\napp = Flask(__name__)\n",
        "examples/demo.py": "import django\n",
    },
}


def _write(root: Path, spec: Spec) -> None:
    for rel, content in spec.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8", newline="")


def _size_limits(root: Path) -> None:
    """Manifests at exactly MAX_FILE_SIZE and one byte over, plus 1 MB of blanks."""
    pad = lambda head, n: (head + b" " * n)[:n]  # noqa: E731
    (root / "ok").mkdir()
    (root / "big").mkdir()
    (root / "ok" / "package.json").write_bytes(
        pad(b'{"dependencies": {"react": "1"}}', MAX_FILE_SIZE)
    )
    (root / "big" / "package.json").write_bytes(
        pad(b'{"dependencies": {"vue": "1"}}', MAX_FILE_SIZE + 1)
    )
    (root / "blank.py").write_bytes(b" \n" * (MAX_FILE_SIZE // 2))


def _special(root: Path) -> None:
    """Excluded trees with decoy manifests; symlinks added by the test if possible."""
    _write(root, {"main.py": "x = 1\n", "pyproject.toml": PYPROJECT})
    for d in ("node_modules/pkg", "build", "dist", ".venv/lib"):
        _write(
            root,
            {
                f"{d}/package.json": '{"dependencies": {"vue": "1"}}',
                f"{d}/decoy.go": "package main\n",
            },
        )
    (root / "real.txt").write_text("x", encoding="utf-8")
    (root / "realdir").mkdir()
    (root / "realdir" / "inner.txt").write_text("x", encoding="utf-8")


BUILDERS: dict[str, Callable[[Path], None]] = {
    "size_limits": _size_limits,
    "special_files": _special,
}

ARCHETYPES = (*SPECS, *BUILDERS)


def materialize(name: str, dest: Path) -> Path:
    """Create archetype ``name`` under ``dest`` and return its root."""
    root = Path(dest) / name
    root.mkdir(parents=True)
    if name in SPECS:
        _write(root, SPECS[name])
    else:
        BUILDERS[name](root)
    return root


def add_symlinks(root: Path) -> bool:
    """Add a file and a dir symlink to ``special_files``; False if unsupported."""
    try:
        os.symlink(root / "real.txt", root / "link.txt")
        os.symlink(root / "realdir", root / "linkdir", target_is_directory=True)
    except (OSError, NotImplementedError):
        return False
    return True
