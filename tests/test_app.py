"""Integration tests for cli/app.py using Typer's CliRunner.

All heavy I/O (filesystem, subprocess, prompts) is mocked so tests run
instantly without touching the real system.
"""

from pathlib import Path
from unittest.mock import patch

import typer
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.core.exceptions import SpawnError
from spawn.core.models import ProjectConfig
from spawn.github.exceptions import GitHubPublishError

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_CONFIG = ProjectConfig(name="demo", template="cli", use_git=True)
_VALID_CONFIG_NO_GIT = ProjectConfig(name="demo", template="cli", use_git=False)


def _fake_generate(_config: ProjectConfig) -> Path:
    """Stub that returns a plausible project path without touching the FS."""
    return Path("demo")


# ---------------------------------------------------------------------------
# spawn version
# ---------------------------------------------------------------------------


def test_version_prints_version_string():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Spawn v" in result.output


# ---------------------------------------------------------------------------
# spawn create — happy path (use_git=True, decline GitHub publish)
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG)
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.Confirm.ask", return_value=False)
def test_create_happy_path_declines_github(
    mock_confirm, mock_show_success, mock_generator_cls, mock_config
):
    mock_generator_cls.return_value.generate.side_effect = _fake_generate

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 0
    mock_show_success.assert_called_once()
    # Declined publish → no "Published" text
    assert "Published" not in result.output


# ---------------------------------------------------------------------------
# spawn create — use_git=False skips GitHub publish entirely
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG_NO_GIT)
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.Confirm.ask")
def test_create_no_git_skips_publish_prompt(
    mock_confirm, mock_show_success, mock_generator_cls, mock_config
):
    mock_generator_cls.return_value.generate.side_effect = _fake_generate

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 0
    assert "GitHub publishing requires Git" in result.output
    # Confirm.ask must never be called because we returned before it
    mock_confirm.assert_not_called()


# ---------------------------------------------------------------------------
# spawn create — generation raises SpawnError
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG)
@patch("spawn.generators.pipeline.ProjectGenerator")
def test_create_generation_error_prints_message(mock_generator_cls, mock_config):
    mock_generator_cls.return_value.generate.side_effect = SpawnError("disk full")

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 1
    assert "❌" in result.output
    assert "disk full" in result.output


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG)
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.GitHubPublisher")
def test_create_generation_error_does_not_attempt_publish(
    mock_publisher_cls, mock_generator_cls, mock_config
):
    mock_generator_cls.return_value.generate.side_effect = SpawnError("oops")

    runner.invoke(app, ["create"])

    mock_publisher_cls.return_value.publish.assert_not_called()


# ---------------------------------------------------------------------------
# spawn create — GitHub publish success
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG)
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.Confirm.ask", return_value=True)
@patch("spawn.cli.app.Prompt.ask", return_value="https://github.com/user/repo.git")
@patch("spawn.cli.app.GitHubPublisher")
def test_create_github_publish_success(
    mock_publisher_cls,
    mock_prompt,
    mock_confirm,
    mock_show_success,
    mock_generator_cls,
    mock_config,
):
    mock_generator_cls.return_value.generate.side_effect = _fake_generate
    mock_publisher_cls.return_value.publish.return_value = None

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 0
    assert "Published successfully" in result.output


# ---------------------------------------------------------------------------
# spawn create — GitHub publish raises GitHubPublishError
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config", return_value=_VALID_CONFIG)
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.Confirm.ask", return_value=True)
@patch("spawn.cli.app.Prompt.ask", return_value="https://github.com/user/repo.git")
@patch("spawn.cli.app.GitHubPublisher")
def test_create_github_publish_error_prints_message(
    mock_publisher_cls,
    mock_prompt,
    mock_confirm,
    mock_show_success,
    mock_generator_cls,
    mock_config,
):
    mock_generator_cls.return_value.generate.side_effect = _fake_generate
    mock_publisher_cls.return_value.publish.side_effect = GitHubPublishError(
        "push rejected"
    )

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 6
    assert "❌" in result.output
    assert "push rejected" in result.output


# ---------------------------------------------------------------------------
# spawn doctor — path validation
# ---------------------------------------------------------------------------


def test_doctor_nonexistent_path(tmp_path):
    nonexistent = str(tmp_path / "does_not_exist")
    result = runner.invoke(app, ["doctor", nonexistent])
    assert result.exit_code == 1
    assert "Path does not exist" in result.output


def test_doctor_path_is_file_not_directory(tmp_path):
    f = tmp_path / "somefile.txt"
    f.write_text("hello", encoding="utf-8")
    result = runner.invoke(app, ["doctor", str(f)])
    assert result.exit_code == 1
    assert "Path is not a directory" in result.output


# ---------------------------------------------------------------------------
# spawn doctor — --fix, --dry-run, --yes, --license
# ---------------------------------------------------------------------------


def test_doctor_without_flags_unchanged(tmp_path):
    result = runner.invoke(app, ["doctor", str(tmp_path)])
    assert result.exit_code == 0
    assert "Project Health Report" in result.output
    assert "→" not in result.output
    assert "Planned fixes" not in result.output


def test_doctor_dry_run_alone_exits_1(tmp_path):
    result = runner.invoke(app, ["doctor", str(tmp_path), "--dry-run"])
    assert result.exit_code == 1
    assert "--dry-run requires --fix" in result.output


def test_doctor_fix_dry_run_writes_nothing(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
    files_before = set(tmp_path.iterdir())
    result = runner.invoke(app, ["doctor", str(tmp_path), "--fix", "--dry-run"])
    assert result.exit_code == 0
    assert "Planned fixes" in result.output
    assert set(tmp_path.iterdir()) == files_before


def test_doctor_fix_yes_creates_files_and_score_improves(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )

    def fake_git(p):
        (p / ".git").mkdir()

    with patch("spawn.utils.doctor_fix.initialize_git", side_effect=fake_git):
        result = runner.invoke(app, ["doctor", str(tmp_path), "--fix", "--yes"])
    assert result.exit_code == 0
    assert (tmp_path / "README.md").is_file()
    assert (tmp_path / ".gitignore").is_file()
    assert "Score:" in result.output
    assert "→" in result.output


def test_doctor_second_run_prints_nothing_to_fix_or_manual_items(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )

    def fake_git(p):
        (p / ".git").mkdir()

    with patch("spawn.utils.doctor_fix.initialize_git", side_effect=fake_git):
        runner.invoke(app, ["doctor", str(tmp_path), "--fix", "--yes"])
        result = runner.invoke(app, ["doctor", str(tmp_path), "--fix", "--yes"])
    assert result.exit_code == 0
    assert "Nothing to fix" in result.output or "Needs manual action" in result.output
    assert "Planned fixes" not in result.output


def test_doctor_fix_yes_license_mit_writes_license(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
    with patch("spawn.utils.doctor_fix.initialize_git"):
        result = runner.invoke(
            app, ["doctor", str(tmp_path), "--fix", "--yes", "--license", "mit"]
        )
    assert result.exit_code == 0
    assert (tmp_path / "LICENSE").is_file()
    assert "MIT License" in (tmp_path / "LICENSE").read_text(encoding="utf-8")


def test_doctor_fix_with_input_n_applies_nothing(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
    files_before = set(tmp_path.iterdir())
    result = runner.invoke(app, ["doctor", str(tmp_path), "--fix"], input="n\n")
    assert result.exit_code == 0
    assert "Cancelled." in result.output
    assert set(tmp_path.iterdir()) == files_before


def test_doctor_typer_abort_exits_130_with_cancelled(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
    with patch("spawn.cli.app.typer.confirm", side_effect=typer.Abort):
        result = runner.invoke(app, ["doctor", str(tmp_path), "--fix"])
    assert result.exit_code == 130
    assert "Cancelled." in result.output


# ---------------------------------------------------------------------------
# spawn create — non-interactive (--name / --template flags)
# ---------------------------------------------------------------------------

_VALID_AUTO_CONFIG = ProjectConfig(name="demo", template="automation", use_git=True)
_VALID_AUTO_CONFIG_NO_GIT = ProjectConfig(
    name="demo", template="automation", use_git=False
)


@patch("spawn.cli.app.get_project_config")
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.instantiate_template")
@patch("spawn.cli.app.Confirm.ask", return_value=False)
def test_noninteractive_name_template_succeeds(
    mock_confirm,
    mock_instantiate,
    mock_show_success,
    mock_generator_cls,
    mock_get_config,
):
    """--name + --template skips get_project_config entirely and exits 0."""
    mock_generator_cls.return_value.generate.return_value = Path("demo")
    mock_instantiate.return_value = None

    result = runner.invoke(
        app, ["create", "--name", "demo", "--template", "automation"]
    )

    assert result.exit_code == 0
    assert mock_get_config.call_count == 0


@patch("spawn.cli.app.get_project_config")
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.instantiate_template")
def test_noninteractive_dry_run_does_not_generate(
    mock_instantiate, mock_generator_cls, mock_get_config
):
    """--dry-run prints config-valid message and never calls generate()."""
    result = runner.invoke(
        app, ["create", "--name", "demo", "--template", "automation", "--dry-run"]
    )

    assert result.exit_code == 0
    assert "Config valid" in result.output
    assert mock_generator_cls.return_value.generate.call_count == 0


def test_noninteractive_unknown_template_exits_1():
    """--template with an unrecognised slug exits 1 and reports the error."""
    result = runner.invoke(
        app, ["create", "--name", "demo", "--template", "bogus-template"]
    )

    assert result.exit_code == 1
    assert "Unknown template" in result.output


def test_noninteractive_invalid_project_name_exits_nonzero():
    """An invalid project name (contains spaces) exits non-zero."""
    result = runner.invoke(
        app, ["create", "--name", "bad name!", "--template", "automation"]
    )

    assert result.exit_code != 0


@patch("spawn.cli.app.get_project_config", return_value=_VALID_AUTO_CONFIG)
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.Confirm.ask", return_value=False)
def test_template_only_no_name_falls_through_to_interactive(
    mock_confirm, mock_show_success, mock_generator_cls, mock_get_config
):
    """--template without --name is NOT non-interactive; get_project_config is called."""
    mock_generator_cls.return_value.generate.side_effect = _fake_generate

    result = runner.invoke(app, ["create", "--template", "automation"])

    assert result.exit_code == 0
    assert mock_get_config.call_count == 1


# ---------------------------------------------------------------------------
# spawn create — non-interactive (--config file)
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config")
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.instantiate_template")
def test_config_file_valid_succeeds(
    mock_instantiate, mock_show_success, mock_generator_cls, mock_get_config, tmp_path
):
    """--config with a valid JSON file exits 0 and never calls get_project_config."""
    cfg = tmp_path / "spawn.json"
    cfg.write_text('{"name": "demo", "template": "automation"}', encoding="utf-8")
    mock_generator_cls.return_value.generate.return_value = Path("demo")
    mock_instantiate.return_value = None

    result = runner.invoke(app, ["create", "--config", str(cfg)])

    assert result.exit_code == 0
    assert mock_get_config.call_count == 0


def test_config_file_missing_exits_1(tmp_path):
    """--config pointing at a nonexistent file exits 1."""
    missing = str(tmp_path / "no_such_file.json")

    result = runner.invoke(app, ["create", "--config", missing])

    assert result.exit_code == 1
    assert "Config file not found" in result.output


# ---------------------------------------------------------------------------
# spawn create — --yes skips GitHub publish prompt
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config")
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.instantiate_template")
@patch("spawn.cli.app.Confirm.ask")
def test_yes_flag_skips_confirm_ask(
    mock_confirm,
    mock_instantiate,
    mock_show_success,
    mock_generator_cls,
    mock_get_config,
):
    """--yes must prevent Confirm.ask from ever being called."""
    mock_generator_cls.return_value.generate.return_value = Path("demo")
    mock_instantiate.return_value = None

    result = runner.invoke(
        app, ["create", "--name", "demo", "--template", "automation", "--yes"]
    )

    assert result.exit_code == 0
    assert mock_confirm.call_count == 0


@patch("spawn.cli.app.get_project_config")
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.instantiate_template")
@patch("spawn.cli.app.Confirm.ask")
def test_noninteractive_without_yes_also_skips_confirm_ask(
    mock_confirm,
    mock_instantiate,
    mock_show_success,
    mock_generator_cls,
    mock_get_config,
):
    """Non-interactive mode alone (no --yes) must also skip Confirm.ask."""
    mock_generator_cls.return_value.generate.return_value = Path("demo")
    mock_instantiate.return_value = None

    result = runner.invoke(
        app, ["create", "--name", "demo", "--template", "automation"]
    )

    assert result.exit_code == 0
    assert mock_confirm.call_count == 0


# ---------------------------------------------------------------------------
# spawn create — --claude-md flag
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config")
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.instantiate_template")
def test_claude_md_flag_sets_generate_claude_md_on_config(
    mock_instantiate, mock_show_success, mock_generator_cls, mock_get_config
):
    """--claude-md must result in generate_claude_md=True on the config passed to generate()."""
    captured = {}

    def capture_generate(config):
        captured["config"] = config
        return Path("demo")

    mock_generator_cls.return_value.generate.side_effect = capture_generate
    mock_instantiate.return_value = None

    result = runner.invoke(
        app,
        ["create", "--name", "demo", "--template", "automation", "--claude-md"],
    )

    assert result.exit_code == 0
    assert "config" in captured
    assert captured["config"].generate_claude_md is True


@patch("spawn.cli.app.get_project_config")
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.instantiate_template")
def test_no_claude_md_flag_defaults_false(
    mock_instantiate, mock_show_success, mock_generator_cls, mock_get_config
):
    """Without --claude-md the config must have generate_claude_md=False (default)."""
    captured = {}

    def capture_generate(config):
        captured["config"] = config
        return Path("demo")

    mock_generator_cls.return_value.generate.side_effect = capture_generate
    mock_instantiate.return_value = None

    result = runner.invoke(
        app,
        ["create", "--name", "demo", "--template", "automation"],
    )

    assert result.exit_code == 0
    assert captured["config"].generate_claude_md is False


@patch("spawn.cli.app.get_project_config")
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.instantiate_template")
def test_license_none_reaches_generator_config(
    mock_instantiate, mock_show_success, mock_generator_cls, mock_get_config
):
    """--license none must result in license='none' on the config passed to generate()."""
    captured = {}

    def capture_generate(config):
        captured["config"] = config
        return Path("demo")

    mock_generator_cls.return_value.generate.side_effect = capture_generate
    mock_instantiate.return_value = None

    result = runner.invoke(
        app,
        ["create", "--name", "demo", "--template", "automation", "--license", "none"],
    )

    assert result.exit_code == 0
    assert "config" in captured
    assert captured["config"].license == "none"


# ---------------------------------------------------------------------------
# Bug regressions — Bug 1 (config-file path for --claude-md)
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config")
@patch("spawn.generators.pipeline.ProjectGenerator")
@patch("spawn.cli.app.show_success")
@patch("spawn.cli.app.instantiate_template")
def test_claude_md_via_config_file_sets_generate_claude_md(
    mock_instantiate, mock_show_success, mock_generator_cls, mock_get_config, tmp_path
):
    """--config file with claude_md:true must result in generate_claude_md=True on config."""
    captured = {}

    def capture_generate(config):
        captured["config"] = config
        return Path("demo")

    mock_generator_cls.return_value.generate.side_effect = capture_generate
    mock_instantiate.return_value = None

    cfg = tmp_path / "spawn.json"
    cfg.write_text(
        '{"name": "demo", "template": "automation", "claude_md": true}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["create", "--config", str(cfg)])

    assert result.exit_code == 0
    assert "config" in captured
    assert captured["config"].generate_claude_md is True


# ---------------------------------------------------------------------------
# Bug regressions — Bug 2 (Custom Structure generate_claude_md wiring)
# ---------------------------------------------------------------------------


@patch("spawn.cli.app.get_project_config")
def test_custom_structure_generate_called_with_claude_md(mock_get_config, tmp_path):
    """When config.generate_claude_md is True, CustomStructureGenerator.generate
    must be called with generate_claude_md=True."""
    from spawn.core.models import ProjectConfig
    from spawn.generators.custom_structure import ParsedEntry

    mock_get_config.return_value = ProjectConfig(
        name="cs-proj",
        template="custom",
        use_git=False,
        use_uv=False,
        custom_entries=[ParsedEntry(path="AGENTS.md", is_file=True)],
        generate_claude_md=True,
    )

    with (
        patch("spawn.generators.pipeline.CustomStructureGenerator") as mock_gen_cls,
        patch("spawn.generators.pipeline.write_project_meta"),
        patch("spawn.cli.app.show_success"),
    ):
        mock_gen_cls.return_value.generate.return_value = Path("cs-proj")
        runner.invoke(app, ["create"])

    call_kwargs = mock_gen_cls.return_value.generate.call_args[1]
    assert call_kwargs.get("generate_claude_md") is True
