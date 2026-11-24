"""A small FastAPI repo materialized as data and never imported."""

from pathlib import Path

FILES = {
    "README.md": "# Example FastAPI service\n",
    "pyproject.toml": """\
[project]
name = "api-demo"
dependencies = ["fastapi", "uvicorn"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 88
""",
    "uv.lock": "version = 1\n",
    "app/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
    "tests/test_api.py": "def test_health():\n    assert True\n",
}


def materialize(parent: Path) -> Path:
    root = parent / "api-demo"
    for relative, content in FILES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    return root
