from spawn.templates.automation import AutomationTemplate


def test_automation_template_default():
    t = AutomationTemplate()
    assert t.name == "Automation Tool"
    assert t.extras == []


def test_automation_template_folders():
    t = AutomationTemplate()
    assert "src/workflows" in t.folders
    assert "src/tasks" in t.folders
    assert "src/integrations" in t.folders
    assert "src/utils" in t.folders
    assert "logs" in t.folders
    assert "tests" in t.folders


def test_automation_template_starter_files():
    t = AutomationTemplate()
    paths = [path for path, _ in t.starter_files]
    assert "src/main.py" in paths
    assert "src/workflows/report_workflow.py" in paths
    assert "src/tasks/data_task.py" in paths
    assert "src/tasks/report_task.py" in paths
    assert "src/utils/logger.py" in paths
    assert "tests/test_automation.py" in paths
    assert ".env.example" in paths
    assert "logs/.gitkeep" in paths


def test_automation_base_dependencies():
    t = AutomationTemplate()
    deps = t.get_dependencies()
    assert "requests" in deps
    assert "python-dotenv" in deps


def test_automation_extras_add_deps():
    t = AutomationTemplate(extras=["pytest", "ruff"])
    deps = t.get_dependencies()
    assert "pytest" in deps
    assert "ruff" in deps


def test_automation_no_extras_excludes_optional_deps():
    t = AutomationTemplate()
    deps = t.get_dependencies()
    assert "pytest" not in deps
    assert "ruff" not in deps


def test_automation_readme_contains_project_name():
    t = AutomationTemplate()
    readme = t.get_readme_content({"project_name": "my-automation"})
    assert "my-automation" in readme


def test_automation_starter_file_paths_are_strings():
    t = AutomationTemplate()
    for path, _ in t.starter_files:
        assert isinstance(path, str)


def test_automation_next_steps():
    t = AutomationTemplate()
    assert any("src.main" in step for step in t.next_steps)
