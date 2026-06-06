from spawn.core.registry import get_template


def test_python_template_exists():
    template = get_template("python")

    assert template is not None
    assert template.name == "Python Script"

def test_invalid_template_returns_none():
    assert get_template("banana") is None