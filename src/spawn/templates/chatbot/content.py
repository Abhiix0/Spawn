INIT_CONTENT = ""

# ─── Shared content ───────────────────────────────────────────────────────

CHAT_CONTENT = """\
from src.providers.llm import get_llm_response
from src.memory.history import append_user, append_assistant, get_history
from src.config.settings import get_system_prompt


def get_response(user_input: str) -> str:
    append_user(user_input)
    history = get_history()
    system_prompt = get_system_prompt()
    response = get_llm_response(history, system_prompt)
    append_assistant(response)
    return response
"""

MEMORY_HISTORY_CONTENT_BASE = """\
_history: list[dict] = []


def append_user(content: str) -> None:
    _history.append({{"role": "user", "content": content}})


def append_assistant(content: str) -> None:
    _history.append({{"role": "assistant", "content": content}})


def get_history() -> list[dict]:
    return list(_history)


def clear() -> None:
    _history.clear()
"""

MEMORY_HISTORY_CONTENT_PYDANTIC = """\
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage

_history: list[dict] = []
_pai_history: list[ModelMessage] = []


def append_user(content: str) -> None:
    _history.append({{"role": "user", "content": content}})


def append_assistant(content: str) -> None:
    _history.append({{"role": "assistant", "content": content}})


def get_history() -> list[dict]:
    return list(_history)


def get_pai_history() -> list[ModelMessage]:
    return list(_pai_history)


def append_pai_messages(messages: list[ModelMessage]) -> None:
    _pai_history.extend(messages)


def clear() -> None:
    _history.clear()
    _pai_history.clear()
"""

SYSTEM_PROMPT_TXT_CONTENT = """\
You are a helpful AI assistant.
Answer questions clearly and concisely.
"""

SETTINGS_CONTENT = """\
from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    load_dotenv()


def get_system_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "system.txt"
    return prompt_path.read_text(encoding="utf-8").strip()
"""

# ─── PydanticAI ───────────────────────────────────────────────────────────

PYDANTIC_AI_OPENAI_LLM_CONTENT = """\
import os

from pydantic_ai import Agent

from src.memory.history import get_pai_history, append_pai_messages


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model = os.getenv("MODEL", "openai:gpt-4o-mini")
    user_messages = [m["content"] for m in messages if m["role"] == "user"]
    prompt = user_messages[-1] if user_messages else ""
    agent = Agent(model, system_prompt=system_prompt)
    result = agent.run_sync(prompt, message_history=get_pai_history())
    append_pai_messages(result.new_messages())
    return result.output
"""

PYDANTIC_AI_ANTHROPIC_LLM_CONTENT = """\
import os

from pydantic_ai import Agent

from src.memory.history import get_pai_history, append_pai_messages


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model = os.getenv("MODEL", "anthropic:claude-3-5-haiku-latest")
    user_messages = [m["content"] for m in messages if m["role"] == "user"]
    prompt = user_messages[-1] if user_messages else ""
    agent = Agent(model, system_prompt=system_prompt)
    result = agent.run_sync(prompt, message_history=get_pai_history())
    append_pai_messages(result.new_messages())
    return result.output
"""

PYDANTIC_AI_GEMINI_LLM_CONTENT = """\
import os

from pydantic_ai import Agent

from src.memory.history import get_pai_history, append_pai_messages


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model = os.getenv("MODEL", "google:gemini-2.0-flash")
    user_messages = [m["content"] for m in messages if m["role"] == "user"]
    prompt = user_messages[-1] if user_messages else ""
    agent = Agent(model, system_prompt=system_prompt)
    result = agent.run_sync(prompt, message_history=get_pai_history())
    append_pai_messages(result.new_messages())
    return result.output
"""

PYDANTIC_AI_OPENROUTER_LLM_CONTENT = """\
import os

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.memory.history import get_pai_history, append_pai_messages


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model_name = os.getenv("MODEL", "openai/gpt-4o-mini")
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    user_messages = [m["content"] for m in messages if m["role"] == "user"]
    prompt = user_messages[-1] if user_messages else ""
    provider = OpenAIProvider(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    model = OpenAIChatModel(model_name, provider=provider)
    agent = Agent(model, system_prompt=system_prompt)
    result = agent.run_sync(prompt, message_history=get_pai_history())
    append_pai_messages(result.new_messages())
    return result.output
"""

PYDANTIC_AI_OLLAMA_LLM_CONTENT = """\
import os

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.memory.history import get_pai_history, append_pai_messages


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model_name = os.getenv("MODEL", "llama3.2")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    user_messages = [m["content"] for m in messages if m["role"] == "user"]
    prompt = user_messages[-1] if user_messages else ""
    provider = OpenAIProvider(api_key="ollama", base_url=base_url)
    model = OpenAIChatModel(model_name, provider=provider)
    agent = Agent(model, system_prompt=system_prompt)
    result = agent.run_sync(prompt, message_history=get_pai_history())
    append_pai_messages(result.new_messages())
    return result.output
"""

PYDANTIC_AI_GROQ_LLM_CONTENT = """\
import os

from pydantic_ai import Agent

from src.memory.history import get_pai_history, append_pai_messages


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model = os.getenv("MODEL", "groq:llama-3.1-8b-instant")
    user_messages = [m["content"] for m in messages if m["role"] == "user"]
    prompt = user_messages[-1] if user_messages else ""
    agent = Agent(model, system_prompt=system_prompt)
    result = agent.run_sync(prompt, message_history=get_pai_history())
    append_pai_messages(result.new_messages())
    return result.output
"""

# ─── OpenAI SDK ───────────────────────────────────────────────────────────

OPENAI_SDK_OPENAI_LLM_CONTENT = """\
import os

from openai import OpenAI


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
    model = os.getenv("MODEL", "gpt-4o-mini")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = client.chat.completions.create(model=model, messages=full_messages)
    return response.choices[0].message.content or ""
"""

OPENAI_SDK_OPENROUTER_LLM_CONTENT = """\
import os

from openai import OpenAI


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        base_url="https://openrouter.ai/api/v1",
    )
    model = os.getenv("MODEL", "openai/gpt-4o-mini")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = client.chat.completions.create(model=model, messages=full_messages)
    return response.choices[0].message.content or ""
"""

OPENAI_SDK_GEMINI_LLM_CONTENT = """\
import os

from openai import OpenAI


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    client = OpenAI(
        api_key=os.getenv("GOOGLE_API_KEY", ""),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    model = os.getenv("MODEL", "gemini-1.5-flash")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = client.chat.completions.create(model=model, messages=full_messages)
    return response.choices[0].message.content or ""
"""

OPENAI_SDK_GROQ_LLM_CONTENT = """\
import os

from openai import OpenAI


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY", ""),
        base_url="https://api.groq.com/openai/v1",
    )
    model = os.getenv("MODEL", "llama-3.1-8b-instant")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = client.chat.completions.create(model=model, messages=full_messages)
    return response.choices[0].message.content or ""
"""

# ─── LiteLLM ──────────────────────────────────────────────────────────────

LITELLM_OPENAI_LLM_CONTENT = """\
import os

import litellm


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model = os.getenv("MODEL", "gpt-4o-mini")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = litellm.completion(model=model, messages=full_messages)
    return response.choices[0].message.content or ""
"""

LITELLM_ANTHROPIC_LLM_CONTENT = """\
import os

import litellm


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model = os.getenv("MODEL", "claude-3-5-haiku-latest")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = litellm.completion(model=model, messages=full_messages)
    return response.choices[0].message.content or ""
"""

LITELLM_GEMINI_LLM_CONTENT = """\
import os

import litellm


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model = os.getenv("MODEL", "gemini/gemini-1.5-flash")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = litellm.completion(model=model, messages=full_messages)
    return response.choices[0].message.content or ""
"""

LITELLM_OPENROUTER_LLM_CONTENT = """\
import os

import litellm


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model = os.getenv("MODEL", "openrouter/openai/gpt-4o-mini")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = litellm.completion(model=model, messages=full_messages)
    return response.choices[0].message.content or ""
"""

LITELLM_OLLAMA_LLM_CONTENT = """\
import os

import litellm


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model = os.getenv("MODEL", "ollama/llama3.2")
    base_url = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = litellm.completion(model=model, messages=full_messages, api_base=base_url)
    return response.choices[0].message.content or ""
"""

LITELLM_GROQ_LLM_CONTENT = """\
import os

import litellm


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    model = os.getenv("MODEL", "groq/llama-3.1-8b-instant")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = litellm.completion(model=model, messages=full_messages)
    return response.choices[0].message.content or ""
"""

# ─── Main content ─────────────────────────────────────────────────────────

MAIN_CONTENT_NO_RICH = """\
from src.chatbot.chat import get_response
from src.config.settings import load_env


def main() -> None:
    load_env()
    print("Chatbot ready. Type 'quit' to exit.\\n")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break
        response = get_response(user_input)
        print(f"Bot: {{response}}\\n")


if __name__ == "__main__":
    main()
"""

MAIN_CONTENT_RICH = """\
from rich.console import Console
from rich.panel import Panel

from src.chatbot.chat import get_response
from src.config.settings import load_env

console = Console()


def main() -> None:
    load_env()
    console.print(Panel.fit("[bold cyan]Chatbot[/bold cyan] — type [dim]quit[/dim] to exit"))
    while True:
        user_input = console.input("[bold yellow]You:[/bold yellow] ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break
        response = get_response(user_input)
        console.print(f"[bold green]Bot:[/bold green] {{response}}\\n")


if __name__ == "__main__":
    main()
"""

# ─── Env examples (provider-specific) ─────────────────────────────────────

ENV_OPENAI = """\
APP_NAME={project_name}
OPENAI_API_KEY=
MODEL=gpt-4o-mini
"""

ENV_ANTHROPIC = """\
APP_NAME={project_name}
ANTHROPIC_API_KEY=
MODEL=claude-3-5-haiku-latest
"""

ENV_GEMINI = """\
APP_NAME={project_name}
GOOGLE_API_KEY=
MODEL=gemini-1.5-flash
"""

ENV_OPENROUTER = """\
APP_NAME={project_name}
OPENROUTER_API_KEY=
MODEL=openai/gpt-4o-mini
"""

ENV_OLLAMA = """\
APP_NAME={project_name}
OLLAMA_BASE_URL=http://localhost:11434
MODEL=llama3.2
"""

# litellm+ollama uses a different env var for the base URL
ENV_LITELLM_OLLAMA = """\
APP_NAME={project_name}
OLLAMA_API_BASE=http://localhost:11434
MODEL=ollama/llama3.2
"""

ENV_GROQ = """\
APP_NAME={project_name}
GROQ_API_KEY=
MODEL=llama-3.1-8b-instant
"""

# Provider-prefixed MODEL for pydantic-ai variants

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

ENV_LITELLM_GROQ = """\
APP_NAME={project_name}
GROQ_API_KEY=
MODEL=groq/llama-3.1-8b-instant
"""

# ─── Test content ─────────────────────────────────────────────────────────

# BUG FIX: removed unused imports MagicMock and get_llm_response
# which caused ruff F401 failures in generated projects with ruff extra selected
CONFTEST_CONTENT = """\
import pytest

from src.memory.history import clear


@pytest.fixture(autouse=True)
def reset_memory():
    \"\"\"Reset conversation history before every test.\"\"\"
    clear()
    yield
    clear()
"""

TEST_CONTENT = """\
from unittest.mock import patch

from src.chatbot.chat import get_response


def test_get_response_returns_string():
    with patch("src.chatbot.chat.get_llm_response", return_value="Hello!"):
        with patch("src.chatbot.chat.get_system_prompt", return_value="You are helpful."):
            result = get_response("Hi")
    assert isinstance(result, str)
    assert result == "Hello!"


def test_generate_response_mock():
    with patch("src.chatbot.chat.get_llm_response", return_value="Mocked response"):
        with patch("src.chatbot.chat.get_system_prompt", return_value="prompt"):
            result = get_response("test input")
    assert result == "Mocked response"


def test_get_response_non_empty():
    with patch("src.chatbot.chat.get_llm_response", return_value="Sure!"):
        with patch("src.chatbot.chat.get_system_prompt", return_value="prompt"):
            result = get_response("Tell me something")
    assert result != ""
"""

# ─── README content ───────────────────────────────────────────────────────

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
        f"An AI chatbot generated with Spawn, using {framework.title()} + {provider.title()}.\n\n"
        "## Getting Started\n\n"
        "1. Copy `.env.example` to `.env` and fill in your credentials:\n\n"
        "```env\n"
        f"{key_line}\n"
        "```\n\n"
        "2. Run the chatbot:\n\n"
        "```bash\n"
        "uv run python -m src.main\n"
        "```\n\n"
        "## Example\n\n"
        "```\n"
        "You: Hello\n"
        "Bot: Hello! How can I help?\n"
        "```\n\n"
        "## Project Structure\n\n"
        "```\n"
        "{project_name}/\n"
        "├── src/\n"
        "│   ├── chatbot/      # Conversation orchestration\n"
        "│   ├── providers/    # LLM provider (llm.py)\n"
        "│   ├── prompts/      # system.txt\n"
        "│   ├── memory/       # Runtime conversation history\n"
        "│   ├── config/       # Settings and env loading\n"
        "│   └── main.py\n"
        "├── tests/\n"
        "├── .env.example\n"
        "└── README.md\n"
        "```\n\n"
        "## Running Tests\n\n"
        "```bash\n"
        "uv run pytest\n"
        "```\n\n"
        "## Roadmap (Not Yet Available)\n\n"
        "```bash\n"
        "spawn add rag\n"
        "spawn add tools\n"
        "spawn add vector-db\n"
        "spawn add memory\n"
        "spawn add mcp\n"
        "spawn add voice\n"
        "spawn add web-ui\n"
        "spawn add streaming\n"
        "spawn add observability\n"
        "```\n"
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