"""Regression tests for Issue 4: Backend Dockerfile correctness.

Verifies that every generated Dockerfile:
- Copies uv.lock before running uv sync (layer-cache correctness)
- Uses --frozen so builds are reproducible
- Uses --no-dev so dev tools are excluded from the image
- Sets PATH to include the venv bin directory
"""

import pytest
from spawn.templates.backend_api.content import (
    DOCKERFILE_FASTAPI_CONTENT,
    DOCKERFILE_FLASK_CONTENT,
    DOCKERFILE_DJANGO_CONTENT,
)


@pytest.mark.parametrize(
    "content,label",
    [
        (DOCKERFILE_FASTAPI_CONTENT, "fastapi"),
        (DOCKERFILE_FLASK_CONTENT, "flask"),
        (DOCKERFILE_DJANGO_CONTENT, "django"),
    ],
)
def test_dockerfile_copies_lockfile(content, label):
    """uv.lock must be copied before uv sync so the lock is honoured."""
    assert "uv.lock" in content, f"{label} Dockerfile does not copy uv.lock"
    copy_line = next(
        (line for line in content.splitlines() if "COPY" in line and "uv.lock" in line),
        None,
    )
    assert copy_line is not None, f"{label} Dockerfile has no COPY line for uv.lock"
    # The COPY of pyproject.toml/uv.lock must precede the RUN uv sync line.
    copy_idx = content.index(copy_line)
    run_sync_idx = content.index("uv sync")
    assert copy_idx < run_sync_idx, f"{label} Dockerfile copies lockfile after uv sync"


@pytest.mark.parametrize(
    "content,label",
    [
        (DOCKERFILE_FASTAPI_CONTENT, "fastapi"),
        (DOCKERFILE_FLASK_CONTENT, "flask"),
        (DOCKERFILE_DJANGO_CONTENT, "django"),
    ],
)
def test_dockerfile_uses_frozen(content, label):
    """uv sync must use --frozen for reproducible builds."""
    assert "--frozen" in content, f"{label} Dockerfile does not use --frozen"


@pytest.mark.parametrize(
    "content,label",
    [
        (DOCKERFILE_FASTAPI_CONTENT, "fastapi"),
        (DOCKERFILE_FLASK_CONTENT, "flask"),
        (DOCKERFILE_DJANGO_CONTENT, "django"),
    ],
)
def test_dockerfile_excludes_dev_deps(content, label):
    """uv sync must use --no-dev so dev tools are not installed in the image."""
    assert "--no-dev" in content, f"{label} Dockerfile does not use --no-dev"


@pytest.mark.parametrize(
    "content,label",
    [
        (DOCKERFILE_FASTAPI_CONTENT, "fastapi"),
        (DOCKERFILE_FLASK_CONTENT, "flask"),
        (DOCKERFILE_DJANGO_CONTENT, "django"),
    ],
)
def test_dockerfile_sets_venv_on_path(content, label):
    """The venv bin directory must be on PATH so CMD binaries resolve."""
    assert ".venv/bin" in content, f"{label} Dockerfile does not add .venv/bin to PATH"
    assert "ENV PATH" in content or 'ENV PATH="' in content or "ENV PATH=" in content, (
        f"{label} Dockerfile does not set PATH via ENV directive"
    )


def test_fastapi_dockerfile_cmd_uses_uvicorn():
    assert "uvicorn" in DOCKERFILE_FASTAPI_CONTENT


def test_flask_dockerfile_cmd_uses_python_run():
    assert "run.py" in DOCKERFILE_FLASK_CONTENT


def test_django_dockerfile_cmd_uses_manage():
    assert "manage.py" in DOCKERFILE_DJANGO_CONTENT


def test_backend_api_template_generates_dockerfile(tmp_path):
    """BackendAPITemplate.post_install writes a Dockerfile when docker extra requested."""
    from spawn.templates.backend_api import BackendAPITemplate

    t = BackendAPITemplate(framework="fastapi", extras=["docker"])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")
    t.post_install(tmp_path)

    dockerfile = tmp_path / "Dockerfile"
    assert dockerfile.exists()
    content = dockerfile.read_text(encoding="utf-8")
    assert "--frozen" in content
    assert "--no-dev" in content
    assert ".venv/bin" in content
    assert "uv.lock" in content


def test_flask_template_generates_correct_dockerfile(tmp_path):
    from spawn.templates.backend_api import BackendAPITemplate

    t = BackendAPITemplate(framework="flask", extras=["docker"])
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")
    t.post_install(tmp_path)
    content = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    assert "run.py" in content
    assert "--frozen" in content


def test_django_template_generates_correct_dockerfile(tmp_path):
    from spawn.templates.backend_api import BackendAPITemplate

    t = BackendAPITemplate(framework="django", extras=["docker"])
    (tmp_path / "pyproject.toml").write_text('[project]\nname="x"\n', encoding="utf-8")
    t.post_install(tmp_path)
    content = (tmp_path / "Dockerfile").read_text(encoding="utf-8")
    assert "manage.py" in content
    assert "--frozen" in content
