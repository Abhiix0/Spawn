"""`spawn create` flag correctness: --no-uv extras, interactive --dry-run, --config conflicts."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.core.models import ProjectConfig
from spawn.core.registry import get_metadata
from spawn.generators import project_generator

runner = CliRunner()

# slug -> extra CLI options selecting one framework/type
TEMPLATES = {
    "backend-api": ["--framework", "fastapi"],
    "cli": ["--framework", "typer", "--cli-type", "utility"],
    "automation": [],
    "chatbot": ["--framework", "pydantic-ai"],
    "agent": ["--framework", "pydantic-ai"],
    "rag": [],
    "data": ["--data-type", "Data Analysis"],
    "mcp": [],
}


def _fake_uv_init(project_path):
    (Path(project_path) / "pyproject.toml").write_text("[project]\n", encoding="utf-8")


@pytest.fixture
def offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spies = {
        "initialize_uv": MagicMock(side_effect=_fake_uv_init),
        "install_packages": MagicMock(),
        "initialize_git": MagicMock(),
    }
    for name, spy in spies.items():
        monkeypatch.setattr(project_generator, name, spy)
    return spies


def _flat(output: str) -> str:
    return " ".join(output.split())


def _create(slug, extras, *flags):
    args = ["create", "--name", "p", "--template", slug, *TEMPLATES[slug]]
    if extras:
        args += ["--extras", ",".join(extras)]
    return runner.invoke(app, [*args, *flags])


def _meta():
    return json.loads(Path("p/.spawn/meta.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("slug", TEMPLATES)
def test_no_uv_keeps_file_only_extras_and_warns(offline, slug):
    extras = get_metadata(slug).available_extras
    result = _create(slug, extras, "--no-git", "--no-uv", "--yes")

    assert result.exit_code == 0, result.output
    project = Path("p")
    assert (project / ".pre-commit-config.yaml").is_file()
    # These need pyproject.toml (CI and Docker both run `uv sync`).
    assert not (project / "pyproject.toml").exists()
    assert not (project / ".github" / "workflows" / "ci.yml").exists()
    assert not (project / "Dockerfile").exists()
    assert not (project / ".dockerignore").exists()

    skipped = [e for e in extras if e != "pre-commit"]
    assert f"Skipped without uv: {', '.join(skipped)} (need pyproject.toml)" in _flat(
        result.output
    )
    assert _flat(result.output).count("Skipped without uv") == 1
    offline["initialize_uv"].assert_not_called()
    offline["install_packages"].assert_not_called()
    assert _meta()["uv"] is False


@pytest.mark.parametrize("slug", TEMPLATES)
def test_no_uv_without_extras_no_warning(offline, slug):
    result = _create(slug, [], "--no-git", "--no-uv", "--yes")
    assert result.exit_code == 0, result.output
    assert "Skipped without uv" not in result.output
    assert not Path("p/.pre-commit-config.yaml").exists()


def test_no_uv_only_precommit_has_no_warning(offline):
    result = _create("mcp", ["pre-commit"], "--no-git", "--no-uv", "--yes")
    assert result.exit_code == 0, result.output
    assert Path("p/.pre-commit-config.yaml").is_file()
    assert "Skipped without uv" not in result.output


@pytest.mark.parametrize("slug", TEMPLATES)
def test_with_uv_all_extras_still_applied(offline, slug):
    extras = get_metadata(slug).available_extras
    result = _create(slug, extras, "--no-git", "--yes")

    assert result.exit_code == 0, result.output
    assert "Skipped without uv" not in result.output
    project = Path("p")
    assert (project / ".pre-commit-config.yaml").is_file()
    assert (project / ".github" / "workflows" / "ci.yml").is_file()
    assert "[tool.mypy]" in (project / "pyproject.toml").read_text(encoding="utf-8")
    offline["initialize_uv"].assert_called_once()
    dev_calls = [
        c for c in offline["install_packages"].call_args_list if c.kwargs.get("dev")
    ]
    assert dev_calls[0].args[1] == ["mypy", "pre-commit"]
    if slug == "backend-api":
        assert (project / "Dockerfile").is_file()
        assert (project / ".dockerignore").is_file()
    assert _meta()["uv"] is True


# ---------------------------------------------------------------------------
# Interactive --dry-run
# ---------------------------------------------------------------------------

_INTERACTIVE_CONFIG = ProjectConfig(name="demo", template="cli", use_git=False)


@patch("spawn.cli.app.generate_project")
@patch("spawn.cli.app.get_project_config", return_value=_INTERACTIVE_CONFIG)
def test_interactive_dry_run_writes_nothing(
    mock_get, mock_generate, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["create", "--dry-run"])

    assert list(tmp_path.iterdir()) == []
    assert result.exit_code == 0, result.output
    assert "Config valid" in result.output
    mock_get.assert_called_once()
    mock_generate.assert_not_called()


# ---------------------------------------------------------------------------
# --config combined with --no-git / --no-uv
# ---------------------------------------------------------------------------


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "spawn.json"
    path.write_text(
        json.dumps({"name": "demo", "template": "mcp", "git": True, "uv": True}),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(
    "flag, other",
    [("--no-git", "--no-uv"), ("--no-uv", "--no-git")],
)
def test_config_with_conflicting_flag_warns(config_file, flag, other):
    with patch("spawn.cli.app.generate_project") as mock_generate:
        mock_generate.return_value = Path("demo")
        result = runner.invoke(
            app, ["create", "--config", str(config_file), flag, "--dry-run"]
        )

    assert result.exit_code == 0, result.output
    assert f"{flag} ignored: --config takes precedence" in result.output
    assert f"{other} ignored" not in result.output
    assert "use_git=True" in _flat(result.output)
    assert "use_uv=True" in _flat(result.output)


def test_config_with_both_flags_warns_for_each(config_file):
    result = runner.invoke(
        app,
        ["create", "--config", str(config_file), "--no-git", "--no-uv", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert "--no-git ignored: --config takes precedence" in result.output
    assert "--no-uv ignored: --config takes precedence" in result.output


def test_config_without_flags_no_warning(config_file):
    result = runner.invoke(app, ["create", "--config", str(config_file), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "ignored" not in result.output


def test_config_values_used_for_generation(config_file):
    with patch("spawn.cli.app.generate_project") as mock_generate:
        mock_generate.return_value = Path("demo")
        result = runner.invoke(
            app, ["create", "--config", str(config_file), "--no-git", "--no-uv"]
        )

    assert result.exit_code == 0, result.output
    config = mock_generate.call_args.args[0]
    assert config.use_git is True and config.use_uv is True
