from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.templates.rag.content import (
    INIT_CONTENT,
    SAMPLE_KNOWLEDGE_CONTENT,
    SETTINGS_CONTENT,
    KNOWLEDGE_INDEX_CONTENT,
    INGESTION_CONTENT,
    RETRIEVAL_CONTENT,
    MAIN_CONTENT,
    TEST_CONTENT,
    CONFTEST_CONTENT,
    ENV_CONTENT,
    GITHUB_ACTIONS_CI_BASE,
    GITHUB_ACTIONS_CI_RUFF_STEP,
    GITHUB_ACTIONS_CI_PYTEST_STEP,
    make_readme,
)

RAG_FOLDERS = [
    "data",
    "chroma_db",
    "src/ingestion",
    "src/retrieval",
    "src/knowledge",
    "src/config",
    "tests",
]


def _build_files() -> list:
    return [
        ("data/sample_knowledge.md",      SAMPLE_KNOWLEDGE_CONTENT),
        ("src/__init__.py",               INIT_CONTENT),
        ("src/config/__init__.py",        INIT_CONTENT),
        ("src/config/settings.py",        SETTINGS_CONTENT),
        ("src/knowledge/__init__.py",     INIT_CONTENT),
        ("src/knowledge/index.py",        KNOWLEDGE_INDEX_CONTENT),
        ("src/ingestion/__init__.py",     INIT_CONTENT),
        ("src/ingestion/ingest.py",       INGESTION_CONTENT),
        ("src/retrieval/__init__.py",     INIT_CONTENT),
        ("src/retrieval/retrieve.py",     RETRIEVAL_CONTENT),
        ("src/main.py",                   MAIN_CONTENT),
        ("tests/__init__.py",             INIT_CONTENT),
        ("tests/conftest.py",             CONFTEST_CONTENT),
        ("tests/test_rag.py",             TEST_CONTENT),
        (".env.example",                  ENV_CONTENT),
    ]


class RAGTemplate(BaseTemplate):
    def __init__(self, extras: list[str] | None = None) -> None:
        self.extras = extras or []

        super().__init__(
            name="RAG System",
            folders=list(RAG_FOLDERS),
            starter_files=_build_files(),
            next_steps=[
                "cd {project_name}",
                "Rename .env.example to .env and add your OPENAI_API_KEY",
                "uv run python -m src.main",
            ],
        )

    def get_readme_content(self, context: dict) -> str | None:
        return make_readme().format_map(context)

    def get_dependencies(self) -> list[str]:
        base = [
            "llama-index-core",
            "llama-index-vector-stores-chroma",
            "llama-index-embeddings-openai",
            "llama-index-llms-openai",
            "chromadb",
            "python-dotenv",
        ]
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

        # Write .gitkeep into chroma_db/ so git tracks the directory
        # but the actual DB files are gitignored
        gitkeep = project_path / "chroma_db" / ".gitkeep"
        gitkeep.write_text("", encoding="utf-8")
