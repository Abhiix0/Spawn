import os
import py_compile
import tempfile

import pytest

from spawn.templates.chatbot import ChatbotTemplate
from spawn.templates.chatbot.content import (
    ENV_PYDANTIC_GEMINI,
    PYDANTIC_AI_ANTHROPIC_LLM_CONTENT,
    PYDANTIC_AI_GEMINI_LLM_CONTENT,
    PYDANTIC_AI_OLLAMA_LLM_CONTENT,
    PYDANTIC_AI_OPENAI_LLM_CONTENT,
    PYDANTIC_AI_OPENROUTER_LLM_CONTENT,
)

# ─── Construction ─────────────────────────────────────────────────────────


def test_default_framework_and_provider():
    t = ChatbotTemplate()
    assert t.framework == "pydantic-ai"
    assert t.provider == "openai"
    assert t.extras == []


def test_explicit_framework_and_provider():
    t = ChatbotTemplate(framework="litellm", provider="anthropic")
    assert t.framework == "litellm"
    assert t.provider == "anthropic"


def test_openai_sdk_openrouter():
    t = ChatbotTemplate(framework="openai-sdk", provider="openrouter")
    assert t.framework == "openai-sdk"
    assert t.provider == "openrouter"


# ─── Folders ──────────────────────────────────────────────────────────────


def test_folders_include_all_required():
    t = ChatbotTemplate()
    assert "src/chatbot" in t.folders
    assert "src/providers" in t.folders
    assert "src/prompts" in t.folders
    assert "src/memory" in t.folders
    assert "src/config" in t.folders
    assert "tests" in t.folders


# ─── Starter files ────────────────────────────────────────────────────────


def test_starter_files_include_all_required():
    t = ChatbotTemplate()
    paths = [p for p, _ in t.starter_files]
    assert "src/main.py" in paths
    assert "src/chatbot/chat.py" in paths
    assert "src/providers/llm.py" in paths
    assert "src/prompts/system.txt" in paths
    assert "src/memory/history.py" in paths
    assert "src/config/settings.py" in paths
    assert "tests/test_chatbot.py" in paths
    assert ".env.example" in paths


def test_starter_file_paths_are_strings():
    t = ChatbotTemplate()
    for path, _ in t.starter_files:
        assert isinstance(path, str)


def test_system_prompt_is_txt_not_py():
    t = ChatbotTemplate()
    paths = [p for p, _ in t.starter_files]
    assert "src/prompts/system.txt" in paths
    assert "src/prompts/system_prompt.py" not in paths


# ─── LLM content per combination ──────────────────────────────────────────


@pytest.mark.parametrize(
    "framework,provider,expected_import",
    [
        ("pydantic-ai", "openai", "from pydantic_ai import Agent"),
        ("pydantic-ai", "anthropic", "from pydantic_ai import Agent"),
        ("pydantic-ai", "gemini", "from pydantic_ai import Agent"),
        ("pydantic-ai", "openrouter", "from pydantic_ai import Agent"),
        ("pydantic-ai", "ollama", "from pydantic_ai import Agent"),
        ("openai-sdk", "openai", "from openai import OpenAI"),
        ("openai-sdk", "openrouter", "from openai import OpenAI"),
        ("openai-sdk", "gemini", "from openai import OpenAI"),
        ("litellm", "openai", "import litellm"),
        ("litellm", "anthropic", "import litellm"),
        ("litellm", "gemini", "import litellm"),
        ("litellm", "openrouter", "import litellm"),
        ("litellm", "ollama", "import litellm"),
    ],
)
def test_llm_content_import(framework, provider, expected_import):
    t = ChatbotTemplate(framework=framework, provider=provider)
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert expected_import in llm


def test_pydantic_ai_llm_uses_result_output():
    t = ChatbotTemplate(framework="pydantic-ai", provider="openai")
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert "result.output" in llm
    assert "result.data" not in llm


def test_pydantic_ai_no_setdefault_openai_key():
    t = ChatbotTemplate(framework="pydantic-ai", provider="openai")
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert "setdefault" not in llm


# ─── Env example per provider ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "framework,provider,expected_key",
    [
        ("pydantic-ai", "openai", "OPENAI_API_KEY"),
        ("pydantic-ai", "anthropic", "ANTHROPIC_API_KEY"),
        ("pydantic-ai", "gemini", "GOOGLE_API_KEY"),
        ("pydantic-ai", "openrouter", "OPENROUTER_API_KEY"),
        ("pydantic-ai", "ollama", "OLLAMA_BASE_URL"),
        ("openai-sdk", "openai", "OPENAI_API_KEY"),
        ("openai-sdk", "openrouter", "OPENROUTER_API_KEY"),
        ("openai-sdk", "gemini", "GOOGLE_API_KEY"),
        ("litellm", "openai", "OPENAI_API_KEY"),
        ("litellm", "anthropic", "ANTHROPIC_API_KEY"),
        ("litellm", "gemini", "GOOGLE_API_KEY"),
        ("litellm", "openrouter", "OPENROUTER_API_KEY"),
        ("litellm", "ollama", "OLLAMA_API_BASE"),
    ],
)
def test_env_example_correct_key(framework, provider, expected_key):
    t = ChatbotTemplate(framework=framework, provider=provider)
    files = dict(t.starter_files)
    env = files[".env.example"].format_map({"project_name": "test"})
    assert expected_key in env


def test_pydantic_ai_env_has_prefixed_model():
    t = ChatbotTemplate(framework="pydantic-ai", provider="openai")
    files = dict(t.starter_files)
    env = files[".env.example"].format_map({"project_name": "test"})
    assert "MODEL=openai:" in env


def test_openai_sdk_env_has_plain_model():
    t = ChatbotTemplate(framework="openai-sdk", provider="openai")
    files = dict(t.starter_files)
    env = files[".env.example"].format_map({"project_name": "test"})
    assert "MODEL=gpt-4o-mini" in env
    assert "MODEL=openai:" not in env


# ─── Dependencies ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "framework,provider,expected_dep",
    [
        ("pydantic-ai", "openai", "pydantic-ai"),
        ("openai-sdk", "openai", "openai"),
        ("litellm", "openai", "litellm"),
        ("litellm", "anthropic", "litellm"),
    ],
)
def test_dependencies_include_correct_package(framework, provider, expected_dep):
    t = ChatbotTemplate(framework=framework, provider=provider)
    assert expected_dep in t.get_dependencies()


def test_all_variants_include_python_dotenv():
    combos = [
        ("pydantic-ai", "openai"),
        ("pydantic-ai", "anthropic"),
        ("openai-sdk", "openai"),
        ("litellm", "openai"),
    ]
    for fw, pv in combos:
        assert (
            "python-dotenv"
            in ChatbotTemplate(framework=fw, provider=pv).get_dependencies()
        )


def test_extras_add_deps():
    t = ChatbotTemplate(extras=["pytest", "ruff", "rich"])
    deps = t.get_dependencies()
    assert "pytest" in deps
    assert "ruff" in deps
    assert "rich" in deps


def test_no_extras_excludes_optional():
    t = ChatbotTemplate()
    deps = t.get_dependencies()
    assert "pytest" not in deps
    assert "ruff" not in deps
    assert "rich" not in deps


# ─── Rich extra ───────────────────────────────────────────────────────────


def test_rich_extra_uses_rich_main():
    t = ChatbotTemplate(extras=["rich"])
    files = dict(t.starter_files)
    main = files["src/main.py"]
    assert "from rich" in main
    assert "Console" in main


def test_no_rich_uses_plain_main():
    t = ChatbotTemplate()
    files = dict(t.starter_files)
    main = files["src/main.py"]
    assert "from rich" not in main
    assert 'print(f"Bot:' in main


# ─── Memory ───────────────────────────────────────────────────────────────


def test_memory_history_has_required_functions():
    t = ChatbotTemplate()
    files = dict(t.starter_files)
    mem = files["src/memory/history.py"]
    assert "append_user" in mem
    assert "append_assistant" in mem
    assert "get_history" in mem
    assert "clear" in mem


# ─── Conftest ─────────────────────────────────────────────────────────────


def test_conftest_py_is_generated():
    t = ChatbotTemplate()
    paths = [p for p, _ in t.starter_files]
    assert "tests/conftest.py" in paths


def test_conftest_has_autouse_fixture():
    t = ChatbotTemplate()
    files = dict(t.starter_files)
    conftest = files["tests/conftest.py"]
    assert "autouse=True" in conftest
    assert "clear()" in conftest
    assert "reset_memory" in conftest


def test_conftest_is_valid_python():
    from spawn.templates.chatbot.content import CONFTEST_CONTENT

    _assert_valid_python(CONFTEST_CONTENT, "CONFTEST_CONTENT")


# ─── README ───────────────────────────────────────────────────────────────


def test_readme_contains_project_name():
    t = ChatbotTemplate()
    readme = t.get_readme_content({"project_name": "my-bot"})
    assert "my-bot" in readme


def test_readme_mentions_framework_and_provider():
    t = ChatbotTemplate(framework="litellm", provider="anthropic")
    readme = t.get_readme_content({"project_name": "test"})
    assert "Litellm" in readme or "litellm" in readme.lower()
    assert "Anthropic" in readme or "anthropic" in readme.lower()


# ─── Next steps ───────────────────────────────────────────────────────────


def test_next_steps_contain_run_command():
    t = ChatbotTemplate()
    assert any("src.main" in step for step in t.next_steps)


def test_next_steps_mention_env():
    t = ChatbotTemplate()
    assert any(".env" in step for step in t.next_steps)


# ─── pydantic-ai API correctness ────────────────────────────────────────


def test_pydantic_ai_openai_no_api_key_in_run_sync():
    """api_key is not a valid run_sync() kwarg in pydantic-ai 2.x."""
    assert "run_sync(prompt, api_key" not in PYDANTIC_AI_OPENAI_LLM_CONTENT


def test_pydantic_ai_anthropic_no_api_key_in_run_sync():
    """api_key is not a valid run_sync() kwarg in pydantic-ai 2.x."""
    assert "run_sync(prompt, api_key" not in PYDANTIC_AI_ANTHROPIC_LLM_CONTENT


def test_pydantic_ai_gemini_no_api_key_in_run_sync():
    """api_key is not a valid run_sync() kwarg in pydantic-ai 2.x."""
    assert "run_sync(prompt, api_key" not in PYDANTIC_AI_GEMINI_LLM_CONTENT


def test_pydantic_ai_gemini_uses_correct_provider_prefix():
    """pydantic-ai 2.0.0 uses google: not google-gla: for Gemini."""
    assert "google-gla" not in PYDANTIC_AI_GEMINI_LLM_CONTENT
    assert "google:" in PYDANTIC_AI_GEMINI_LLM_CONTENT


def test_env_pydantic_gemini_uses_correct_model_prefix():
    """ENV_PYDANTIC_GEMINI MODEL must match the provider prefix in llm.py."""
    assert "google-gla" not in ENV_PYDANTIC_GEMINI
    assert "MODEL=google:" in ENV_PYDANTIC_GEMINI


def test_pydantic_ai_openrouter_uses_openai_chat_model():
    """Correct pydantic-ai 2.0.0 pattern for custom base_url providers."""
    assert "OpenAIChatModel" in PYDANTIC_AI_OPENROUTER_LLM_CONTENT
    assert "OpenAIProvider" in PYDANTIC_AI_OPENROUTER_LLM_CONTENT
    assert 'model_settings={"provider"' not in PYDANTIC_AI_OPENROUTER_LLM_CONTENT
    assert "model_settings" not in PYDANTIC_AI_OPENROUTER_LLM_CONTENT


def test_pydantic_ai_ollama_uses_openai_chat_model():
    """Correct pydantic-ai 2.0.0 pattern for local Ollama provider."""
    assert "OpenAIChatModel" in PYDANTIC_AI_OLLAMA_LLM_CONTENT
    assert "OpenAIProvider" in PYDANTIC_AI_OLLAMA_LLM_CONTENT
    assert "model_settings" not in PYDANTIC_AI_OLLAMA_LLM_CONTENT


# ─── Python syntax validity ──────────────────────────────────────────────


def _assert_valid_python(content: str, label: str) -> None:
    """Write content to a temp file and verify it compiles."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        fname = f.name
    try:
        py_compile.compile(fname, doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"{label} is not valid Python: {e}") from e
    finally:
        os.unlink(fname)


def test_pydantic_ai_openai_llm_is_valid_python():
    _assert_valid_python(
        PYDANTIC_AI_OPENAI_LLM_CONTENT, "PYDANTIC_AI_OPENAI_LLM_CONTENT"
    )


def test_pydantic_ai_anthropic_llm_is_valid_python():
    _assert_valid_python(
        PYDANTIC_AI_ANTHROPIC_LLM_CONTENT, "PYDANTIC_AI_ANTHROPIC_LLM_CONTENT"
    )


def test_pydantic_ai_gemini_llm_is_valid_python():
    _assert_valid_python(
        PYDANTIC_AI_GEMINI_LLM_CONTENT, "PYDANTIC_AI_GEMINI_LLM_CONTENT"
    )


def test_pydantic_ai_openrouter_llm_is_valid_python():
    _assert_valid_python(
        PYDANTIC_AI_OPENROUTER_LLM_CONTENT, "PYDANTIC_AI_OPENROUTER_LLM_CONTENT"
    )


def test_pydantic_ai_ollama_llm_is_valid_python():
    _assert_valid_python(
        PYDANTIC_AI_OLLAMA_LLM_CONTENT, "PYDANTIC_AI_OLLAMA_LLM_CONTENT"
    )


# ─── result.output used (not result.data) ────────────────────────────────


def test_pydantic_ai_openai_uses_result_output():
    assert "result.output" in PYDANTIC_AI_OPENAI_LLM_CONTENT
    assert "result.data" not in PYDANTIC_AI_OPENAI_LLM_CONTENT


def test_pydantic_ai_anthropic_uses_result_output():
    assert "result.output" in PYDANTIC_AI_ANTHROPIC_LLM_CONTENT
    assert "result.data" not in PYDANTIC_AI_ANTHROPIC_LLM_CONTENT


def test_pydantic_ai_gemini_uses_result_output():
    assert "result.output" in PYDANTIC_AI_GEMINI_LLM_CONTENT
    assert "result.data" not in PYDANTIC_AI_GEMINI_LLM_CONTENT


def test_pydantic_ai_openrouter_uses_result_output():
    assert "result.output" in PYDANTIC_AI_OPENROUTER_LLM_CONTENT


def test_pydantic_ai_ollama_uses_result_output():
    assert "result.output" in PYDANTIC_AI_OLLAMA_LLM_CONTENT


# ─── Memory dual-store ────────────────────────────────────────────────────


def test_memory_has_get_pai_history():
    t = ChatbotTemplate()
    files = dict(t.starter_files)
    mem = files["src/memory/history.py"]
    assert "get_pai_history" in mem
    assert "_pai_history" in mem


def test_memory_has_append_pai_messages():
    t = ChatbotTemplate()
    files = dict(t.starter_files)
    mem = files["src/memory/history.py"]
    assert "append_pai_messages" in mem


def test_memory_clear_resets_both_stores():
    t = ChatbotTemplate()
    files = dict(t.starter_files)
    mem = files["src/memory/history.py"]
    assert "_history.clear()" in mem
    assert "_pai_history.clear()" in mem


def test_memory_type_checking_guard():
    """pydantic_ai import is guarded by TYPE_CHECKING to avoid
    import errors in openai-sdk/litellm projects."""
    t = ChatbotTemplate()
    files = dict(t.starter_files)
    mem = files["src/memory/history.py"]
    assert "TYPE_CHECKING" in mem
    assert "from pydantic_ai.messages import ModelMessage" in mem


def test_openai_sdk_memory_has_no_pai_history():
    """openai-sdk projects get the base history without pydantic-ai dead code."""
    t = ChatbotTemplate(framework="openai-sdk")
    files = dict(t.starter_files)
    mem = files["src/memory/history.py"]
    assert "get_pai_history" not in mem
    assert "_pai_history" not in mem
    assert "append_pai_messages" not in mem


def test_litellm_memory_has_no_pai_history():
    """litellm projects get the base history without pydantic-ai dead code."""
    t = ChatbotTemplate(framework="litellm")
    files = dict(t.starter_files)
    mem = files["src/memory/history.py"]
    assert "get_pai_history" not in mem
    assert "_pai_history" not in mem
    assert "append_pai_messages" not in mem


# ─── PydanticAI multi-turn memory ────────────────────────────────────────


@pytest.mark.parametrize(
    "provider", ["openai", "anthropic", "gemini", "openrouter", "ollama"]
)
def test_pydantic_ai_sends_message_history(provider):
    """All pydantic-ai variants must pass message_history to run_sync()."""
    t = ChatbotTemplate(framework="pydantic-ai", provider=provider)
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert "message_history=get_pai_history()" in llm, (
        f"pydantic-ai+{provider} missing message_history param"
    )


@pytest.mark.parametrize(
    "provider", ["openai", "anthropic", "gemini", "openrouter", "ollama"]
)
def test_pydantic_ai_appends_new_messages(provider):
    """All pydantic-ai variants must store new messages after each call."""
    t = ChatbotTemplate(framework="pydantic-ai", provider=provider)
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert "append_pai_messages(result.new_messages())" in llm, (
        f"pydantic-ai+{provider} missing append_pai_messages call"
    )


@pytest.mark.parametrize(
    "provider", ["openai", "anthropic", "gemini", "openrouter", "ollama"]
)
def test_pydantic_ai_imports_memory_functions(provider):
    """All pydantic-ai variants must import the pai history functions."""
    t = ChatbotTemplate(framework="pydantic-ai", provider=provider)
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert "from src.memory.history import get_pai_history, append_pai_messages" in llm


# ─── Dependency simplification ───────────────────────────────────────────


@pytest.mark.parametrize(
    "provider", ["openai", "anthropic", "gemini", "openrouter", "ollama"]
)
def test_pydantic_ai_uses_metapackage_only(provider):
    """pydantic-ai metapackage bundles all providers — no separate installs."""
    t = ChatbotTemplate(framework="pydantic-ai", provider=provider)
    deps = t.get_dependencies()
    assert "pydantic-ai" in deps
    assert "openai" not in deps, (
        f"pydantic-ai+{provider} should not list openai separately"
    )
    assert "anthropic" not in deps, (
        f"pydantic-ai+{provider} should not list anthropic separately"
    )
    assert "google-genai" not in deps, (
        f"pydantic-ai+{provider} should not list google-genai separately"
    )


# ─── All 13 combinations generate complete file sets ─────────────────────

ALL_COMBINATIONS = [
    ("pydantic-ai", "openai"),
    ("pydantic-ai", "anthropic"),
    ("pydantic-ai", "gemini"),
    ("pydantic-ai", "openrouter"),
    ("pydantic-ai", "ollama"),
    ("pydantic-ai", "groq"),
    ("openai-sdk", "openai"),
    ("openai-sdk", "openrouter"),
    ("openai-sdk", "gemini"),
    ("openai-sdk", "groq"),
    ("litellm", "openai"),
    ("litellm", "anthropic"),
    ("litellm", "gemini"),
    ("litellm", "openrouter"),
    ("litellm", "ollama"),
    ("litellm", "groq"),
]

REQUIRED_FILES = [
    "src/__init__.py",
    "src/chatbot/__init__.py",
    "src/chatbot/chat.py",
    "src/providers/__init__.py",
    "src/providers/llm.py",
    "src/prompts/__init__.py",
    "src/prompts/system.txt",
    "src/memory/__init__.py",
    "src/memory/history.py",
    "src/config/__init__.py",
    "src/config/settings.py",
    "src/main.py",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/test_chatbot.py",
    ".env.example",
]


@pytest.mark.parametrize("framework,provider", ALL_COMBINATIONS)
def test_all_combinations_generate_required_files(framework, provider):
    t = ChatbotTemplate(framework=framework, provider=provider)
    generated = [p for p, _ in t.starter_files]
    for required in REQUIRED_FILES:
        assert required in generated, f"{framework}+{provider} missing {required}"


@pytest.mark.parametrize("framework,provider", ALL_COMBINATIONS)
def test_all_combinations_llm_compiles(framework, provider):
    """Every llm.py variant must be syntactically valid Python."""
    t = ChatbotTemplate(framework=framework, provider=provider)
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    _assert_valid_python(llm, f"{framework}+{provider} llm.py")


@pytest.mark.parametrize("framework,provider", ALL_COMBINATIONS)
def test_all_combinations_memory_compiles(framework, provider):
    """memory/history.py must compile for all combinations."""
    t = ChatbotTemplate(framework=framework, provider=provider)
    files = dict(t.starter_files)
    mem = files["src/memory/history.py"]
    _assert_valid_python(mem, f"{framework}+{provider} memory/history.py")


@pytest.mark.parametrize("framework,provider", ALL_COMBINATIONS)
def test_all_combinations_have_python_dotenv(framework, provider):
    t = ChatbotTemplate(framework=framework, provider=provider)
    assert "python-dotenv" in t.get_dependencies(), (
        f"{framework}+{provider} missing python-dotenv"
    )


@pytest.mark.parametrize("framework,provider", ALL_COMBINATIONS)
def test_no_utils_dir_generated(framework, provider):
    t = ChatbotTemplate(framework=framework, provider=provider)
    paths = [p for p, _ in t.starter_files]
    assert "src/utils/env.py" not in paths
    assert "src/utils/__init__.py" not in paths
    assert "src/utils" not in t.folders


# ─── Groq-specific ───────────────────────────────────────────────────────


def test_pydantic_ai_groq_uses_groq_prefix():
    t = ChatbotTemplate(framework="pydantic-ai", provider="groq")
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert "groq:llama-3.1-8b-instant" in llm


def test_pydantic_ai_groq_has_multi_turn_memory():
    t = ChatbotTemplate(framework="pydantic-ai", provider="groq")
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert "message_history=get_pai_history()" in llm
    assert "append_pai_messages(result.new_messages())" in llm


def test_openai_sdk_groq_uses_groq_base_url():
    t = ChatbotTemplate(framework="openai-sdk", provider="groq")
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert "api.groq.com" in llm
    assert "GROQ_API_KEY" in llm


def test_litellm_groq_uses_groq_prefix():
    t = ChatbotTemplate(framework="litellm", provider="groq")
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert "groq/llama-3.1-8b-instant" in llm


@pytest.mark.parametrize("framework", ["pydantic-ai", "openai-sdk", "litellm"])
def test_groq_env_has_groq_api_key(framework):
    t = ChatbotTemplate(framework=framework, provider="groq")
    files = dict(t.starter_files)
    env = files[".env.example"].format_map({"project_name": "test"})
    assert "GROQ_API_KEY" in env


@pytest.mark.parametrize("framework", ["pydantic-ai", "openai-sdk", "litellm"])
def test_groq_deps_correct(framework):
    t = ChatbotTemplate(framework=framework, provider="groq")
    deps = t.get_dependencies()
    assert "python-dotenv" in deps
    # groq is bundled in pydantic-ai metapackage, no separate dep needed
    assert "groq" not in deps


# ─── AGENTS.md special-case: litellm + ollama ────────────────────────────


def test_litellm_ollama_agents_md_has_ollama_api_base():
    """litellm+ollama must reference OLLAMA_API_BASE, not OLLAMA_BASE_URL."""
    from spawn.templates.chatbot import ChatbotTemplate

    t = ChatbotTemplate(framework="litellm", provider="ollama")
    result = t.get_agents_md_content({"project_name": "my-bot"})
    assert result is not None
    assert "OLLAMA_API_BASE" in result
    assert "OLLAMA_BASE_URL" not in result
