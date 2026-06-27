"""Generator integration tests for the Automation Tool template."""
import json

from contextlib import contextmanager
from unittest.mock import patch

from spawn.core.models import ProjectConfig
from spawn.generators.project_generator import ProjectGenerator
from spawn.templates.automation import AutomationTemplate


def _cfg(name: str = "demo", extras: list[str] | None = None) -> ProjectConfig:
    return ProjectConfig(
        name=name,
        template="automation",
        use_git=False,
        extras=extras or [],
    )


@contextmanager
def _mock_uv_and_install():
    with patch("spawn.generators.project_generator.install_packages") as mock_install, \
         patch("spawn.generators.project_generator.initialize_uv") as mock_uv, \
         patch.object(AutomationTemplate, "post_install"):
        yield mock_install, mock_uv


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------


def test_automation_creates_root_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo").is_dir()


def test_automation_creates_workflows_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "src" / "workflows").is_dir()


def test_automation_creates_tasks_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "src" / "tasks").is_dir()


def test_automation_creates_integrations_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "src" / "integrations").is_dir()


def test_automation_creates_utils_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "src" / "utils").is_dir()


def test_automation_creates_logs_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "logs").is_dir()


def test_automation_creates_tests_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "tests").is_dir()


# ---------------------------------------------------------------------------
# File tests
# ---------------------------------------------------------------------------


def test_automation_creates_main(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "src" / "main.py").exists()


def test_automation_creates_logger(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "src" / "utils" / "logger.py").exists()


def test_automation_creates_report_workflow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "src" / "workflows" / "report_workflow.py").exists()


def test_automation_creates_data_task(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "src" / "tasks" / "data_task.py").exists()


def test_automation_creates_report_task(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "src" / "tasks" / "report_task.py").exists()


def test_automation_creates_test_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "tests" / "test_automation.py").exists()


def test_automation_creates_env_example(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / ".env.example").exists()


def test_automation_creates_logs_gitkeep(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / "logs" / ".gitkeep").exists()


# ---------------------------------------------------------------------------
# Content tests
# ---------------------------------------------------------------------------


def test_automation_main_contains_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="my-bot"))
    content = (tmp_path / "my-bot" / "src" / "main.py").read_text(encoding="utf-8")
    assert "my-bot" in content


def test_automation_readme_contains_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="my-bot"))
    readme = (tmp_path / "my-bot" / "README.md").read_text(encoding="utf-8")
    assert "my-bot" in readme


def test_automation_env_example_contains_project_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg(name="my-bot"))
    env = (tmp_path / "my-bot" / ".env.example").read_text(encoding="utf-8")
    assert "my-bot" in env


def test_automation_gitignore_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    assert (tmp_path / "demo" / ".gitignore").exists()


def test_automation_gitignore_excludes_log_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    gitignore = (tmp_path / "demo" / ".gitignore").read_text(encoding="utf-8")
    assert "logs/*.log" in gitignore


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


def test_automation_creates_spawn_meta_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install():
        ProjectGenerator().generate(_cfg())
    meta = json.loads(
        (tmp_path / "demo" / ".spawn" / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["intent"] == "automation"
    assert meta["framework"] is None


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def test_automation_install_packages_called_with_requests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install() as (mock_install, _):
        ProjectGenerator().generate(_cfg())
    args = mock_install.call_args[0][1]
    assert "requests" in args
    assert "python-dotenv" in args


def test_automation_extras_reach_install_packages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with _mock_uv_and_install() as (mock_install, _):
        ProjectGenerator().generate(_cfg(extras=["ruff", "pytest"]))
    args = mock_install.call_args[0][1]
    assert "ruff" in args
    assert "pytest" in args
