INIT_CONTENT = ""

# ─── Knowledge base ───────────────────────────────────────────────────────

SAMPLE_KNOWLEDGE_CONTENT = """\
# Spawn Knowledge Base

## What is Spawn?

Spawn is an intent-based project generator that helps developers create
production-friendly project foundations in seconds. Instead of manually
creating folders, installing dependencies, and configuring tools, developers
run one command and get a complete, immediately runnable project.

## Spawn Intents

Spawn supports the following project intents:

- Backend API: FastAPI, Flask, or Django with production structure
- CLI Application: Typer, Click, or Argparse command-line tools
- Automation Tool: Workflow-based automation with logging
- AI Chatbot: Conversational AI with PydanticAI, OpenAI SDK, or LiteLLM
- AI Agent: Tool-calling agents with PydanticAI or OpenAI Agents SDK
- RAG System: Retrieval-Augmented Generation with LlamaIndex and ChromaDB

## How Spawn Works

Run `spawn create`, select your intent, choose your framework and provider,
pick any extras (ruff, pytest, github-actions), and Spawn generates the full
project structure, installs dependencies via uv, and shows you the exact
commands to run next. The entire setup takes under 30 seconds.

## RAG System Intent

The RAG System intent (added in v0.8.0) generates a complete
Retrieval-Augmented Generation application using LlamaIndex and ChromaDB.
It ingests documents from the data/ directory, creates embeddings using
OpenAI's text-embedding-3-small model, stores them in a local ChromaDB
vector database, and answers questions using retrieved context. On first
run the ingestion step is triggered automatically before the Q&A loop starts.

## Version History

- v0.6.0: Initial release with Backend API, CLI Application, Automation Tool,
  and AI Chatbot intents.
- v0.7.0: Added AI Agent intent with PydanticAI and OpenAI Agents SDK support,
  plus Groq provider across all AI intents.
- v0.8.0: Added RAG System intent with LlamaIndex, ChromaDB, and OpenAI.
"""

# ─── Config ───────────────────────────────────────────────────────────────

SETTINGS_CONTENT = """\
import os
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI


def load_env() -> None:
    load_dotenv()


def configure_llm() -> None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    Settings.llm = OpenAI(model=model, api_key=api_key)
    Settings.embed_model = OpenAIEmbedding(
        model="text-embedding-3-small",
        api_key=api_key,
    )
"""

# ─── Knowledge index ──────────────────────────────────────────────────────

KNOWLEDGE_INDEX_CONTENT = """\
import re
from pathlib import Path

import chromadb
from llama_index.core import StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore


def _sanitize_collection_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "-", name)
    cleaned = cleaned.strip("-._")
    if len(cleaned) < 3:
        cleaned = f"rag-{{cleaned}}".strip("-._")
    if len(cleaned) < 3:
        cleaned = "rag-collection"
    return cleaned[:512]


CHROMA_PATH = Path("chroma_db")
COLLECTION_NAME = _sanitize_collection_name("{project_name}")


def get_vector_store() -> ChromaVectorStore:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(COLLECTION_NAME)
    return ChromaVectorStore(chroma_collection=collection)


def get_storage_context() -> StorageContext:
    return StorageContext.from_defaults(vector_store=get_vector_store())


def index_exists() -> bool:
    if not CHROMA_PATH.exists():
        return False
    return any(CHROMA_PATH.iterdir())
"""

# ─── Ingestion ────────────────────────────────────────────────────────────

INGESTION_CONTENT = """\
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

from src.knowledge.index import get_storage_context

DATA_PATH = Path("data")


def ingest_documents() -> VectorStoreIndex:
    print("Ingesting documents from data/...")
    documents = SimpleDirectoryReader(
        input_dir=str(DATA_PATH),
        required_exts=[".txt", ".md"],
        recursive=True,
    ).load_data()
    print(f"Loaded {{len(documents)}} document(s).")
    storage_context = get_storage_context()
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True,
    )
    print("Ingestion complete. Index stored in chroma_db/")
    return index
"""

# ─── Retrieval ────────────────────────────────────────────────────────────

RETRIEVAL_CONTENT = """\
from llama_index.core import VectorStoreIndex
from openai import APIError, AuthenticationError, RateLimitError

from src.knowledge.index import get_storage_context, get_vector_store


def load_index() -> VectorStoreIndex:
    vector_store = get_vector_store()
    storage_context = get_storage_context()
    return VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
    )


def answer_question(question: str) -> str:
    index = load_index()
    query_engine = index.as_query_engine(
        similarity_top_k=3,
    )
    try:
        response = query_engine.query(question)
    except AuthenticationError:
        raise RuntimeError(
            "OpenAI rejected your API key. Check OPENAI_API_KEY in .env."
        ) from None
    except RateLimitError as e:
        if "insufficient_quota" in str(e):
            raise RuntimeError(
                "Your OpenAI account has no available quota/credits. "
                "Check billing at https://platform.openai.com/settings/organization/billing"
            ) from None
        raise RuntimeError(
            "OpenAI rate limit hit. Wait a moment and try again."
        ) from None
    except APIError as e:
        raise RuntimeError(f"OpenAI API error: {{e}}") from None
    return str(response)
"""

# ─── Main ─────────────────────────────────────────────────────────────────

MAIN_CONTENT = """\
from src.config.settings import configure_llm, load_env
from src.ingestion.ingest import ingest_documents
from src.knowledge.index import index_exists
from src.retrieval.retrieve import answer_question


def main() -> None:
    load_env()
    configure_llm()
    print("{project_name} RAG System")
    print("-" * 40)
    if not index_exists():
        print("No index found. Running ingestion...\\n")
        try:
            ingest_documents()
        except RuntimeError as e:
            print(f"\\n[Error] {{e}}\\n")
            return
        print()
    print("Ask a question (or type 'quit' to exit):\\n")
    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in ("quit", "exit"):
            break
        try:
            answer = answer_question(question)
            print(f"\\nAnswer: {{answer}}\\n")
        except RuntimeError as e:
            print(f"\\n[Error] {{e}}\\n")
            continue


if __name__ == "__main__":
    main()
"""

# ─── Tests ────────────────────────────────────────────────────────────────

CONFTEST_CONTENT = """\
# conftest.py — shared test fixtures for RAG tests
"""

TEST_CONTENT = """\
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_index_exists_false_when_no_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from src.knowledge.index import index_exists
    assert not index_exists()


def test_index_exists_false_when_empty_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "chroma_db").mkdir()
    from src.knowledge.index import index_exists
    assert not index_exists()


def test_index_exists_true_when_has_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chroma = tmp_path / "chroma_db"
    chroma.mkdir()
    (chroma / "chroma.sqlite3").write_text("db")
    from src.knowledge.index import index_exists
    assert index_exists()


def test_sample_knowledge_file_exists():
    data_path = Path("data") / "sample_knowledge.md"
    assert data_path.exists(), "data/sample_knowledge.md must exist"


def test_answer_question_mock():
    mock_engine = MagicMock()
    mock_engine.query.return_value = "Spawn is a project generator."
    mock_index = MagicMock()
    mock_index.as_query_engine.return_value = mock_engine

    with patch("src.retrieval.retrieve.load_index", return_value=mock_index):
        from src.retrieval.retrieve import answer_question
        result = answer_question("What is Spawn?")

    assert isinstance(result, str)
    assert len(result) > 0


def test_answer_question_rate_limit_raises_runtime_error():
    from openai import RateLimitError

    mock_engine = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_engine.query.side_effect = RateLimitError(
        "insufficient_quota", response=mock_response, body=None
    )
    mock_index = MagicMock()
    mock_index.as_query_engine.return_value = mock_engine

    with patch("src.retrieval.retrieve.load_index", return_value=mock_index):
        from src.retrieval.retrieve import answer_question
        try:
            answer_question("What is Spawn?")
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "quota" in str(e).lower() or "rate limit" in str(e).lower()


def test_answer_question_api_error_raises_runtime_error():
    from openai import APIError

    mock_engine = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_engine.query.side_effect = APIError(
        "server error", response=mock_response, body=None
    )
    mock_index = MagicMock()
    mock_index.as_query_engine.return_value = mock_engine

    with patch("src.retrieval.retrieve.load_index", return_value=mock_index):
        from src.retrieval.retrieve import answer_question
        try:
            answer_question("What is Spawn?")
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "OpenAI API error" in str(e)
"""

# ─── Env ──────────────────────────────────────────────────────────────────

ENV_CONTENT = """\
APP_NAME={project_name}
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
"""

# ─── README ───────────────────────────────────────────────────────────────


def make_readme() -> str:
    return (
        "# {project_name}\n\n"
        "A RAG system generated with Spawn using LlamaIndex and ChromaDB.\n\n"
        "## Getting Started\n\n"
        "1. Rename `.env.example` to `.env`\n\n"
        "2. Add your `OPENAI_API_KEY` to `.env`:\n\n"
        "```env\n"
        "OPENAI_API_KEY=your-key\n"
        "```\n\n"
        "3. (Optional) Add your own `.txt` or `.md` files to `data/`\n\n"
        "4. Run the RAG system:\n\n"
        "```bash\n"
        "uv run python -m src.main\n"
        "```\n\n"
        "On first run, documents in `data/` are automatically ingested.\n"
        "Then ask questions about your knowledge base.\n\n"
        "## Example\n\n"
        "```\n"
        "You: What is Spawn?\n"
        "Answer: Spawn is an intent-based project generator...\n"
        "```\n\n"
        "## Adding Knowledge\n\n"
        "Drop `.txt` or `.md` files into `data/` and delete `chroma_db/` to re-index:\n\n"
        "```bash\n"
        "rm -rf chroma_db/\n"
        "uv run python -m src.main\n"
        "```\n\n"
        "## Project Structure\n\n"
        "```\n"
        "{project_name}/\n"
        "├── data/                  # Knowledge documents\n"
        "│   └── sample_knowledge.md\n"
        "├── src/\n"
        "│   ├── config/            # Settings and LLM configuration\n"
        "│   ├── knowledge/         # ChromaDB index management\n"
        "│   ├── ingestion/         # Document ingestion pipeline\n"
        "│   ├── retrieval/         # Query engine and retrieval\n"
        "│   └── main.py\n"
        "├── tests/\n"
        "├── chroma_db/             # Created on first run\n"
        "├── .env.example\n"
        "└── README.md\n"
        "```\n\n"
        "## Running Tests\n\n"
        "```bash\n"
        "uv run pytest\n"
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
