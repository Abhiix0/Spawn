from spawn.core.registry import get_template, get_metadata, list_templates


def test_python_template_exists():
    template = get_template("python")

    assert template is not None
    assert template.name == "Python Script"

def test_invalid_template_returns_none():
    assert get_template("banana") is None


def test_backend_api_template_is_registered():
    from spawn.templates.backend_api import BackendAPITemplate
    template = get_template("backend-api")
    assert template is not None
    assert isinstance(template, BackendAPITemplate)


def test_data_science_template_exists():
    template = get_template("data-science")
    assert template is not None
    assert template.name == "Data Science"


def test_ml_template_exists():
    template = get_template("ml")
    assert template is not None
    assert template.name == "ML Project"


def test_list_templates_returns_all():
    templates = list_templates()

    slugs = [t.slug for t in templates]

    assert "python" in slugs
    assert "backend-api" in slugs
    assert "data-science" in slugs
    assert "ml" in slugs


def test_get_metadata_returns_metadata():
    meta = get_metadata("python")

    assert meta is not None
    assert meta.display_name == "Python Script"
    assert meta.slug == "python"


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
