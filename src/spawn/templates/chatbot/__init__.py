from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.chatbot.content import (
    INIT_CONTENT,
    CHAT_CONTENT,
    MEMORY_HISTORY_CONTENT,
    SYSTEM_PROMPT_TXT_CONTENT,
    SETTINGS_CONTENT,
    ENV_UTIL_CONTENT,
    MAIN_CONTENT_NO_RICH,
    MAIN_CONTENT_RICH,
    TEST_CONTENT,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
    PYDANTIC_AI_OPENAI_LLM_CONTENT,
    PYDANTIC_AI_ANTHROPIC_LLM_CONTENT,
    PYDANTIC_AI_GEMINI_LLM_CONTENT,
    PYDANTIC_AI_OPENROUTER_LLM_CONTENT,
    PYDANTIC_AI_OLLAMA_LLM_CONTENT,
    OPENAI_SDK_OPENAI_LLM_CONTENT,
    OPENAI_SDK_OPENROUTER_LLM_CONTENT,
    OPENAI_SDK_GEMINI_LLM_CONTENT,
    LITELLM_OPENAI_LLM_CONTENT,
    LITELLM_ANTHROPIC_LLM_CONTENT,
    LITELLM_GEMINI_LLM_CONTENT,
    LITELLM_OPENROUTER_LLM_CONTENT,
    LITELLM_OLLAMA_LLM_CONTENT,
    ENV_OPENAI,
    ENV_ANTHROPIC,
    ENV_GEMINI,
    ENV_OPENROUTER,
    ENV_OLLAMA,
    ENV_PYDANTIC_OPENAI,
    ENV_PYDANTIC_ANTHROPIC,
    ENV_PYDANTIC_GEMINI,
    ENV_PYDANTIC_OPENROUTER,
    ENV_PYDANTIC_OLLAMA,
    make_readme,
)

CHATBOT_FOLDERS = [
    "src/chatbot",
    "src/providers",
    "src/prompts",
    "src/memory",
    "src/config",
    "src/utils",
    "tests",
]

# Maps (framework, provider) → llm content
_LLM_MAP: dict[tuple[str, str], str] = {
    ("pydantic-ai",  "openai"):     PYDANTIC_AI_OPENAI_LLM_CONTENT,
    ("pydantic-ai",  "anthropic"):  PYDANTIC_AI_ANTHROPIC_LLM_CONTENT,
    ("pydantic-ai",  "gemini"):     PYDANTIC_AI_GEMINI_LLM_CONTENT,
    ("pydantic-ai",  "openrouter"): PYDANTIC_AI_OPENROUTER_LLM_CONTENT,
    ("pydantic-ai",  "ollama"):     PYDANTIC_AI_OLLAMA_LLM_CONTENT,
    ("openai-sdk",   "openai"):     OPENAI_SDK_OPENAI_LLM_CONTENT,
    ("openai-sdk",   "openrouter"): OPENAI_SDK_OPENROUTER_LLM_CONTENT,
    ("openai-sdk",   "gemini"):     OPENAI_SDK_GEMINI_LLM_CONTENT,
    ("litellm",      "openai"):     LITELLM_OPENAI_LLM_CONTENT,
    ("litellm",      "anthropic"):  LITELLM_ANTHROPIC_LLM_CONTENT,
    ("litellm",      "gemini"):     LITELLM_GEMINI_LLM_CONTENT,
    ("litellm",      "openrouter"): LITELLM_OPENROUTER_LLM_CONTENT,
    ("litellm",      "ollama"):     LITELLM_OLLAMA_LLM_CONTENT,
}

# Maps provider → env example (pydantic-ai uses prefixed MODEL format)
_ENV_MAP_PYDANTIC: dict[str, str] = {
    "openai":     ENV_PYDANTIC_OPENAI,
    "anthropic":  ENV_PYDANTIC_ANTHROPIC,
    "gemini":     ENV_PYDANTIC_GEMINI,
    "openrouter": ENV_PYDANTIC_OPENROUTER,
    "ollama":     ENV_PYDANTIC_OLLAMA,
}

_ENV_MAP_GENERIC: dict[str, str] = {
    "openai":     ENV_OPENAI,
    "anthropic":  ENV_ANTHROPIC,
    "gemini":     ENV_GEMINI,
    "openrouter": ENV_OPENROUTER,
    "ollama":     ENV_OLLAMA,
}


def _resolve_llm(framework: str, provider: str) -> str:
    return _LLM_MAP.get((framework, provider), PYDANTIC_AI_OPENAI_LLM_CONTENT)


def _resolve_env(framework: str, provider: str) -> str:
    if framework == "pydantic-ai":
        return _ENV_MAP_PYDANTIC.get(provider, ENV_PYDANTIC_OPENAI)
    return _ENV_MAP_GENERIC.get(provider, ENV_OPENAI)


def _build_files(main_content: str, llm_content: str, env_content: str) -> list:
    return [
        ("src/__init__.py",           INIT_CONTENT),
        ("src/chatbot/__init__.py",   INIT_CONTENT),
        ("src/chatbot/chat.py",       CHAT_CONTENT),
        ("src/providers/__init__.py", INIT_CONTENT),
        ("src/providers/llm.py",      llm_content),
        ("src/prompts/__init__.py",   INIT_CONTENT),
        ("src/prompts/system.txt",    SYSTEM_PROMPT_TXT_CONTENT),
        ("src/memory/__init__.py",    INIT_CONTENT),
        ("src/memory/history.py",     MEMORY_HISTORY_CONTENT),
        ("src/config/__init__.py",    INIT_CONTENT),
        ("src/config/settings.py",    SETTINGS_CONTENT),
        ("src/utils/__init__.py",     INIT_CONTENT),
        ("src/utils/env.py",          ENV_UTIL_CONTENT),
        ("src/main.py",               main_content),
        ("tests/__init__.py",         INIT_CONTENT),
        ("tests/test_chatbot.py",     TEST_CONTENT),
        (".env.example",              env_content),
    ]


class ChatbotTemplate(BaseTemplate):
    def __init__(
        self,
        framework: str | None = None,
        provider: str | None = None,
        extras: list[str] | None = None,
    ) -> None:
        self.framework = framework or "pydantic-ai"
        self.provider  = provider  or "openai"
        self.extras    = extras    or []

        llm_content  = _resolve_llm(self.framework, self.provider)
        env_content  = _resolve_env(self.framework, self.provider)
        main_content = MAIN_CONTENT_RICH if "rich" in self.extras else MAIN_CONTENT_NO_RICH

        super().__init__(
            name="AI Chatbot",
            folders=list(CHATBOT_FOLDERS),
            starter_files=_build_files(main_content, llm_content, env_content),
            next_steps=[
                "cd {project_name}",
                "cp .env.example .env  # then fill in your API key",
                "uv run python -m src.main",
            ],
        )

    def get_readme_content(self, context: dict) -> str | None:
        raw = make_readme(self.framework, self.provider)
        return raw.format_map(context)

    def get_dependencies(self) -> list[str]:
        dep_map: dict[tuple[str, str], list[str]] = {
            ("pydantic-ai",  "openai"):     ["pydantic-ai", "openai",       "python-dotenv"],
            ("pydantic-ai",  "anthropic"):  ["pydantic-ai", "anthropic",    "python-dotenv"],
            ("pydantic-ai",  "gemini"):     ["pydantic-ai", "google-genai", "python-dotenv"],
            ("pydantic-ai",  "openrouter"): ["pydantic-ai", "openai",       "python-dotenv"],
            ("pydantic-ai",  "ollama"):     ["pydantic-ai", "openai",       "python-dotenv"],
            ("openai-sdk",   "openai"):     ["openai",       "python-dotenv"],
            ("openai-sdk",   "openrouter"): ["openai",       "python-dotenv"],
            ("openai-sdk",   "gemini"):     ["openai",       "python-dotenv"],
            ("litellm",      "openai"):     ["litellm",      "python-dotenv"],
            ("litellm",      "anthropic"):  ["litellm",      "python-dotenv"],
            ("litellm",      "gemini"):     ["litellm",      "python-dotenv"],
            ("litellm",      "openrouter"): ["litellm",      "python-dotenv"],
            ("litellm",      "ollama"):     ["litellm",      "python-dotenv"],
        }

        base = list(dep_map.get((self.framework, self.provider), ["pydantic-ai", "openai", "python-dotenv"]))

        if "pytest" in self.extras:
            base.append("pytest")
        if "ruff" in self.extras:
            base.append("ruff")
        if "rich" in self.extras:
            base.append("rich")

        return base

    def post_install(self, project_path: Path) -> None:
        pyproject = project_path / "pyproject.toml"
        current   = pyproject.read_text(encoding="utf-8")
        additions = ""

        if "pytest" in self.extras:
            additions += "\n[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n"

        if "ruff" in self.extras:
            additions += "\n[tool.ruff]\nline-length = 88\n"

        if additions:
            pyproject.write_text(current + additions, encoding="utf-8")

        if "github-actions" in self.extras:
            workflows_path = project_path / ".github" / "workflows"
            workflows_path.mkdir(parents=True, exist_ok=True)
            ci = GITHUB_ACTIONS_CI_BASE
            if "ruff" in self.extras:
                ci += GITHUB_ACTIONS_CI_RUFF_STEP
            if "pytest" in self.extras:
                ci += GITHUB_ACTIONS_CI_PYTEST_STEP
            (workflows_path / "ci.yml").write_text(ci, encoding="utf-8")
