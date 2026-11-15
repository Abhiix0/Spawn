"""Regression tests for Issue 5: --no-uv next-step guidance.

Verifies that:
- show_success strips "uv run " from every step when use_uv=False
- show_success preserves "uv run " prefix when use_uv=True
- Steps not starting with "uv run " are unaffected in both modes
- The full create CLI path (--no-uv flag) prints correct commands
"""

import pytest
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.utils.success import show_success


# ---------------------------------------------------------------------------
# show_success unit tests
# ---------------------------------------------------------------------------


def _capture_success(capsys, next_steps, use_uv):
    show_success(
        project_name="my-proj",
        template_name="Test",
        use_git=False,
        next_steps=next_steps,
        use_uv=use_uv,
    )
    return capsys.readouterr().out


def test_no_uv_strips_uv_run_prefix(capsys):
    output = _capture_success(
        capsys,
        next_steps=["cd {project_name}", "uv run python -m src.main hello"],
        use_uv=False,
    )
    assert "uv run" not in output
    assert "python -m src.main hello" in output


def test_uv_mode_preserves_uv_run_prefix(capsys):
    output = _capture_success(
        capsys,
        next_steps=["cd {project_name}", "uv run python -m src.main hello"],
        use_uv=True,
    )
    assert "uv run python -m src.main hello" in output


def test_no_uv_non_uv_steps_unchanged(capsys):
    """Steps without 'uv run' must pass through unmodified."""
    output = _capture_success(
        capsys,
        next_steps=["cd {project_name}", "python -m src.main hello"],
        use_uv=False,
    )
    assert "python -m src.main hello" in output


def test_uv_mode_non_uv_steps_unchanged(capsys):
    output = _capture_success(
        capsys,
        next_steps=["cd {project_name}", "python -m src.main hello"],
        use_uv=True,
    )
    assert "python -m src.main hello" in output


def test_no_uv_project_name_substituted(capsys):
    output = _capture_success(
        capsys,
        next_steps=["cd {project_name}"],
        use_uv=False,
    )
    assert "my-proj" in output
    assert "{project_name}" not in output


def test_multiple_uv_steps_all_stripped(capsys):
    output = _capture_success(
        capsys,
        next_steps=[
            "cd {project_name}",
            "uv run uvicorn app.main:app --reload",
            "uv run pytest",
        ],
        use_uv=False,
    )
    assert "uv run" not in output
    assert "uvicorn app.main:app --reload" in output
    assert "pytest" in output


# ---------------------------------------------------------------------------
# CLI integration: --no-uv flag produces correct next-step output
# ---------------------------------------------------------------------------


runner = CliRunner()


def test_create_no_uv_output_does_not_contain_uv_run(
    tmp_path, monkeypatch, no_toolchain
):
    """spawn create --name x --template mcp --no-uv must not print 'uv run' in next steps."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["create", "--name", "myproj", "--template", "mcp", "--no-uv", "--no-git"],
    )
    assert result.exit_code == 0, result.output
    # The Next Steps section must not contain "uv run"
    if "Next Steps" in result.output:
        lines_after = result.output.split("Next Steps")[1]
        assert "uv run" not in lines_after


def test_create_with_uv_output_contains_uv_run(tmp_path, monkeypatch, no_toolchain):
    """spawn create with uv enabled should still print 'uv run' in next steps."""
    monkeypatch.chdir(tmp_path)
    # Stub post_install so it doesn't require a real pyproject.toml (which
    # would normally be created by uv init, but uv is stubbed by no_toolchain).
    from spawn.templates.mcp_server import MCPServerTemplate

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(MCPServerTemplate, "post_install", lambda self, p: None)
        result = runner.invoke(
            app,
            ["create", "--name", "myproj2", "--template", "mcp", "--no-git"],
        )
    assert result.exit_code == 0, result.output
    assert "uv run" in result.output
