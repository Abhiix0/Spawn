import os
import py_compile
import re
import tempfile

import pytest

from spawn.templates.rag import RAGTemplate

# ─── Basic instantiation ──────────────────────────────────────────────────


def test_rag_template_name():
    t = RAGTemplate()
    assert t.name == "RAG System"


def test_rag_template_no_framework():
    t = RAGTemplate()
    assert not hasattr(t, "framework") or getattr(t, "framework", None) is None


def test_rag_template_default_extras():
    t = RAGTemplate()
    assert t.extras == []


# ─── Folders ─────────────────────────────────────────────────────────────


def test_rag_folders_complete():
    t = RAGTemplate()
    for required in [
        "data", "chroma_db", "src/ingestion",
        "src/retrieval", "src/knowledge", "src/config", "tests",
    ]:
        assert required in t.folders, f"Missing folder: {required}"


# ─── Files ───────────────────────────────────────────────────────────────

REQUIRED_FILES = [
    "data/sample_knowledge.md",
    "src/__init__.py",
    "src/config/settings.py",
    "src/knowledge/index.py",
    "src/ingestion/ingest.py",
    "src/retrieval/retrieve.py",
    "src/main.py",
    "tests/conftest.py",
    "tests/test_rag.py",
    ".env.example",
]


def test_rag_required_files():
    t = RAGTemplate()
    paths = [p for p, _ in t.starter_files]
    for f in REQUIRED_FILES:
        assert f in paths, f"Missing file: {f}"


def test_rag_has_no_utils_dir():
    t = RAGTemplate()
    assert "src/utils" not in t.folders


# ─── Content checks ──────────────────────────────────────────────────────


def test_settings_configures_openai_embedding():
    t = RAGTemplate()
    files = dict(t.starter_files)
    settings = files["src/config/settings.py"]
    assert "OpenAIEmbedding" in settings
    assert "text-embedding-3-small" in settings


def test_settings_configures_llm():
    t = RAGTemplate()
    files = dict(t.starter_files)
    settings = files["src/config/settings.py"]
    assert "Settings.llm" in settings
    assert "Settings.embed_model" in settings


def test_knowledge_index_uses_persistent_client():
    t = RAGTemplate()
    files = dict(t.starter_files)
    index = files["src/knowledge/index.py"]
    assert "PersistentClient" in index
    assert "chroma_db" in index


def test_knowledge_index_has_exists_check():
    t = RAGTemplate()
    files = dict(t.starter_files)
    index = files["src/knowledge/index.py"]
    assert "index_exists" in index


def test_ingestion_loads_txt_and_md():
    t = RAGTemplate()
    files = dict(t.starter_files)
    ingest = files["src/ingestion/ingest.py"]
    assert ".txt" in ingest
    assert ".md" in ingest


def test_ingestion_uses_vector_store_index():
    t = RAGTemplate()
    files = dict(t.starter_files)
    ingest = files["src/ingestion/ingest.py"]
    assert "VectorStoreIndex" in ingest


def test_retrieval_uses_query_engine():
    t = RAGTemplate()
    files = dict(t.starter_files)
    retrieve = files["src/retrieval/retrieve.py"]
    assert "as_query_engine" in retrieve
    assert "similarity_top_k" in retrieve


def test_main_auto_ingests_on_first_run():
    t = RAGTemplate()
    files = dict(t.starter_files)
    main = files["src/main.py"]
    assert "index_exists" in main
    assert "ingest_documents" in main


def test_env_has_openai_key():
    t = RAGTemplate()
    files = dict(t.starter_files)
    env = files[".env.example"].format_map({"project_name": "test"})
    assert "OPENAI_API_KEY" in env
    assert "OPENAI_MODEL" in env


def test_sample_knowledge_mentions_spawn():
    t = RAGTemplate()
    files = dict(t.starter_files)
    knowledge = files["data/sample_knowledge.md"]
    assert "Spawn" in knowledge
    assert len(knowledge) > 100


# ─── Compile checks ──────────────────────────────────────────────────────

PYTHON_FILES = [
    "src/config/settings.py",
    "src/knowledge/index.py",
    "src/ingestion/ingest.py",
    "src/retrieval/retrieve.py",
    "src/main.py",
    "tests/test_rag.py",
]


@pytest.mark.parametrize("filepath", PYTHON_FILES)
def test_file_is_valid_python(filepath):
    t = RAGTemplate()
    files = dict(t.starter_files)
    content = files[filepath].format_map({"project_name": "test-rag"})
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        fname = f.name
    try:
        py_compile.compile(fname, doraise=True)
    except py_compile.PyCompileError as e:
        raise AssertionError(f"{filepath} is not valid Python: {e}") from e
    finally:
        os.unlink(fname)


@pytest.mark.parametrize("filepath", PYTHON_FILES)
def test_no_unescaped_braces(filepath):
    t = RAGTemplate()
    files = dict(t.starter_files)
    content = files[filepath]
    singles = re.findall(r"(?<!\{)\{(?!\{)([^}]*)\}(?!\})", content)
    bad = [s for s in singles if s != "project_name"]
    assert not bad, f"{filepath} has unescaped braces: {bad}"


# ─── Dependencies ────────────────────────────────────────────────────────


def test_rag_core_dependencies():
    t = RAGTemplate()
    deps = t.get_dependencies()
    for required in [
        "llama-index-core",
        "llama-index-vector-stores-chroma",
        "llama-index-embeddings-openai",
        "llama-index-llms-openai",
        "chromadb",
        "python-dotenv",
    ]:
        assert required in deps, f"Missing dep: {required}"


def test_rag_no_framework_deps_by_default():
    t = RAGTemplate()
    deps = t.get_dependencies()
    assert "llama-index" not in deps   # meta-package, too heavy
    assert "openai" not in deps        # pulled transitively by llama-index-llms-openai


def test_rag_pytest_extra():
    t = RAGTemplate(extras=["pytest"])
    assert "pytest" in t.get_dependencies()


def test_rag_ruff_extra():
    t = RAGTemplate(extras=["ruff"])
    assert "ruff" in t.get_dependencies()


# ─── Readme ──────────────────────────────────────────────────────────────


def test_rag_readme_contains_project_name():
    t = RAGTemplate()
    readme = t.get_readme_content({"project_name": "my-rag"})
    assert readme is not None
    assert "my-rag" in readme


def test_rag_readme_has_openai_key_instruction():
    t = RAGTemplate()
    readme = t.get_readme_content({"project_name": "x"})
    assert "OPENAI_API_KEY" in readme


def test_rag_readme_explains_re_indexing():
    t = RAGTemplate()
    readme = t.get_readme_content({"project_name": "x"})
    assert "chroma_db" in readme


# ─── next_steps ──────────────────────────────────────────────────────────


def test_rag_next_steps_has_rename():
    t = RAGTemplate()
    assert any("Rename" in s for s in t.next_steps)


def test_rag_next_steps_has_run():
    t = RAGTemplate()
    assert any("src.main" in s for s in t.next_steps)


# ─── gitignore ───────────────────────────────────────────────────────────


def test_gitignore_excludes_chroma_db():
    from spawn.templates.shared_content import GITIGNORE_CONTENT
    assert "chroma_db/" in GITIGNORE_CONTENT


def test_gitignore_keeps_gitkeep():
    from spawn.templates.shared_content import GITIGNORE_CONTENT
    assert "!chroma_db/.gitkeep" in GITIGNORE_CONTENT


# ─── Collection name sanitizer ───────────────────────────────────────────


def test_collection_name_is_valid_for_various_project_names():
    import re
    import types

    t = RAGTemplate()
    files = dict(t.starter_files)
    raw_index = files["src/knowledge/index.py"]

    pattern = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,510}[a-zA-Z0-9]$")

    for project_name in ["my-rag", "ab", "x", "my rag project"]:
        rendered = raw_index.format_map({"project_name": project_name})
        ns: dict = {}
        # Stub out heavy imports so exec works without llama-index installed
        for mod in [
            "chromadb", "llama_index", "llama_index.core",
            "llama_index.vector_stores", "llama_index.vector_stores.chroma",
        ]:
            ns[mod] = types.ModuleType(mod)
        import sys
        stubs = {}
        for mod in [
            "chromadb", "llama_index", "llama_index.core",
            "llama_index.vector_stores", "llama_index.vector_stores.chroma",
        ]:
            stubs[mod] = sys.modules.get(mod)
            sys.modules[mod] = types.ModuleType(mod)
        # Provide minimal fakes so the module-level code executes
        import types as _types
        llama_core = _types.ModuleType("llama_index.core")
        llama_core.StorageContext = object  # type: ignore[attr-defined]
        sys.modules["llama_index.core"] = llama_core
        vs_fake = _types.ModuleType("llama_index.vector_stores.chroma")
        vs_fake.ChromaVectorStore = object  # type: ignore[attr-defined]
        sys.modules["llama_index.vector_stores.chroma"] = vs_fake
        try:
            exec(compile(rendered, "<string>", "exec"), ns)  # noqa: S102
        finally:
            for mod, orig in stubs.items():
                if orig is None:
                    sys.modules.pop(mod, None)
                else:
                    sys.modules[mod] = orig
        collection_name = ns.get("COLLECTION_NAME", "")
        assert pattern.match(collection_name), (
            f"project_name={project_name!r} → COLLECTION_NAME={collection_name!r} "
            "does not match ChromaDB constraints"
        )
