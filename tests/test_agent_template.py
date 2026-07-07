import os
import py_compile
import tempfile

import pytest

from spawn.templates.agent import AgentTemplate, get_supported_providers

# ─── Basic instantiation ──────────────────────────────────────────────────


def test_agent_template_default_name():
    t = AgentTemplate()
    assert t.name == "AI Agent"


def test_agent_template_default_framework():
    t = AgentTemplate()
    assert t.framework == "pydantic-ai"


def test_agent_template_default_provider():
    t = AgentTemplate()
    assert t.provider == "openai"


def test_agent_template_default_extras_empty():
    t = AgentTemplate()
    assert t.extras == []


# ─── Folders and files ───────────────────────────────────────────────────


def test_agent_folders():
    t = AgentTemplate()
    assert "src/agent"   in t.folders
    assert "src/tools"   in t.folders
    assert "src/prompts" in t.folders
    assert "src/config"  in t.folders
    assert "tests"       in t.folders


def test_agent_required_files():
    t = AgentTemplate()
    paths = [p for p, _ in t.starter_files]
    for required in [
        "src/agent/run.py",
        "src/tools/calculator.py",
        "src/prompts/agent_prompt.txt",
        "src/config/settings.py",
        "tests/test_agent.py",
        ".env.example",
    ]:
        assert required in paths, f"Missing: {required}"


def test_agent_has_conftest():
    t = AgentTemplate()
    paths = [p for p, _ in t.starter_files]
    assert "tests/conftest.py" in paths


# ─── Calculator tool ─────────────────────────────────────────────────────


def test_calculator_is_generated():
    t = AgentTemplate()
    files = dict(t.starter_files)
    calc = files["src/tools/calculator.py"]
    assert "calculate" in calc
    assert "__builtins__" in calc  # safe eval pattern


def test_calculator_no_bare_eval():
    """Calculator must use restricted eval, not bare eval."""
    t = AgentTemplate()
    files = dict(t.starter_files)
    calc = files["src/tools/calculator.py"]
    assert '"__builtins__"' in calc or "'__builtins__'" in calc


# ─── Provider maps ───────────────────────────────────────────────────────


def test_pydantic_ai_supports_6_providers():
    providers = get_supported_providers("pydantic-ai")
    assert len(providers) == 6
    for p in ["openai", "anthropic", "gemini", "openrouter", "ollama", "groq"]:
        assert p in providers


def test_openai_agents_supports_2_providers():
    providers = get_supported_providers("openai-agents")
    assert providers == ["openai", "openrouter"]


def test_unknown_framework_defaults_to_openai():
    providers = get_supported_providers("unknown")
    assert "openai" in providers


# ─── ALL_COMBINATIONS parametrized ───────────────────────────────────────

ALL_COMBINATIONS = [
    ("pydantic-ai",   "openai"),
    ("pydantic-ai",   "anthropic"),
    ("pydantic-ai",   "gemini"),
    ("pydantic-ai",   "openrouter"),
    ("pydantic-ai",   "ollama"),
    ("pydantic-ai",   "groq"),
    ("openai-agents", "openai"),
    ("openai-agents", "openrouter"),
]

REQUIRED_FILES = [
    "src/__init__.py",
    "src/agent/__init__.py",
    "src/agent/run.py",
    "src/tools/__init__.py",
    "src/tools/calculator.py",
    "src/prompts/__init__.py",
    "src/config/__init__.py",
    "src/config/settings.py",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/test_agent.py",
    ".env.example",
]


@pytest.mark.parametrize("framework,provider", ALL_COMBINATIONS)
def test_all_combinations_have_required_files(framework, provider):
    t = AgentTemplate(framework=framework, provider=provider)
    paths = [p for p, _ in t.starter_files]
    for req in REQUIRED_FILES:
        assert req in paths, f"{framework}+{provider} missing {req}"


@pytest.mark.parametrize("framework,provider", ALL_COMBINATIONS)
def test_all_combinations_agent_run_compiles(framework, provider):
    t = AgentTemplate(framework=framework, provider=provider)
    files = dict(t.starter_files)
    content = files["src/agent/run.py"].format_map({"project_name": "test"})
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(content)
        fname = f.name
    try:
        py_compile.compile(fname, doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"{framework}+{provider} run.py invalid: {e}") from e
    finally:
        os.unlink(fname)


@pytest.mark.parametrize("framework,provider", ALL_COMBINATIONS)
def test_all_combinations_have_python_dotenv(framework, provider):
    t = AgentTemplate(framework=framework, provider=provider)
    assert "python-dotenv" in t.get_dependencies()


@pytest.mark.parametrize("framework,provider", ALL_COMBINATIONS)
def test_all_combinations_env_has_api_key(framework, provider):
    t = AgentTemplate(framework=framework, provider=provider)
    files = dict(t.starter_files)
    env = files[".env.example"].format_map({"project_name": "test"})
    has_key = any(
        key in env for key in [
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
            "OPENROUTER_API_KEY", "GROQ_API_KEY", "OLLAMA_BASE_URL",
        ]
    )
    assert has_key, f"{framework}+{provider} env missing API key"


@pytest.mark.parametrize("framework,provider", ALL_COMBINATIONS)
def test_all_combinations_readme_contains_project_name(framework, provider):
    t = AgentTemplate(framework=framework, provider=provider)
    readme = t.get_readme_content({"project_name": "my-agent"})
    assert readme is not None
    assert "my-agent" in readme


# ─── Dependencies ────────────────────────────────────────────────────────


def test_pydantic_ai_groq_uses_extras():
    t = AgentTemplate(framework="pydantic-ai", provider="groq")
    deps = t.get_dependencies()
    assert "pydantic-ai[groq]" in deps


def test_openai_agents_uses_openai_agents_package():
    t = AgentTemplate(framework="openai-agents", provider="openai")
    deps = t.get_dependencies()
    assert "openai-agents" in deps
    assert "pydantic-ai" not in deps


def test_pytest_extra_adds_pytest():
    t = AgentTemplate(extras=["pytest"])
    assert "pytest" in t.get_dependencies()


def test_ruff_extra_adds_ruff():
    t = AgentTemplate(extras=["ruff"])
    assert "ruff" in t.get_dependencies()


# ─── next_steps ──────────────────────────────────────────────────────────


def test_next_steps_has_rename_instruction():
    t = AgentTemplate()
    assert any("Rename" in s for s in t.next_steps)


def test_next_steps_has_run_command():
    t = AgentTemplate()
    assert any("src/main.py" in s for s in t.next_steps)
