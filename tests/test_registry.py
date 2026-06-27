from spawn.core.registry import get_template, get_metadata, list_templates


def test_invalid_template_returns_none():
    assert get_template("banana") is None


def test_backend_api_template_is_registered():
    from spawn.templates.backend_api import BackendAPITemplate
    template = get_template("backend-api")
    assert template is not None
    assert isinstance(template, BackendAPITemplate)


def test_removed_slugs_return_none():
    assert get_template("python") is None
    assert get_template("data-science") is None
    assert get_template("ml") is None


def test_list_templates_returns_all():
    templates = list_templates()
    slugs = [t.slug for t in templates]
    assert "backend-api" in slugs
    assert "cli" in slugs
    assert "automation" in slugs
    assert len(slugs) == 3


def test_get_metadata_returns_none_for_unknown():
    assert get_metadata("banana") is None


def test_backend_api_in_list_templates():
    templates = list_templates()
    slugs = [t.slug for t in templates]
    assert "backend-api" in slugs


def test_backend_api_metadata():
    from spawn.core.registry import get_metadata
    meta = get_metadata("backend-api")
    assert meta is not None
    assert meta.slug == "backend-api"
    assert meta.display_name == "Backend API"
    assert "fastapi" in meta.available_frameworks
    assert "ruff" in meta.available_extras
    assert "pytest" in meta.available_extras


def test_backend_api_template_exists():
    from spawn.templates.backend_api import BackendAPITemplate
    template = get_template("backend-api")
    assert template is not None
    assert isinstance(template, BackendAPITemplate)
    assert template.name == "Backend API"


def test_backend_api_frameworks_include_flask_and_django():
    from spawn.core.registry import get_metadata
    meta = get_metadata("backend-api")
    assert "flask" in meta.available_frameworks
    assert "django" in meta.available_frameworks


def test_backend_api_extras_include_docker_and_github_actions():
    from spawn.core.registry import get_metadata
    meta = get_metadata("backend-api")
    assert "docker" in meta.available_extras
    assert "github-actions" in meta.available_extras


def test_cli_template_is_registered():
    from spawn.templates.cli_application import CLITemplate

    template = get_template("cli")
    assert template is not None
    assert isinstance(template, CLITemplate)


def test_cli_metadata():
    meta = get_metadata("cli")
    assert meta is not None
    assert meta.slug == "cli"
    assert meta.display_name == "CLI Application"
    assert "typer" in meta.available_frameworks
    assert "click" in meta.available_frameworks
    assert "argparse" in meta.available_frameworks
    assert "ruff" in meta.available_extras
    assert "pytest" in meta.available_extras
    assert "utility" in meta.available_cli_types
    assert "interactive" in meta.available_cli_types


def test_cli_in_list_templates():
    slugs = [m.slug for m in list_templates()]
    assert "cli" in slugs
