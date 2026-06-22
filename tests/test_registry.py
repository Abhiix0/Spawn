from spawn.core.registry import get_template


def test_python_template_exists():
    template = get_template("python")

    assert template is not None
    assert template.name == "Python Script"

def test_invalid_template_returns_none():
    assert get_template("banana") is None


def test_fastapi_template_exists():
    template = get_template("fastapi")
    assert template is not None
    assert template.name == "FastAPI"


def test_data_science_template_exists():
    template = get_template("data-science")
    assert template is not None
    assert template.name == "Data Science"


def test_ml_template_exists():
    template = get_template("ml")
    assert template is not None
    assert template.name == "ML Project"


from spawn.core.registry import get_metadata, list_templates


def test_list_templates_returns_all():
    templates = list_templates()

    slugs = [t.slug for t in templates]

    assert "python" in slugs
    assert "fastapi" in slugs
    assert "data-science" in slugs
    assert "ml" in slugs


def test_get_metadata_returns_metadata():
    meta = get_metadata("python")

    assert meta is not None
    assert meta.display_name == "Python Script"
    assert meta.slug == "python"


def test_get_metadata_returns_none_for_unknown():
    assert get_metadata("banana") is None
