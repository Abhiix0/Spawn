import json
from contextlib import contextmanager
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.agent import AgentTemplate


def _cfg(
    name: str = "my-agent",
    framework: str = "pydantic-ai",
    provider: str = "openai",
    extras: list[str] | None = None,
) -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="agent",
        use_git=False,
        framework=framework,
        provider=provider,
        extras=extras or [],
    )


@contextmanager
def _mock_uv_and_install():
    with patch("spawn.generators.project_generator.install_packages"), \
         patch("spawn.generators.project_generator.initialize_uv"), \
         patch.object(AgentTemplate, "post_install"):
        yield


# ─── Structure ───────────────────────────────────────────────────────────


def test_agent_creates_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-agent").is_dir()


def test_agent_creates_agent_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-agent" / "src" / "agent").is_dir()


def test_agent_creates_tools_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-agent" / "src" / "tools").is_dir()


def test_agent_creates_prompts_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-agent" / "src" / "prompts").is_dir()


# ─── Files ───────────────────────────────────────────────────────────────


def test_agent_creates_run_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-agent" / "src" / "agent" / "run.py").exists()


def test_agent_creates_calculator(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-agent" / "src" / "tools" / "calculator.py").exists()


def test_agent_creates_agent_prompt_txt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-agent" / "src" / "prompts" / "agent_prompt.txt").exists()


def test_agent_creates_test_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-agent" / "tests" / "test_agent.py").exists()


def test_agent_creates_env_example(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-agent" / ".env.example").exists()


def test_agent_creates_conftest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-agent" / "tests" / "conftest.py").exists()


# ─── Content ─────────────────────────────────────────────────────────────


def test_agent_readme_has_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="super-agent"))
    readme = (tmp_path / "super-agent" / "README.md").read_text(encoding="utf-8")
    assert "super-agent" in readme


def test_agent_readme_has_tool_example(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    readme = (tmp_path / "my-agent" / "README.md").read_text(encoding="utf-8")
    assert "calculator" in readme.lower() or "145" in readme or "tool" in readme.lower()


def test_agent_calculator_has_safe_eval(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    calc = (tmp_path / "my-agent" / "src" / "tools" / "calculator.py").read_text(
        encoding="utf-8"
    )
    assert "__builtins__" in calc


def test_agent_pydantic_ai_env_has_openai_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(framework="pydantic-ai", provider="openai"))
    env = (tmp_path / "my-agent" / ".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in env


def test_agent_pydantic_ai_groq_env_has_groq_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(framework="pydantic-ai", provider="groq"))
    env = (tmp_path / "my-agent" / ".env.example").read_text(encoding="utf-8")
    assert "GROQ_API_KEY" in env


def test_agent_openai_agents_env_has_openai_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(framework="openai-agents", provider="openai"))
    env = (tmp_path / "my-agent" / ".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in env


# ─── meta.json ───────────────────────────────────────────────────────────


def test_agent_meta_json_has_correct_intent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    meta = json.loads(
        (tmp_path / "my-agent" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "agent"
    assert meta["framework"] == "pydantic-ai"
    assert meta["provider"] == "openai"
    assert meta["spawn_version"] == "0.8.0"


def test_agent_meta_json_openai_agents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(
            _cfg(framework="openai-agents", provider="openrouter")
        )
    meta = json.loads(
        (tmp_path / "my-agent" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["framework"] == "openai-agents"
    assert meta["provider"] == "openrouter"


# ─── Dependencies ────────────────────────────────────────────────────────


def test_agent_pydantic_ai_install_packages_called(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("spawn.generators.project_generator.install_packages") as mock_install, \
         patch("spawn.generators.project_generator.initialize_uv"), \
         patch.object(AgentTemplate, "post_install"):
        ProjectGenerator().generate(_cfg())
    args = mock_install.call_args[0][1]
    assert "pydantic-ai" in args
    assert "openai-agents" not in args


def test_agent_openai_agents_install_packages_called(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("spawn.generators.project_generator.install_packages") as mock_install, \
         patch("spawn.generators.project_generator.initialize_uv"), \
         patch.object(AgentTemplate, "post_install"):
        ProjectGenerator().generate(_cfg(framework="openai-agents", provider="openai"))
    args = mock_install.call_args[0][1]
    assert "openai-agents" in args
    assert "pydantic-ai" not in args
