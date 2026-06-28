import pytest

from spawn.templates.chatbot import ChatbotTemplate

# ─── Construction ─────────────────────────────────────────────────────────


def test_default_framework_and_provider():
    t = ChatbotTemplate()
    assert t.framework == "pydantic-ai"
    assert t.provider  == "openai"
    assert t.extras    == []


def test_explicit_framework_and_provider():
    t = ChatbotTemplate(framework="litellm", provider="anthropic")
    assert t.framework == "litellm"
    assert t.provider  == "anthropic"


def test_openai_sdk_openrouter():
    t = ChatbotTemplate(framework="openai-sdk", provider="openrouter")
    assert t.framework == "openai-sdk"
    assert t.provider  == "openrouter"


# ─── Folders ──────────────────────────────────────────────────────────────


def test_folders_include_all_required():
    t = ChatbotTemplate()
    assert "src/chatbot"   in t.folders
    assert "src/providers" in t.folders
    assert "src/prompts"   in t.folders
    assert "src/memory"    in t.folders
    assert "src/config"    in t.folders
    assert "src/utils"     in t.folders
    assert "tests"         in t.folders


# ─── Starter files ────────────────────────────────────────────────────────


def test_starter_files_include_all_required():
    t = ChatbotTemplate()
    paths = [p for p, _ in t.starter_files]
    assert "src/main.py"            in paths
    assert "src/chatbot/chat.py"    in paths
    assert "src/providers/llm.py"   in paths
    assert "src/prompts/system.txt" in paths
    assert "src/memory/history.py"  in paths
    assert "src/config/settings.py" in paths
    assert "tests/test_chatbot.py"  in paths
    assert ".env.example"           in paths


def test_starter_file_paths_are_strings():
    t = ChatbotTemplate()
    for path, _ in t.starter_files:
        assert isinstance(path, str)


def test_system_prompt_is_txt_not_py():
    t = ChatbotTemplate()
    paths = [p for p, _ in t.starter_files]
    assert "src/prompts/system.txt"       in paths
    assert "src/prompts/system_prompt.py" not in paths


# ─── LLM content per combination ──────────────────────────────────────────


@pytest.mark.parametrize("framework,provider,expected_import", [
    ("pydantic-ai",  "openai",     "from pydantic_ai import Agent"),
    ("pydantic-ai",  "anthropic",  "from pydantic_ai import Agent"),
    ("pydantic-ai",  "gemini",     "from pydantic_ai import Agent"),
    ("pydantic-ai",  "openrouter", "from pydantic_ai import Agent"),
    ("pydantic-ai",  "ollama",     "from pydantic_ai import Agent"),
    ("openai-sdk",   "openai",     "from openai import OpenAI"),
    ("openai-sdk",   "openrouter", "from openai import OpenAI"),
    ("openai-sdk",   "gemini",     "from openai import OpenAI"),
    ("litellm",      "openai",     "import litellm"),
    ("litellm",      "anthropic",  "import litellm"),
    ("litellm",      "gemini",     "import litellm"),
    ("litellm",      "openrouter", "import litellm"),
    ("litellm",      "ollama",     "import litellm"),
])
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
    assert "result.data"   not in llm


def test_pydantic_ai_no_setdefault_openai_key():
    t = ChatbotTemplate(framework="pydantic-ai", provider="openai")
    files = dict(t.starter_files)
    llm = files["src/providers/llm.py"]
    assert "setdefault" not in llm


# ─── Env example per provider ─────────────────────────────────────────────


@pytest.mark.parametrize("framework,provider,expected_key", [
    ("pydantic-ai",  "openai",     "OPENAI_API_KEY"),
    ("pydantic-ai",  "anthropic",  "ANTHROPIC_API_KEY"),
    ("pydantic-ai",  "gemini",     "GOOGLE_API_KEY"),
    ("pydantic-ai",  "openrouter", "OPENROUTER_API_KEY"),
    ("pydantic-ai",  "ollama",     "OLLAMA_BASE_URL"),
    ("openai-sdk",   "openai",     "OPENAI_API_KEY"),
    ("openai-sdk",   "openrouter", "OPENROUTER_API_KEY"),
    ("openai-sdk",   "gemini",     "GOOGLE_API_KEY"),
    ("litellm",      "openai",     "OPENAI_API_KEY"),
    ("litellm",      "anthropic",  "ANTHROPIC_API_KEY"),
    ("litellm",      "gemini",     "GOOGLE_API_KEY"),
    ("litellm",      "openrouter", "OPENROUTER_API_KEY"),
    ("litellm",      "ollama",     "OLLAMA_BASE_URL"),
])
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


@pytest.mark.parametrize("framework,provider,expected_dep", [
    ("pydantic-ai",  "openai",     "pydantic-ai"),
    ("pydantic-ai",  "anthropic",  "anthropic"),
    ("pydantic-ai",  "gemini",     "google-genai"),
    ("openai-sdk",   "openai",     "openai"),
    ("litellm",      "openai",     "litellm"),
    ("litellm",      "anthropic",  "litellm"),
])
def test_dependencies_include_correct_package(framework, provider, expected_dep):
    t = ChatbotTemplate(framework=framework, provider=provider)
    assert expected_dep in t.get_dependencies()


def test_all_variants_include_python_dotenv():
    combos = [
        ("pydantic-ai", "openai"), ("pydantic-ai", "anthropic"),
        ("openai-sdk", "openai"),  ("litellm", "openai"),
    ]
    for fw, pv in combos:
        assert "python-dotenv" in ChatbotTemplate(framework=fw, provider=pv).get_dependencies()


def test_extras_add_deps():
    t = ChatbotTemplate(extras=["pytest", "ruff", "rich"])
    deps = t.get_dependencies()
    assert "pytest" in deps
    assert "ruff"   in deps
    assert "rich"   in deps


def test_no_extras_excludes_optional():
    t = ChatbotTemplate()
    deps = t.get_dependencies()
    assert "pytest" not in deps
    assert "ruff"   not in deps
    assert "rich"   not in deps


# ─── Rich extra ───────────────────────────────────────────────────────────


def test_rich_extra_uses_rich_main():
    t = ChatbotTemplate(extras=["rich"])
    files = dict(t.starter_files)
    main = files["src/main.py"]
    assert "from rich" in main
    assert "Console"   in main


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
    assert "append_user"      in mem
    assert "append_assistant" in mem
    assert "get_history"      in mem
    assert "clear"            in mem


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
