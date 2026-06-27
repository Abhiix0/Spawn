INIT_CONTENT = ""

PYDANTIC_AI_MAIN_CONTENT = """\
from src.chatbot.chat import get_response
from src.utils.env import load_env


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

OPENAI_MAIN_CONTENT = PYDANTIC_AI_MAIN_CONTENT

PYDANTIC_AI_LLM_CONTENT = """\
import os

from pydantic_ai import Agent


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    api_key = os.getenv("API_KEY", "")
    model = os.getenv("MODEL", "openai:gpt-4o-mini")
    history = [m["content"] for m in messages if m["role"] == "user"]
    prompt = history[-1] if history else ""
    agent = Agent(model, system_prompt=system_prompt)
    result = agent.run_sync(prompt, api_key=api_key)
    return result.output
"""

OPENAI_LLM_CONTENT = """\
import os

from openai import OpenAI


def get_llm_response(messages: list[dict], system_prompt: str) -> str:
    client = OpenAI(
        api_key=os.getenv("API_KEY", ""),
        base_url=os.getenv("BASE_URL", "https://api.openai.com/v1"),
    )
    model = os.getenv("MODEL", "gpt-4o-mini")
    full_messages = [{{"role": "system", "content": system_prompt}}] + messages
    response = client.chat.completions.create(
        model=model,
        messages=full_messages,
    )
    return response.choices[0].message.content or ""
"""

CHAT_CONTENT = """\
from src.providers.llm import get_llm_response
from src.prompts.system_prompt import SYSTEM_PROMPT

_history: list[dict] = []


def get_response(user_input: str) -> str:
    _history.append({{"role": "user", "content": user_input}})
    response = get_llm_response(_history, SYSTEM_PROMPT)
    _history.append({{"role": "assistant", "content": response}})
    return response
"""

SYSTEM_PROMPT_CONTENT = """\
SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "Answer questions clearly and concisely."
)
"""

ENV_UTIL_CONTENT = """\
from dotenv import load_dotenv


def load_env() -> None:
    load_dotenv()
"""

PYDANTIC_AI_ENV_EXAMPLE_CONTENT = """\
APP_NAME={project_name}

# Your API key — passed directly to the provider via pydantic-ai
API_KEY=

# Model string with provider prefix (pydantic-ai format)
# Examples:
#   openai:gpt-4o-mini
#   groq:llama-3.3-70b-versatile
#   anthropic:claude-3-5-haiku-latest
MODEL=openai:gpt-4o-mini
"""

OPENAI_ENV_EXAMPLE_CONTENT = """\
APP_NAME={project_name}

# Your API key for the provider
API_KEY=

# Plain model name (no provider prefix for OpenAI SDK)
MODEL=gpt-4o-mini

# Base URL — change to use Groq, OpenRouter, Ollama, etc.
# Examples:
#   https://api.groq.com/openai/v1
#   https://openrouter.ai/api/v1
#   http://localhost:11434/v1
BASE_URL=https://api.openai.com/v1
"""

PYDANTIC_AI_TEST_CONTENT = """\
from unittest.mock import MagicMock, patch

from src.chatbot.chat import get_response
from src.providers.llm import get_llm_response


def test_get_response_returns_string():
    with patch("src.chatbot.chat.get_llm_response", return_value="Hello!"):
        result = get_response("Hi")
    assert isinstance(result, str)
    assert result == "Hello!"


def test_get_response_non_empty():
    with patch("src.chatbot.chat.get_llm_response", return_value="Sure!"):
        result = get_response("Tell me something")
    assert result != ""


def test_get_llm_response_uses_output_attribute():
    mock_result = MagicMock()
    mock_result.output = "test response"
    with patch("src.providers.llm.Agent") as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent.run_sync.return_value = mock_result
        mock_agent_class.return_value = mock_agent
        messages = [{{"role": "user", "content": "hello"}}]
        response = get_llm_response(messages, "You are helpful.")
    assert response == "test response"
    mock_agent.run_sync.assert_called_once()


def test_get_llm_response_passes_api_key():
    mock_result = MagicMock()
    mock_result.output = "ok"
    with patch("src.providers.llm.Agent") as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent.run_sync.return_value = mock_result
        mock_agent_class.return_value = mock_agent
        with patch("src.providers.llm.os.getenv", side_effect=lambda k, d="": {{
            "API_KEY": "test-key", "MODEL": "openai:gpt-4o-mini"
        }}.get(k, d)):
            get_llm_response([{{"role": "user", "content": "hi"}}], "prompt")
        call_kwargs = mock_agent.run_sync.call_args
        assert call_kwargs.kwargs.get("api_key") == "test-key"
"""

OPENAI_TEST_CONTENT = PYDANTIC_AI_TEST_CONTENT

PYDANTIC_AI_README_CONTENT = """\
# {project_name}

An AI chatbot generated with Spawn, using PydanticAI.

## Getting Started

1. Add your API key to `.env`:

```env
API_KEY=your-api-key-here
# Provider-prefixed model string:
MODEL=openai:gpt-4o-mini
# or: groq:llama-3.3-70b-versatile
# or: anthropic:claude-3-5-haiku-latest
```

2. Run the chatbot:

```bash
uv run python -m src.main
```

## Project Structure

```
{project_name}/
├── src/
│   ├── chatbot/        # Conversation logic
│   ├── providers/      # LLM provider (llm.py)
│   ├── prompts/        # System prompt definitions
│   ├── utils/          # Shared helpers
│   └── main.py         # Entry point
├── tests/
├── .env.example
└── README.md
```

## Running Tests

```bash
uv run pytest
```

## Switching Providers

Change the MODEL in `.env` to switch providers:

```env
# OpenAI
MODEL=openai:gpt-4o-mini
API_KEY=your-openai-key

# Groq (fast, free tier available)
MODEL=groq:llama-3.3-70b-versatile
API_KEY=your-groq-key

# Anthropic
MODEL=anthropic:claude-3-5-haiku-latest
API_KEY=your-anthropic-key
```

No code changes needed — `src/providers/llm.py` handles all providers.

## Future Expansions

```bash
spawn add memory
spawn add tools
spawn add rag
spawn add discord
```
"""

OPENAI_README_CONTENT = """\
# {project_name}

An AI chatbot generated with Spawn, using the OpenAI SDK.

## Getting Started

1. Add your API key to `.env`:

```env
API_KEY=your-api-key-here
MODEL=gpt-4o-mini
BASE_URL=https://api.openai.com/v1
```

2. Run the chatbot:

```bash
uv run python -m src.main
```

## Project Structure

```
{project_name}/
├── src/
│   ├── chatbot/        # Conversation logic
│   ├── providers/      # LLM provider (llm.py)
│   ├── prompts/        # System prompt definitions
│   ├── utils/          # Shared helpers
│   └── main.py         # Entry point
├── tests/
├── .env.example
└── README.md
```

## Running Tests

```bash
uv run pytest
```

## Switching Providers

Edit `BASE_URL` and `MODEL` in `.env` to switch providers.

`API_KEY` is passed directly — no code changes needed.

```env
# Groq
BASE_URL=https://api.groq.com/openai/v1
MODEL=llama-3.3-70b-versatile
API_KEY=your-groq-key

# OpenRouter
BASE_URL=https://openrouter.ai/api/v1
MODEL=openai/gpt-4o-mini
API_KEY=your-openrouter-key

# Ollama (local)
BASE_URL=http://localhost:11434/v1
MODEL=llama3.2
API_KEY=ollama
```

## Future Expansions

```bash
spawn add memory
spawn add tools
spawn add rag
spawn add discord
```
"""

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
