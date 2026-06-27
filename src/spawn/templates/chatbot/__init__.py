from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.chatbot.content import (
    INIT_CONTENT,
    PYDANTIC_AI_MAIN_CONTENT,
    OPENAI_MAIN_CONTENT,
    PYDANTIC_AI_LLM_CONTENT,
    OPENAI_LLM_CONTENT,
    CHAT_CONTENT,
    SYSTEM_PROMPT_CONTENT,
    ENV_UTIL_CONTENT,
    PYDANTIC_AI_ENV_EXAMPLE_CONTENT,
    OPENAI_ENV_EXAMPLE_CONTENT,
    PYDANTIC_AI_TEST_CONTENT,
    OPENAI_TEST_CONTENT,
    PYDANTIC_AI_README_CONTENT,
    OPENAI_README_CONTENT,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
)

CHATBOT_FOLDERS = [
    "src/chatbot",
    "src/providers",
    "src/prompts",
    "src/utils",
    "tests",
]


def _build_files(
    main_content: str,
    llm_content: str,
    test_content: str,
    env_example_content: str,
) -> list:
    return [
        ("src/__init__.py", INIT_CONTENT),
        ("src/chatbot/__init__.py", INIT_CONTENT),
        ("src/chatbot/chat.py", CHAT_CONTENT),
        ("src/providers/__init__.py", INIT_CONTENT),
        ("src/providers/llm.py", llm_content),
        ("src/prompts/__init__.py", INIT_CONTENT),
        ("src/prompts/system_prompt.py", SYSTEM_PROMPT_CONTENT),
        ("src/utils/__init__.py", INIT_CONTENT),
        ("src/utils/env.py", ENV_UTIL_CONTENT),
        ("src/main.py", main_content),
        ("tests/__init__.py", INIT_CONTENT),
        ("tests/test_chatbot.py", test_content),
        (".env.example", env_example_content),
    ]


class ChatbotTemplate(BaseTemplate):
    def __init__(
        self,
        framework: str | None = None,
        extras: list[str] | None = None,
    ) -> None:
        self.framework = framework or "pydantic-ai"
        self.extras = extras or []

        if self.framework == "openai-sdk":
            main_content = OPENAI_MAIN_CONTENT
            llm_content = OPENAI_LLM_CONTENT
            test_content = OPENAI_TEST_CONTENT
            env_example_content = OPENAI_ENV_EXAMPLE_CONTENT
        else:
            # Default: pydantic-ai
            main_content = PYDANTIC_AI_MAIN_CONTENT
            llm_content = PYDANTIC_AI_LLM_CONTENT
            test_content = PYDANTIC_AI_TEST_CONTENT
            env_example_content = PYDANTIC_AI_ENV_EXAMPLE_CONTENT

        super().__init__(
            name="AI Chatbot",
            folders=list(CHATBOT_FOLDERS),
            starter_files=_build_files(
                main_content, llm_content, test_content, env_example_content
            ),
            next_steps=[
                "cd {project_name}",
                "Add your API_KEY to .env",
                "uv run python -m src.main",
            ],
        )

    def get_readme_content(self, context: dict) -> str | None:
        if self.framework == "openai-sdk":
            return OPENAI_README_CONTENT.format_map(context)
        return PYDANTIC_AI_README_CONTENT.format_map(context)

    def get_dependencies(self) -> list[str]:
        if self.framework == "openai-sdk":
            base = ["openai", "python-dotenv"]
        else:
            base = ["pydantic-ai", "python-dotenv"]
        if "pytest" in self.extras:
            base += ["pytest"]
        if "ruff" in self.extras:
            base += ["ruff"]
        return base

    def post_install(self, project_path: Path) -> None:
        pyproject = project_path / "pyproject.toml"
        current = pyproject.read_text(encoding="utf-8")
        additions = ""

        if "pytest" in self.extras:
            additions += (
                "\n[tool.pytest.ini_options]\n"
                'testpaths = ["tests"]\n'
            )

        if "ruff" in self.extras:
            additions += "\n[tool.ruff]\nline-length = 88\n"

        if additions:
            pyproject.write_text(current + additions, encoding="utf-8")

        if "github-actions" in self.extras:
            workflows_path = project_path / ".github" / "workflows"
            workflows_path.mkdir(parents=True, exist_ok=True)
            ci_content = GITHUB_ACTIONS_CI_BASE
            if "ruff" in self.extras:
                ci_content += GITHUB_ACTIONS_CI_RUFF_STEP
            if "pytest" in self.extras:
                ci_content += GITHUB_ACTIONS_CI_PYTEST_STEP
            (workflows_path / "ci.yml").write_text(
                ci_content, encoding="utf-8"
            )
