import pytest

from unittest.mock import patch

from spawn.core.exceptions import SpawnError
from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cli_config(name="demo", **kwargs):
    """Return a minimal ProjectConfig using the cli template."""
    return ProjectConfig(name=name, template="cli", use_git=False, **kwargs)


def _patch_post_install():
    """Context manager that silences CLITemplate.post_install."""
    from spawn.templates.cli_application import CLITemplate
    return patch.object(CLITemplate, "post_install")


def _automation_config(name="demo", **kwargs):
    """Return a minimal ProjectConfig using the automation template."""
    return ProjectConfig(name=name, template="automation", use_git=False, **kwargs)


def _patch_automation_post_install():
    """Context manager that silences AutomationTemplate.post_install."""
    from spawn.templates.automation import AutomationTemplate
    return patch.object(AutomationTemplate, "post_install")


def _chatbot_config(name="demo", **kwargs):
    """Return a minimal ProjectConfig using the chatbot template."""
    return ProjectConfig(name=name, template="chatbot", use_git=False, **kwargs)


def _patch_chatbot_post_install():
    """Context manager that silences ChatbotTemplate.post_install."""
    from spawn.templates.chatbot import ChatbotTemplate
    return patch.object(ChatbotTemplate, "post_install")


# ---------------------------------------------------------------------------
# Basic project structure
# ---------------------------------------------------------------------------


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_project(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_post_install():
        ProjectGenerator().generate(_cli_config())
    assert (tmp_path / "demo").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_folders(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_post_install():
        ProjectGenerator().generate(_cli_config())
    assert (tmp_path / "demo" / "src").exists()
    assert (tmp_path / "demo" / "tests").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_readme(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_post_install():
        ProjectGenerator().generate(_cli_config())
    assert (tmp_path / "demo" / "README.md").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_project_generator_creates_gitignore(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_post_install():
        ProjectGenerator().generate(_cli_config())
    assert (tmp_path / "demo" / ".gitignore").exists()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_invalid_template_raises_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(name="demo", template="banana", use_git=False)
    with pytest.raises(SpawnError):
        ProjectGenerator().generate(config)


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_existing_directory_raises_error(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "demo").mkdir()
    with pytest.raises(SpawnError):
        ProjectGenerator().generate(_cli_config())


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_uv_failure_cleans_up_directory(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_uv.side_effect = SpawnError("uv not found")
    with _patch_post_install():
        with pytest.raises(SpawnError):
            ProjectGenerator().generate(_cli_config())
    assert not (tmp_path / "demo").exists()


@patch("spawn.generators.project_generator.initialize_uv")
@patch("spawn.generators.project_generator.initialize_git")
def test_git_failure_cleans_up_directory(mock_git, mock_uv, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_git.side_effect = SpawnError("Git is not installed or not available in PATH.")
    config = ProjectConfig(name="demo", template="cli", use_git=True)
    with _patch_post_install():
        with patch("spawn.generators.project_generator.install_packages"):
            with pytest.raises(SpawnError):
                ProjectGenerator().generate(config)
    assert not (tmp_path / "demo").exists()


# ---------------------------------------------------------------------------
# Starter file content
# ---------------------------------------------------------------------------


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_template_creates_main(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_post_install():
        ProjectGenerator().generate(_cli_config())
    assert (tmp_path / "demo" / "src" / "main.py").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_backend_api_fastapi_creates_main(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="demo", template="backend-api", use_git=False, framework="fastapi",
    )
    from spawn.templates.backend_api import BackendAPITemplate
    with patch.object(BackendAPITemplate, "post_install"):
        ProjectGenerator().generate(config)
    assert (tmp_path / "demo" / "app" / "main.py").exists()


def test_removed_template_slugs_raise_error(tmp_path, monkeypatch):
    """data-science and ml slugs have been retired — generator must raise SpawnError."""
    monkeypatch.chdir(tmp_path)
    for slug in ("data-science", "ml"):
        config = ProjectConfig(name="demo", template=slug, use_git=False)
        with pytest.raises(SpawnError, match=f"Unknown template: {slug}"):
            ProjectGenerator().generate(config)


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_starter_file_contains_project_name(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_post_install():
        ProjectGenerator().generate(_cli_config(name="my-app"))
    content = (tmp_path / "my-app" / "src" / "main.py").read_text(encoding="utf-8")
    assert "my-app" in content


# ---------------------------------------------------------------------------
# Phase 2 additions
# ---------------------------------------------------------------------------


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_mkdir_failure_raises_spawn_error_not_raw_exception(
    mock_uv, mock_install, tmp_path, monkeypatch
):
    """project_path.mkdir() raising PermissionError must surface as SpawnError."""
    from pathlib import Path

    monkeypatch.chdir(tmp_path)

    original_mkdir = Path.mkdir

    def _failing_mkdir(self, *args, **kwargs):
        if self.name == "demo" and not kwargs.get("exist_ok", False):
            raise PermissionError("Permission denied: 'demo'")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", _failing_mkdir)

    with pytest.raises(SpawnError):
        ProjectGenerator().generate(_cli_config())

    assert not (tmp_path / "demo").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_write_text_failure_raises_spawn_error_and_cleans_up(
    mock_uv, mock_install, tmp_path, monkeypatch
):
    """A write_text OSError mid-generation must wrap as SpawnError and remove the dir."""
    from pathlib import Path

    monkeypatch.chdir(tmp_path)

    original_write_text = Path.write_text
    call_count = 0

    def _failing_write_text(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise OSError("No space left on device")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", _failing_write_text)

    with _patch_post_install():
        with pytest.raises(SpawnError, match="No space left on device"):
            ProjectGenerator().generate(_cli_config())

    assert not (tmp_path / "demo").exists()


@patch("spawn.generators.project_generator.initialize_uv")
def test_nested_folder_path_is_created(mock_uv, tmp_path, monkeypatch):
    """A template that declares a nested folder like 'src/api' must create it."""
    monkeypatch.chdir(tmp_path)

    from spawn.templates.base import BaseTemplate

    nested_template = BaseTemplate(
        name="Nested Test",
        folders=["src/api"],
        starter_files=[],
    )

    with patch(
        "spawn.generators.project_generator.instantiate_template",
        return_value=nested_template,
    ):
        config = ProjectConfig(name="demo", template="nested", use_git=False)
        ProjectGenerator().generate(config)

    assert (tmp_path / "demo" / "src" / "api").is_dir()


# ---------------------------------------------------------------------------
# Phase 5D extras flow tests
# ---------------------------------------------------------------------------


def test_backend_api_extras_reach_template():
    """extras from ProjectConfig must be forwarded to BackendAPITemplate."""
    from spawn.core.registry import instantiate_template
    from spawn.templates.backend_api import BackendAPITemplate

    config = ProjectConfig(
        name="demo", template="backend-api", use_git=False,
        framework="fastapi", extras=["ruff", "pytest"],
    )
    template = instantiate_template(config)
    assert isinstance(template, BackendAPITemplate)
    assert template.extras == ["ruff", "pytest"]
    assert template.framework == "fastapi"


def test_backend_api_extras_in_dependencies():
    """ruff, pytest, and httpx must appear in get_dependencies() when selected."""
    from spawn.core.registry import instantiate_template

    config = ProjectConfig(
        name="demo", template="backend-api", use_git=False,
        framework="fastapi", extras=["ruff", "pytest"],
    )
    deps = instantiate_template(config).get_dependencies()
    assert "ruff" in deps
    assert "pytest" in deps
    assert "httpx" in deps


def test_backend_api_no_extras_excludes_optional_deps():
    """Without extras, ruff/pytest/httpx must NOT appear in dependencies."""
    from spawn.core.registry import instantiate_template

    config = ProjectConfig(
        name="demo", template="backend-api", use_git=False,
        framework="fastapi", extras=[],
    )
    deps = instantiate_template(config).get_dependencies()
    assert "ruff" not in deps
    assert "pytest" not in deps
    assert "httpx" not in deps
    assert "fastapi" in deps
    assert "uvicorn[standard]" in deps


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_generator_passes_extras_to_install_packages(
    mock_uv, mock_install, tmp_path, monkeypatch
):
    """ProjectGenerator must call install_packages with the full dependency list."""
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="demo", template="backend-api", use_git=False,
        framework="fastapi", extras=["ruff", "pytest"],
    )
    from spawn.templates.backend_api import BackendAPITemplate
    with patch.object(BackendAPITemplate, "post_install"):
        ProjectGenerator().generate(config)
    assert mock_install.called
    installed = mock_install.call_args[0][1]
    assert "ruff" in installed
    assert "pytest" in installed
    assert "httpx" in installed


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_argparse_template_never_calls_install_packages(
    mock_uv, mock_install, tmp_path, monkeypatch
):
    """argparse framework has no dependencies — install_packages must not be called."""
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="demo", template="cli", use_git=False, framework="argparse",
    )
    with _patch_post_install():
        ProjectGenerator().generate(config)
    mock_install.assert_not_called()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_generator_creates_spawn_meta_json(mock_uv, mock_install, tmp_path, monkeypatch):
    """Every generated project must have .spawn/meta.json."""
    import json

    monkeypatch.chdir(tmp_path)
    with _patch_post_install():
        ProjectGenerator().generate(_cli_config())

    meta_path = tmp_path / "demo" / ".spawn" / "meta.json"
    assert meta_path.exists(), ".spawn/meta.json was not created"

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert data["intent"] == "cli"
    assert data["framework"] is None
    assert "spawn_version" in data


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_backend_api_meta_json_has_framework(
    mock_uv, mock_install, tmp_path, monkeypatch
):
    """Backend API meta.json must record the selected framework."""
    import json

    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="demo", template="backend-api", use_git=False,
        framework="fastapi", extras=[],
    )
    from spawn.templates.backend_api import BackendAPITemplate
    with patch.object(BackendAPITemplate, "post_install"):
        ProjectGenerator().generate(config)

    data = json.loads(
        (tmp_path / "demo" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert data["intent"] == "backend-api"
    assert data["framework"] == "fastapi"


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_gitignore_contains_spawn_dir(mock_uv, mock_install, tmp_path, monkeypatch):
    """.gitignore in generated projects must exclude .spawn/."""
    monkeypatch.chdir(tmp_path)
    with _patch_post_install():
        ProjectGenerator().generate(_cli_config())
    gitignore = (tmp_path / "demo" / ".gitignore").read_text(encoding="utf-8")
    assert ".spawn/" in gitignore


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_meta_json_rollback_on_failure(mock_uv, mock_install, tmp_path, monkeypatch):
    """If meta.json write fails, rollback must remove the project dir."""
    from pathlib import Path

    monkeypatch.chdir(tmp_path)

    original_mkdir = Path.mkdir
    call_count = 0

    def failing_mkdir(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if self.name == ".spawn":
            raise OSError("Simulated .spawn mkdir failure")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", failing_mkdir)

    with _patch_post_install():
        with pytest.raises(SpawnError):
            ProjectGenerator().generate(_cli_config())

    assert not (tmp_path / "demo").exists()


# ---------------------------------------------------------------------------
# Automation Tool generator tests
# ---------------------------------------------------------------------------


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_automation_generator_creates_project(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_automation_post_install():
        ProjectGenerator().generate(_automation_config())
    assert (tmp_path / "demo").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_automation_generator_creates_folders(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_automation_post_install():
        ProjectGenerator().generate(_automation_config())
    assert (tmp_path / "demo" / "src" / "workflows").exists()
    assert (tmp_path / "demo" / "src" / "tasks").exists()
    assert (tmp_path / "demo" / "src" / "integrations").exists()
    assert (tmp_path / "demo" / "src" / "utils").exists()
    assert (tmp_path / "demo" / "logs").exists()
    assert (tmp_path / "demo" / "tests").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_automation_generator_creates_main(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_automation_post_install():
        ProjectGenerator().generate(_automation_config())
    assert (tmp_path / "demo" / "src" / "main.py").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_automation_generator_creates_env_example(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_automation_post_install():
        ProjectGenerator().generate(_automation_config())
    assert (tmp_path / "demo" / ".env.example").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_automation_generator_creates_meta_json(mock_uv, mock_install, tmp_path, monkeypatch):
    import json

    monkeypatch.chdir(tmp_path)
    with _patch_automation_post_install():
        ProjectGenerator().generate(_automation_config())
    meta = json.loads((tmp_path / "demo" / ".spawn" / "meta.json").read_text())
    assert meta["intent"] == "automation"


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_automation_main_contains_project_name(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_automation_post_install():
        ProjectGenerator().generate(_automation_config(name="my-bot"))
    content = (tmp_path / "my-bot" / "src" / "main.py").read_text(encoding="utf-8")
    assert "my-bot" in content


def test_automation_extras_in_dependencies():
    from spawn.core.registry import instantiate_template

    config = ProjectConfig(
        name="demo", template="automation", use_git=False, extras=["ruff", "pytest"]
    )
    deps = instantiate_template(config).get_dependencies()
    assert "ruff" in deps
    assert "pytest" in deps
    assert "requests" in deps
    assert "python-dotenv" in deps


# ---------------------------------------------------------------------------
# AI Chatbot generator tests
# ---------------------------------------------------------------------------


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_chatbot_generator_creates_project(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_chatbot_post_install():
        ProjectGenerator().generate(_chatbot_config())
    assert (tmp_path / "demo").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_chatbot_generator_creates_folders(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_chatbot_post_install():
        ProjectGenerator().generate(_chatbot_config())
    assert (tmp_path / "demo" / "src" / "chatbot").exists()
    assert (tmp_path / "demo" / "src" / "providers").exists()
    assert (tmp_path / "demo" / "src" / "prompts").exists()
    assert (tmp_path / "demo" / "src" / "utils").exists()
    assert (tmp_path / "demo" / "tests").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_chatbot_generator_creates_main(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_chatbot_post_install():
        ProjectGenerator().generate(_chatbot_config())
    assert (tmp_path / "demo" / "src" / "main.py").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_chatbot_generator_creates_env_example(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_chatbot_post_install():
        ProjectGenerator().generate(_chatbot_config())
    assert (tmp_path / "demo" / ".env.example").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_chatbot_generator_creates_meta_json(mock_uv, mock_install, tmp_path, monkeypatch):
    import json

    monkeypatch.chdir(tmp_path)
    with _patch_chatbot_post_install():
        ProjectGenerator().generate(_chatbot_config())
    meta = json.loads((tmp_path / "demo" / ".spawn" / "meta.json").read_text())
    assert meta["intent"] == "chatbot"
    assert meta["framework"] is None


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_chatbot_generator_with_openai_sdk_framework(mock_uv, mock_install, tmp_path, monkeypatch):
    import json

    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="demo", template="chatbot", use_git=False, framework="openai-sdk"
    )
    with _patch_chatbot_post_install():
        ProjectGenerator().generate(config)
    meta = json.loads((tmp_path / "demo" / ".spawn" / "meta.json").read_text())
    assert meta["framework"] == "openai-sdk"


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_chatbot_env_example_contains_project_name(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _patch_chatbot_post_install():
        ProjectGenerator().generate(_chatbot_config(name="my-bot"))
    content = (tmp_path / "my-bot" / ".env.example").read_text(encoding="utf-8")
    assert "my-bot" in content


def test_chatbot_pydantic_ai_extras_in_dependencies():
    from spawn.core.registry import instantiate_template

    config = ProjectConfig(
        name="demo", template="chatbot", use_git=False,
        framework="pydantic-ai", extras=["ruff", "pytest"],
    )
    deps = instantiate_template(config).get_dependencies()
    assert "pydantic-ai" in deps
    assert "openai" in deps
    assert "python-dotenv" in deps
    assert "ruff" in deps
    assert "pytest" in deps


def test_chatbot_openai_sdk_extras_in_dependencies():
    from spawn.core.registry import instantiate_template

    config = ProjectConfig(
        name="demo", template="chatbot", use_git=False,
        framework="openai-sdk", extras=["pytest"],
    )
    deps = instantiate_template(config).get_dependencies()
    assert "openai" in deps
    assert "python-dotenv" in deps
    assert "pytest" in deps
    assert "pydantic-ai" not in deps
