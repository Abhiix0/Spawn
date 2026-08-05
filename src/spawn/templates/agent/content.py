INIT_CONTENT = ""

# ─── Shared content ───────────────────────────────────────────────────────

AGENT_PROMPT_TXT_CONTENT = """\
You are a helpful AI assistant with access to tools.
Use tools when they are helpful to answer the user's request.
Be concise and accurate in your responses.
"""

SETTINGS_CONTENT = """\
import os
from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    load_dotenv()


def get_agent_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "agent_prompt.txt"
    return prompt_path.read_text(encoding="utf-8").strip()
"""

CALCULATOR_TOOL_CONTENT = """\
import re


def calculate(expression: str) -> str:
    \"\"\"
    Evaluate a mathematical expression safely.
    Supports: +, -, *, /, //, **, (, ), and decimal numbers.
    Returns the result as a string, or an error message.
    \"\"\"
    # Strip whitespace and validate characters
    cleaned = expression.strip()
    if not re.match(r'^[\\d\\s\\+\\-\\*\\/\\(\\)\\.\\*\\*\\/\\/]+$', cleaned):
        return f"Invalid expression: only numbers and operators (+,-,*,/,**,//) are allowed"
    try:
        result = eval(cleaned, {{"__builtins__": {{}}}}, {{}})
        return str(result)
    except ZeroDivisionError:
        return "Error: division by zero"
    except Exception as e:
        return f"Error: {{e}}"
"""

MAIN_CONTENT = """\
from src.agent.run import run_agent
from src.config.settings import load_env


def main() -> None:
    load_env()
    print("{project_name} Agent ready. Type 'quit' to exit.\\n")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break
        print("\\nThinking...\\n")
        response = run_agent(user_input)
        print(f"Agent: {{response}}\\n")


if __name__ == "__main__":
    main()
"""

CONFTEST_CONTENT = """\
# conftest.py — no shared fixtures needed for agent tests
"""

# ─── PydanticAI agent ─────────────────────────────────────────────────────

PYDANTIC_AI_AGENT_CONTENT = """\
import os

from pydantic_ai import Agent

from src.config.settings import get_agent_prompt
from src.tools.calculator import calculate as _calculate


def create_agent() -> Agent:
    model = os.getenv("MODEL", "openai:gpt-4o-mini")
    system_prompt = get_agent_prompt()
    agent = Agent(model, system_prompt=system_prompt)

    @agent.tool_plain
    def calculate(expression: str) -> str:
        \"\"\"Evaluate a mathematical expression. Supports +, -, *, /, **, //.\"\"\"
        return _calculate(expression)

    return agent


def run_agent(user_input: str) -> str:
    agent = create_agent()
    result = agent.run_sync(user_input)
    return result.output
"""

PYDANTIC_AI_TEST_CONTENT = """\
from unittest.mock import patch, MagicMock

from src.tools.calculator import calculate


def test_calculator_addition():
    assert calculate("2 + 3") == "5"


def test_calculator_multiplication():
    assert calculate("6 * 7") == "42"


def test_calculator_division():
    result = calculate("10 / 4")
    assert "2.5" in result


def test_calculator_invalid_expression():
    result = calculate("import os")
    assert "Invalid" in result or "Error" in result


def test_run_agent_mock():
    mock_result = MagicMock()
    mock_result.output = "The answer is 42"

    with patch("src.agent.run.Agent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.run_sync.return_value = mock_result
        MockAgent.return_value = mock_instance

        from src.agent.run import run_agent

        result = run_agent("What is 6 * 7?")

    assert isinstance(result, str)
"""

# ─── OpenAI Agents agent ──────────────────────────────────────────────────

OPENAI_AGENTS_AGENT_CONTENT = """\
import os

from agents import Agent, Runner, function_tool

from src.config.settings import get_agent_prompt
from src.tools.calculator import calculate as _calculate


@function_tool
def calculate(expression: str) -> str:
    \"\"\"Evaluate a mathematical expression. Supports +, -, *, /, **, //.\"\"\"
    return _calculate(expression)


def create_agent() -> Agent:
    system_prompt = get_agent_prompt()
    model = os.getenv("MODEL", "gpt-4o-mini")
    return Agent(
        name="{project_name}",
        instructions=system_prompt,
        model=model,
        tools=[calculate],
    )


def run_agent(user_input: str) -> str:
    agent = create_agent()
    result = Runner.run_sync(agent, user_input)
    return result.final_output
"""

OPENAI_AGENTS_TEST_CONTENT = """\
from unittest.mock import patch, MagicMock

from src.tools.calculator import calculate


def test_calculator_addition():
    assert calculate("2 + 3") == "5"


def test_calculator_multiplication():
    assert calculate("6 * 7") == "42"


def test_calculator_division():
    result = calculate("10 / 4")
    assert "2.5" in result


def test_calculator_invalid_expression():
    result = calculate("import os")
    assert "Invalid" in result or "Error" in result


def test_run_agent_mock():
    mock_result = MagicMock()
    mock_result.final_output = "The answer is 42"

    with patch("src.agent.run.Runner") as MockRunner:
        MockRunner.run_sync.return_value = mock_result

        from src.agent.run import run_agent

        result = run_agent("What is 6 * 7?")

    assert isinstance(result, str)
"""

# ─── Env examples ─────────────────────────────────────────────────────────

ENV_PYDANTIC_OPENAI = """\
APP_NAME={project_name}
OPENAI_API_KEY=
MODEL=openai:gpt-4o-mini
"""

ENV_PYDANTIC_ANTHROPIC = """\
APP_NAME={project_name}
ANTHROPIC_API_KEY=
MODEL=anthropic:claude-3-5-haiku-latest
"""

ENV_PYDANTIC_GEMINI = """\
APP_NAME={project_name}
GOOGLE_API_KEY=
MODEL=google:gemini-2.0-flash
"""

ENV_PYDANTIC_OPENROUTER = """\
APP_NAME={project_name}
OPENROUTER_API_KEY=
MODEL=openai/gpt-4o-mini
"""

ENV_PYDANTIC_OLLAMA = """\
APP_NAME={project_name}
OLLAMA_BASE_URL=http://localhost:11434
MODEL=llama3.2
"""

ENV_PYDANTIC_GROQ = """\
APP_NAME={project_name}
GROQ_API_KEY=
MODEL=groq:llama-3.1-8b-instant
"""

ENV_OPENAI_AGENTS_OPENAI = """\
APP_NAME={project_name}
OPENAI_API_KEY=
MODEL=gpt-4o-mini
"""

ENV_OPENAI_AGENTS_OPENROUTER = """\
APP_NAME={project_name}
OPENAI_API_KEY=
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL=openai/gpt-4o-mini
OPENAI_AGENTS_DISABLE_TRACING=1
"""

# ─── README ───────────────────────────────────────────────────────────────


def make_readme(framework: str, provider: str) -> str:
    provider_key_map = {
        "openai":      "OPENAI_API_KEY=your-key",
        "anthropic":   "ANTHROPIC_API_KEY=your-key",
        "gemini":      "GOOGLE_API_KEY=your-key",
        "openrouter":  "OPENROUTER_API_KEY=your-key",
        "ollama":      "OLLAMA_BASE_URL=http://localhost:11434",
        "groq":        "GROQ_API_KEY=your-key",
    }
    key_line = provider_key_map.get(provider, "API_KEY=your-key")
    return (
        "# {project_name}\n\n"
        f"An AI agent generated with Spawn, using {framework.title()} + {provider.title()}.\n\n"
        "## Getting Started\n\n"
        "1. Rename `.env.example` to `.env` and fill in your API key:\n\n"
        "```env\n"
        f"{key_line}\n"
        "```\n\n"
        "2. Run the agent:\n\n"
        "```bash\n"
        "uv run python -m src.main\n"
        "```\n\n"
        "## Example\n\n"
        "```\n"
        "You: What is 145 * 28?\n"
        "Thinking...\n"
        "Agent: 4060\n"
        "```\n\n"
        "## Project Structure\n\n"
        "```\n"
        "{project_name}/\n"
        "├── src/\n"
        "│   ├── agent/        # Agent definition and runner\n"
        "│   ├── tools/        # Tool implementations\n"
        "│   ├── prompts/      # agent_prompt.txt\n"
        "│   ├── config/       # Settings and env loading\n"
        "│   └── main.py\n"
        "├── tests/\n"
        "├── .env.example\n"
        "└── README.md\n"
        "```\n\n"
        "## Running Tests\n\n"
        "```bash\n"
        "uv run pytest\n"
        "```\n"
    )


def make_agents_md(framework: str, provider: str) -> str:
    provider_key_map = {
        "openai":      "OPENAI_API_KEY",
        "anthropic":   "ANTHROPIC_API_KEY",
        "gemini":      "GOOGLE_API_KEY",
        "openrouter":  "OPENROUTER_API_KEY",
        "ollama":      "OLLAMA_BASE_URL",
        "groq":        "GROQ_API_KEY",
    }
    key_name = provider_key_map.get(provider, "OPENAI_API_KEY")
    return (
        "# {project_name}\n\n"
        f"AI agent using {framework.title()} with {provider.title()} provider.\n\n"
        "## Required Environment Variable\n\n"
        f"Set `{key_name}` in your `.env` file.\n"
    )

# ─── GitHub Actions ───────────────────────────────────────────────────────

GITHUB_ACTIONS_CI_BASE = """\
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ci:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5

      - name: Install dependencies
        run: uv sync
"""

GITHUB_ACTIONS_CI_RUFF_STEP = """\
      - name: Lint
        run: uv run ruff check .
"""

GITHUB_ACTIONS_CI_PYTEST_STEP = """\
      - name: Test
        run: uv run pytest
"""
