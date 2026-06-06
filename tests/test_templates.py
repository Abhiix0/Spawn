import pytest

from spawn.core.exceptions import SpawnError

def test_fastapi_template():
    template = FastAPITemplate()

    assert "app" in template.folders
    assert "tests" in template.folders