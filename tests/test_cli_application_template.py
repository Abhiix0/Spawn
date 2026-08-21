"""Unit tests for CLITemplate — no filesystem, no subprocess."""
from spawn.templates.cli_application import CLITemplate


def test_cli_template_default_name():
    t = CLITemplate()
    assert t.name == "CLI Application"


def test_cli_template_default_framework_is_typer():
    t = CLITemplate()
    assert t.framework == "typer"


def test_cli_template_default_cli_type_is_utility():
    t = CLITemplate()
    assert t.cli_type == "utility"


def test_cli_template_default_extras_empty():
    t = CLITemplate()
    assert t.extras == []


def test_cli_utility_folders():
    t = CLITemplate(cli_type="utility")
    assert "src/commands" in t.folders
    assert "src/utils" in t.folders
    assert "tests" in t.folders
    assert "src/prompts" not in t.folders
    assert "src/ui" not in t.folders


def test_cli_interactive_folders():
    t = CLITemplate(cli_type="interactive")
    assert "src/commands" in t.folders
    assert "src/prompts" in t.folders
    assert "src/ui" in t.folders
    assert "src/utils" in t.folders
    assert "tests" in t.folders


def test_cli_utility_has_main():
    t = CLITemplate(cli_type="utility")
    paths = [p for p, _ in t.starter_files]
    assert "src/main.py" in paths
    assert "tests/test_cli.py" in paths


def test_cli_interactive_has_main():
    t = CLITemplate(cli_type="interactive")
    paths = [p for p, _ in t.starter_files]
    assert "src/main.py" in paths
    assert "tests/test_cli.py" in paths


def test_cli_typer_dependencies():
    t = CLITemplate(framework="typer")
    assert "typer" in t.get_dependencies()


def test_cli_click_dependencies():
    t = CLITemplate(framework="click")
    assert "click" in t.get_dependencies()
    assert "typer" not in t.get_dependencies()


def test_cli_argparse_no_dependencies():
    t = CLITemplate(framework="argparse")
    assert t.get_dependencies() == []


def test_cli_argparse_with_pytest_extra():
    t = CLITemplate(framework="argparse", extras=["pytest"])
    assert "pytest" in t.get_dependencies()


def test_cli_typer_with_all_extras():
    t = CLITemplate(framework="typer", extras=["ruff", "pytest"])
    deps = t.get_dependencies()
    assert "typer" in deps
    assert "ruff" in deps
    assert "pytest" in deps


def test_cli_readme_content_contains_project_name():
    t = CLITemplate(framework="typer")
    readme = t.get_readme_content({"project_name": "my-cli"})
    assert readme is not None
    assert "my-cli" in readme


def test_cli_click_readme_not_none():
    t = CLITemplate(framework="click")
    assert t.get_readme_content({"project_name": "x"}) is not None


def test_cli_argparse_readme_not_none():
    t = CLITemplate(framework="argparse")
    assert t.get_readme_content({"project_name": "x"}) is not None


def test_cli_utility_next_steps_contain_hello():
    t = CLITemplate(cli_type="utility")
    assert any("hello" in step for step in t.next_steps)


def test_cli_interactive_next_steps_contain_greet():
    t = CLITemplate(cli_type="interactive")
    assert any("greet" in step for step in t.next_steps)


def test_cli_typer_main_content_interpolates():
    t = CLITemplate(framework="typer")
    content = dict(t.starter_files)["src/main.py"]
    result = content.format_map({"project_name": "test-tool"})
    assert "test-tool" in result


def test_cli_all_starter_file_paths_are_strings():
    for fw in ["typer", "click", "argparse"]:
        for ct in ["utility", "interactive"]:
            t = CLITemplate(framework=fw, cli_type=ct)
            for path, content in t.starter_files:
                assert isinstance(path, str)
                assert isinstance(content, str)


# ---------------------------------------------------------------------------
# post_install
# ---------------------------------------------------------------------------


def test_cli_post_install_adds_pytest_section(tmp_path):
    t = CLITemplate(framework="typer", extras=["pytest"])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    t.post_install(tmp_path)
    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.pytest.ini_options]" in content
    assert 'testpaths = ["tests"]' in content


def test_cli_post_install_adds_ruff_section(tmp_path):
    t = CLITemplate(framework="typer", extras=["ruff"])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    t.post_install(tmp_path)
    content = pyproject.read_text(encoding="utf-8")
    assert "[tool.ruff]" in content
    assert "line-length = 88" in content


def test_cli_post_install_no_extras_does_not_modify_pyproject(tmp_path):
    t = CLITemplate(framework="typer", extras=[])
    original = "[project]\nname = \"demo\"\n"
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(original, encoding="utf-8")
    t.post_install(tmp_path)
    assert pyproject.read_text(encoding="utf-8") == original


def test_cli_post_install_github_actions_creates_ci_yml(tmp_path):
    t = CLITemplate(framework="typer", extras=["github-actions"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    t.post_install(tmp_path)
    ci_path = tmp_path / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists()
    content = ci_path.read_text(encoding="utf-8")
    assert "uv sync" in content


def test_cli_post_install_github_actions_with_ruff_and_pytest(tmp_path):
    t = CLITemplate(framework="typer", extras=["github-actions", "ruff", "pytest"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    t.post_install(tmp_path)
    ci_path = tmp_path / ".github" / "workflows" / "ci.yml"
    content = ci_path.read_text(encoding="utf-8")
    assert "uv run ruff check ." in content
    assert "uv run pytest" in content


def test_cli_post_install_github_actions_without_ruff_step(tmp_path):
    t = CLITemplate(framework="typer", extras=["github-actions", "pytest"])
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    t.post_install(tmp_path)
    ci_path = tmp_path / ".github" / "workflows" / "ci.yml"
    content = ci_path.read_text(encoding="utf-8")
    assert "uv run ruff check ." not in content
    assert "uv run pytest" in content
