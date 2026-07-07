from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.agent.content import (
    INIT_CONTENT,
    AGENT_PROMPT_TXT_CONTENT,
    SETTINGS_CONTENT,
    CALCULATOR_TOOL_CONTENT,
    PYDANTIC_AI_AGENT_CONTENT,
    OPENAI_AGENTS_AGENT_CONTENT,
    MAIN_CONTENT,
    PYDANTIC_AI_TEST_CONTENT,
    OPENAI_AGENTS_TEST_CONTENT,
    CONFTEST_CONTENT,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
    ENV_PYDANTIC_OPENAI,
    ENV_PYDANTIC_ANTHROPIC,
    ENV_PYDANTIC_GEMINI,
    ENV_PYDANTIC_OPENROUTER,
    ENV_PYDANTIC_OLLAMA,
    ENV_PYDANTIC_GROQ,
    ENV_OPENAI_AGENTS_OPENAI,
    ENV_OPENAI_AGENTS_OPENROUTER,
    make_readme,
)

AGENT_FOLDERS = [
    "src/agent",
    "src/tools",
    "src/prompts",
    "src/config",
    "tests",
]

# Maps (framework, provider) → agent run.py content
_AGENT_MAP: dict[tuple[str, str], str] = {
    ("pydantic-ai",   "openai"):     PYDANTIC_AI_AGENT_CONTENT,
    ("pydantic-ai",   "anthropic"):  PYDANTIC_AI_AGENT_CONTENT,
    ("pydantic-ai",   "gemini"):     PYDANTIC_AI_AGENT_CONTENT,
    ("pydantic-ai",   "openrouter"): PYDANTIC_AI_AGENT_CONTENT,
    ("pydantic-ai",   "ollama"):     PYDANTIC_AI_AGENT_CONTENT,
    ("pydantic-ai",   "groq"):       PYDANTIC_AI_AGENT_CONTENT,
    ("openai-agents", "openai"):     OPENAI_AGENTS_AGENT_CONTENT,
    ("openai-agents", "openrouter"): OPENAI_AGENTS_AGENT_CONTENT,
}

# Maps (framework, provider) → env example
_ENV_MAP: dict[tuple[str, str], str] = {
    ("pydantic-ai",   "openai"):     ENV_PYDANTIC_OPENAI,
    ("pydantic-ai",   "anthropic"):  ENV_PYDANTIC_ANTHROPIC,
    ("pydantic-ai",   "gemini"):     ENV_PYDANTIC_GEMINI,
    ("pydantic-ai",   "openrouter"): ENV_PYDANTIC_OPENROUTER,
    ("pydantic-ai",   "ollama"):     ENV_PYDANTIC_OLLAMA,
    ("pydantic-ai",   "groq"):       ENV_PYDANTIC_GROQ,
    ("openai-agents", "openai"):     ENV_OPENAI_AGENTS_OPENAI,
    ("openai-agents", "openrouter"): ENV_OPENAI_AGENTS_OPENROUTER,
}

# Maps framework → test content
_TEST_MAP: dict[str, str] = {
    "pydantic-ai":   PYDANTIC_AI_TEST_CONTENT,
    "openai-agents": OPENAI_AGENTS_TEST_CONTENT,
}

AGENT_PROVIDER_MAP: dict[str, list[str]] = {
    "pydantic-ai":   ["openai", "anthropic", "gemini", "openrouter", "ollama", "groq"],
    "openai-agents": ["openai", "openrouter"],
}


def get_supported_providers(framework: str) -> list[str]:
    return AGENT_PROVIDER_MAP.get(framework, ["openai"])


def _build_files(
    agent_content: str,
    test_content: str,
    env_content: str,
) -> list:
    return [
        ("src/__init__.py",              INIT_CONTENT),
        ("src/agent/__init__.py",        INIT_CONTENT),
        ("src/agent/run.py",             agent_content),
        ("src/tools/__init__.py",        INIT_CONTENT),
        ("src/tools/calculator.py",      CALCULATOR_TOOL_CONTENT),
        ("src/prompts/__init__.py",      INIT_CONTENT),
        ("src/prompts/agent_prompt.txt", AGENT_PROMPT_TXT_CONTENT),
        ("src/config/__init__.py",       INIT_CONTENT),
        ("src/config/settings.py",       SETTINGS_CONTENT),
        ("src/main.py",                  MAIN_CONTENT),
        ("tests/__init__.py",            INIT_CONTENT),
        ("tests/conftest.py",            CONFTEST_CONTENT),
        ("tests/test_agent.py",          test_content),
        (".env.example",                 env_content),
    ]


class AgentTemplate(BaseTemplate):
    def __init__(
        self,
        framework: str | None = None,
        provider: str | None = None,
        extras: list[str] | None = None,
    ) -> None:
        self.framework = framework or "pydantic-ai"
        self.provider  = provider  or "openai"
        self.extras    = extras    or []

        key = (self.framework, self.provider)
        agent_content = _AGENT_MAP.get(key, PYDANTIC_AI_AGENT_CONTENT)
        env_content   = _ENV_MAP.get(key, ENV_PYDANTIC_OPENAI)
        test_content  = _TEST_MAP.get(self.framework, PYDANTIC_AI_TEST_CONTENT)

        super().__init__(
            name="AI Agent",
            folders=list(AGENT_FOLDERS),
            starter_files=_build_files(agent_content, test_content, env_content),
            next_steps=[
                "cd {project_name}",
                "Rename .env.example to .env and fill in your API key",
                "uv run python src/main.py",
            ],
        )

    def get_readme_content(self, context: dict) -> str | None:
        raw = make_readme(self.framework, self.provider)
        return raw.format_map(context)

    def get_dependencies(self) -> list[str]:
        dep_map: dict[tuple[str, str], list[str]] = {
            ("pydantic-ai",   "openai"):     ["pydantic-ai", "python-dotenv"],
            ("pydantic-ai",   "anthropic"):  ["pydantic-ai", "python-dotenv"],
            ("pydantic-ai",   "gemini"):     ["pydantic-ai", "python-dotenv"],
            ("pydantic-ai",   "openrouter"): ["pydantic-ai", "python-dotenv"],
            ("pydantic-ai",   "ollama"):     ["pydantic-ai", "python-dotenv"],
            ("pydantic-ai",   "groq"):       ["pydantic-ai[groq]", "python-dotenv"],
            ("openai-agents", "openai"):     ["openai-agents", "python-dotenv"],
            ("openai-agents", "openrouter"): ["openai-agents", "python-dotenv"],
        }

        base = list(dep_map.get(
            (self.framework, self.provider),
            ["pydantic-ai", "python-dotenv"],
        ))

        if "pytest" in self.extras:
            base.append("pytest")
        if "ruff" in self.extras:
            base.append("ruff")

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
