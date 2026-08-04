import os
import py_compile
import re
import tempfile

import pytest

from spawn.templates.mcp_server import MCPServerTemplate

# ─── Basic instantiation ──────────────────────────────────────────────────


def test_mcp_template_name():
    t = MCPServerTemplate()
    assert t.name == "MCP Server"


def test_mcp_template_default_extras():
    t = MCPServerTemplate()
    assert t.extras == []


# ─── Folders ─────────────────────────────────────────────────────────────


def test_mcp_folders():
    t = MCPServerTemplate()
    for required in ["src", "tests"]:
        assert required in t.folders, f"Missing folder: {required}"


# ─── Files ───────────────────────────────────────────────────────────────

REQUIRED_FILES = [
    "src/server.py",
    "src/__init__.py",
    "tests/test_server.py",
    "tests/__init__.py",
    ".env.example",
]


def test_mcp_required_files():
    t = MCPServerTemplate()
    paths = [p for p, _ in t.starter_files]
    for f in REQUIRED_FILES:
        assert f in paths, f"Missing file: {f}"


# ─── Content checks ──────────────────────────────────────────────────────


def test_server_content_has_fastmcp():
    t = MCPServerTemplate()
    files = dict(t.starter_files)
    server = files["src/server.py"]
    assert "FastMCP" in server


def test_server_content_has_tool_decorator():
    t = MCPServerTemplate()
    files = dict(t.starter_files)
    server = files["src/server.py"]
    assert "@mcp.tool()" in server


def test_server_content_has_resource_decorator():
    t = MCPServerTemplate()
    files = dict(t.starter_files)
    server = files["src/server.py"]
    assert "@mcp.resource(" in server


# ─── Dependencies ────────────────────────────────────────────────────────


def test_mcp_default_dependencies():
    t = MCPServerTemplate()
    assert t.get_dependencies() == ["mcp"]


def test_mcp_pytest_extra():
    t = MCPServerTemplate(extras=["pytest"])
    assert "pytest" in t.get_dependencies()


def test_mcp_ruff_extra():
    t = MCPServerTemplate(extras=["ruff"])
    assert "ruff" in t.get_dependencies()


# ─── Readme ──────────────────────────────────────────────────────────────


def test_mcp_readme_not_none():
    t = MCPServerTemplate()
    readme = t.get_readme_content({"project_name": "my-server"})
    assert readme is not None


def test_mcp_readme_contains_project_name():
    t = MCPServerTemplate()
    readme = t.get_readme_content({"project_name": "my-server"})
    assert "my-server" in readme


def test_mcp_readme_format_map_does_not_raise():
    """Critical: verifies the JSON example braces are correctly escaped in Phase 1."""
    t = MCPServerTemplate()
    # Must not raise KeyError or ValueError due to unescaped braces
    readme = t.get_readme_content({"project_name": "my-server"})
    assert isinstance(readme, str)
    assert len(readme) > 0


# ─── Compile checks ──────────────────────────────────────────────────────

PYTHON_FILES = [
    "src/server.py",
    "tests/test_server.py",
]


@pytest.mark.parametrize("filepath", PYTHON_FILES)
def test_file_is_valid_python(filepath):
    t = MCPServerTemplate()
    files = dict(t.starter_files)
    content = files[filepath].format_map({"project_name": "test-mcp"})
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        fname = f.name
    try:
        py_compile.compile(fname, doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"{filepath} is not valid Python: {e}") from e
    finally:
        os.unlink(fname)


@pytest.mark.parametrize("filepath", PYTHON_FILES)
def test_no_unescaped_braces(filepath):
    t = MCPServerTemplate()
    files = dict(t.starter_files)
    content = files[filepath]
    singles = re.findall(r"(?<!\{)\{(?!\{)([^}]*)\}(?!\})", content)
    bad = [s for s in singles if s != "project_name"]
    assert not bad, f"{filepath} has unescaped braces: {bad}"


# ─── next_steps ──────────────────────────────────────────────────────────


def test_mcp_next_steps_has_src_server():
    t = MCPServerTemplate()
    assert any("src.server" in s for s in t.next_steps)
