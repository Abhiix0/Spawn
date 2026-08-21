import json
from contextlib import contextmanager
from unittest.mock import patch

from spawn import __version__
from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.mcp_server import MCPServerTemplate


def _cfg(
    name: str = "my-mcp",
    extras: list[str] | None = None,
) -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="mcp",
        use_git=False,
        extras=extras or [],
    )


@contextmanager
def _mock_uv_and_install():
    with patch("spawn.generators.project_generator.install_packages"), \
         patch("spawn.generators.project_generator.initialize_uv"), \
         patch.object(MCPServerTemplate, "post_install"):
        yield


# ─── Structure ───────────────────────────────────────────────────────────


def test_mcp_creates_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-mcp").is_dir()


def test_mcp_creates_src_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-mcp" / "src").is_dir()


def test_mcp_creates_tests_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-mcp" / "tests").is_dir()


# ─── Files ───────────────────────────────────────────────────────────────


def test_mcp_creates_server_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-mcp" / "src" / "server.py").exists()


def test_mcp_creates_test_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-mcp" / "tests" / "test_server.py").exists()


def test_mcp_creates_env_example(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-mcp" / ".env.example").exists()


# ─── Content ─────────────────────────────────────────────────────────────


def test_mcp_readme_has_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="my-mcp-tool"))
    readme = (tmp_path / "my-mcp-tool" / "README.md").read_text(encoding="utf-8")
    assert "my-mcp-tool" in readme


# ─── meta.json ───────────────────────────────────────────────────────────


def test_mcp_meta_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    meta = json.loads(
        (tmp_path / "my-mcp" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "mcp"
    assert meta["framework"] is None
    assert meta["provider"] is None
    assert meta["spawn_version"] == __version__


# ─── Dependencies ────────────────────────────────────────────────────────


def test_mcp_install_packages_called_with_correct_deps(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("spawn.generators.project_generator.install_packages") as mock_install, \
         patch("spawn.generators.project_generator.initialize_uv"), \
         patch.object(MCPServerTemplate, "post_install"):
        ProjectGenerator().generate(_cfg())
    args = mock_install.call_args[0][1]
    assert "mcp" in args


# ─── AGENTS.md ───────────────────────────────────────────────────────────


def test_mcp_creates_agents_md(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-mcp" / "AGENTS.md").is_file()


def test_mcp_agents_md_contains_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="test-mcp-x"))
    content = (tmp_path / "test-mcp-x" / "AGENTS.md").read_text(encoding="utf-8")
    assert "test-mcp-x" in content
