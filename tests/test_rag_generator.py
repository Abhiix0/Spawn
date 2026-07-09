import json
from contextlib import contextmanager
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.rag import RAGTemplate


def _cfg(
    name: str = "my-rag",
    extras: list[str] | None = None,
) -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="rag",
        use_git=False,
        extras=extras or [],
    )


@contextmanager
def _mock_uv_and_install():
    with patch("spawn.generators.project_generator.install_packages"), \
         patch("spawn.generators.project_generator.initialize_uv"), \
         patch.object(RAGTemplate, "post_install"):
        yield


# ─── Structure ───────────────────────────────────────────────────────────


def test_rag_creates_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag").is_dir()


def test_rag_creates_data_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "data").is_dir()


def test_rag_creates_chroma_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "chroma_db").is_dir()


def test_rag_creates_knowledge_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "src" / "knowledge").is_dir()


def test_rag_creates_ingestion_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "src" / "ingestion").is_dir()


def test_rag_creates_retrieval_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "src" / "retrieval").is_dir()


# ─── Files ───────────────────────────────────────────────────────────────


def test_rag_creates_sample_knowledge(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "data" / "sample_knowledge.md").exists()


def test_rag_creates_index_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "src" / "knowledge" / "index.py").exists()


def test_rag_creates_ingest_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "src" / "ingestion" / "ingest.py").exists()


def test_rag_creates_retrieve_py(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "src" / "retrieval" / "retrieve.py").exists()


def test_rag_creates_main(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "src" / "main.py").exists()


def test_rag_creates_test_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / "tests" / "test_rag.py").exists()


def test_rag_creates_env_example(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "my-rag" / ".env.example").exists()


# ─── Content ─────────────────────────────────────────────────────────────


def test_rag_readme_has_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="my-knowledge-base"))
    readme = (tmp_path / "my-knowledge-base" / "README.md").read_text(encoding="utf-8")
    assert "my-knowledge-base" in readme


def test_rag_env_has_openai_key(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    env = (tmp_path / "my-rag" / ".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" in env


def test_rag_gitignore_has_chroma(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    gitignore = (tmp_path / "my-rag" / ".gitignore").read_text(encoding="utf-8")
    assert "chroma_db/" in gitignore


def test_rag_sample_knowledge_contains_spawn(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    knowledge = (tmp_path / "my-rag" / "data" / "sample_knowledge.md").read_text(
        encoding="utf-8"
    )
    assert "Spawn" in knowledge


# ─── meta.json ───────────────────────────────────────────────────────────


def test_rag_meta_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    meta = json.loads(
        (tmp_path / "my-rag" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "rag"
    assert meta["framework"] is None
    assert meta["provider"] is None
    assert meta["spawn_version"] == "0.8.0"


# ─── Dependencies ────────────────────────────────────────────────────────


def test_rag_install_packages_called_with_correct_deps(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("spawn.generators.project_generator.install_packages") as mock_install, \
         patch("spawn.generators.project_generator.initialize_uv"), \
         patch.object(RAGTemplate, "post_install"):
        ProjectGenerator().generate(_cfg())
    args = mock_install.call_args[0][1]
    assert "llama-index-core" in args
    assert "chromadb" in args
    assert "llama-index-embeddings-openai" in args
    assert "python-dotenv" in args


def test_rag_gitignore_has_chroma_wildcard_rule(tmp_path, monkeypatch):
    """post_install must append chroma_db/* and !chroma_db/.gitkeep to .gitignore."""
    monkeypatch.chdir(tmp_path)
    with patch("spawn.generators.project_generator.install_packages"), \
         patch("spawn.generators.project_generator.initialize_uv") as mock_uv:
        # initialize_uv needs to create a minimal pyproject.toml so post_install
        # can read it without error
        def fake_uv(p):
            (p / "pyproject.toml").write_text(
                '[project]\nname="x"\nversion="0.1.0"\n', encoding="utf-8"
            )
        mock_uv.side_effect = fake_uv
        ProjectGenerator().generate(_cfg())
    gitignore = (tmp_path / "my-rag" / ".gitignore").read_text(encoding="utf-8")
    assert "chroma_db/*" in gitignore
    assert "!chroma_db/.gitkeep" in gitignore
