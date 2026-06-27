INIT_CONTENT = ""

PYDANTIC_AI_MAIN_CONTENT = """\
from src.chatbot.chat import get_response
from src.utils.env import load_env


def main() -> None:
    load_env()
    print("Chatbot ready. Type 'quit' to exit.\n")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break
        response = get_response(user_input)
        print(f"Bot: {{response}}\n")


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
    agent = Agent(model, system_prompt=system_prompt, api_key=api_key)
    history = [m["content"] for m in messages if m["role"] == "user"]
    prompt = history[-1] if history else ""
    result = agent.run_sync(prompt)
    return result.data
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

ENV_EXAMPLE_CONTENT = """\
APP_NAME={project_name}
API_KEY=
MODEL=gpt-4o-mini
BASE_URL=https://api.openai.com/v1
"""

PYDANTIC_AI_TEST_CONTENT = """\
from unittest.mock import patch

from src.chatbot.chat import get_response


def test_get_response_returns_string():
    with patch("src.chatbot.chat.get_llm_response", return_value="Hello!"):
        result = get_response("Hi")
    assert isinstance(result, str)
    assert result == "Hello!"


def test_get_response_non_empty():
    with patch("src.chatbot.chat.get_llm_response", return_value="Sure!"):
        result = get_response("Tell me something")
    assert result != ""
"""

OPENAI_TEST_CONTENT = PYDANTIC_AI_TEST_CONTENT

PYDANTIC_AI_README_CONTENT = """\
# {project_name}

An AI chatbot generated with Spawn, using PydanticAI.

## Getting Started

1. Add your API key to `.env`:

```env
API_KEY=your-api-key-here
MODEL=openai:gpt-4o-mini
```

2. Run the chatbot:

```bash
uv run python src/main.py
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

Edit `src/providers/llm.py` to change model or provider.

Update `MODEL` and `API_KEY` in `.env`.

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
uv run python src/main.py
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

Edit `src/providers/llm.py` and update `BASE_URL`, `MODEL`, and `API_KEY` in `.env`.

Compatible with any OpenAI-compatible API (Groq, OpenRouter, Ollama).

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
