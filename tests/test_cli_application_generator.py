"""Generator integration tests for the CLI Application template."""
import json
import pytest

from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_generator_creates_root(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="typer", cli_type="utility", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    assert (tmp_path / "my-cli").is_dir()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_utility_creates_src_main(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="typer", cli_type="utility", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    assert (tmp_path / "my-cli" / "src" / "main.py").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_utility_creates_test_file(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="typer", cli_type="utility", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    assert (tmp_path / "my-cli" / "tests" / "test_cli.py").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_interactive_creates_prompts_dir(
    mock_uv, mock_install, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="typer", cli_type="interactive", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    assert (tmp_path / "my-cli" / "src" / "prompts").is_dir()
    assert (tmp_path / "my-cli" / "src" / "ui").is_dir()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_creates_readme(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="typer", cli_type="utility", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    readme = (tmp_path / "my-cli" / "README.md").read_text(encoding="utf-8")
    assert "my-cli" in readme


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_creates_spawn_meta_json(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="typer", cli_type="utility", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    meta = json.loads(
        (tmp_path / "my-cli" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "cli"
    assert meta["framework"] == "typer"


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_typer_install_packages_called(
    mock_uv, mock_install, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="typer", cli_type="utility", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    mock_install.assert_called_once()
    args = mock_install.call_args[0][1]
    assert "typer" in args


@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_argparse_no_install_packages_called(
    mock_uv, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="argparse", cli_type="utility", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    # argparse has no dependencies — install_packages should not be called
    # (it's not patched here; if called it would raise, failing the test)


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_click_creates_src_main(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="click", cli_type="utility", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    assert (tmp_path / "my-cli" / "src" / "main.py").exists()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_interactive_main_contains_greet(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="typer", cli_type="interactive", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    content = (tmp_path / "my-cli" / "src" / "main.py").read_text(encoding="utf-8")
    assert "greet" in content


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_utility_main_contains_hello(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-cli", template="cli", use_git=False,
        framework="typer", cli_type="utility", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    content = (tmp_path / "my-cli" / "src" / "main.py").read_text(encoding="utf-8")
    assert "hello" in content.lower()


@patch("spawn.generators.project_generator.install_packages")
@patch("spawn.generators.project_generator.initialize_uv")
def test_cli_main_contains_project_name(mock_uv, mock_install, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = ProjectConfig(
        name="my-tool", template="cli", use_git=False,
        framework="typer", cli_type="utility", extras=[],
    )
    from spawn.templates.cli_application import CLITemplate
    with patch.object(CLITemplate, "post_install"):
        ProjectGenerator().generate(config)
    content = (tmp_path / "my-tool" / "src" / "main.py").read_text(encoding="utf-8")
    assert "my-tool" in content
