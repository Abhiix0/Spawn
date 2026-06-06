from spawn.templates.fastapi import FastAPITemplate


def test_fastapi_template():
    template = FastAPITemplate()

    assert "app" in template.folders
    assert "tests" in template.folders