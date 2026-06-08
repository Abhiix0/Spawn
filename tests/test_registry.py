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