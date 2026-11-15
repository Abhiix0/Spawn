"""Regression tests for Issue 6: Django template defaults.

Covers:
- DATABASES has a valid SQLite default (not empty)
- conftest.py is generated with DJANGO_SETTINGS_MODULE
- manage.py is executable on Unix
- pytest-django is included when pytest extra is selected
- Django pytest.ini_options sets DJANGO_SETTINGS_MODULE (not FastAPI warnings)
- Non-Django templates are not affected by django-specific extras
"""

import stat
import sys
import pytest
from spawn.templates.backend_api.content import (
    DJANGO_SETTINGS_CONTENT,
    DJANGO_CONFTEST_CONTENT,
)
from spawn.templates.backend_api import BackendAPITemplate, DJANGO_FILES


# ---------------------------------------------------------------------------
# settings.py DATABASES
# ---------------------------------------------------------------------------


def test_django_settings_has_sqlite_database():
    """DATABASES must not be empty; SQLite is the correct default."""
    assert "DATABASES = {}" not in DJANGO_SETTINGS_CONTENT
    assert "sqlite3" in DJANGO_SETTINGS_CONTENT
    assert (
        '"default"' in DJANGO_SETTINGS_CONTENT or "'default'" in DJANGO_SETTINGS_CONTENT
    )


def test_django_databases_references_base_dir():
    """SQLite path should use BASE_DIR for portability."""
    assert "BASE_DIR" in DJANGO_SETTINGS_CONTENT


# ---------------------------------------------------------------------------
# conftest.py
# ---------------------------------------------------------------------------


def test_django_conftest_content_exists():
    assert DJANGO_CONFTEST_CONTENT.strip() != ""


def test_django_conftest_sets_settings_module():
    assert "DJANGO_SETTINGS_MODULE" in DJANGO_CONFTEST_CONTENT
    assert "config.settings" in DJANGO_CONFTEST_CONTENT


def test_django_conftest_calls_django_setup():
    assert "django.setup()" in DJANGO_CONFTEST_CONTENT


def test_django_files_include_conftest():
    paths = [p for p, _ in DJANGO_FILES]
    assert "conftest.py" in paths


# ---------------------------------------------------------------------------
# pytest-django dependency
# ---------------------------------------------------------------------------


def test_django_with_pytest_extra_includes_pytest_django():
    t = BackendAPITemplate(framework="django", extras=["pytest"])
    deps = t.get_dependencies()
    assert "pytest-django" in deps


def test_django_without_pytest_extra_excludes_pytest_django():
    t = BackendAPITemplate(framework="django", extras=[])
    deps = t.get_dependencies()
    assert "pytest-django" not in deps


def test_fastapi_with_pytest_extra_does_not_include_pytest_django():
    """pytest-django must not bleed into the FastAPI template."""
    t = BackendAPITemplate(framework="fastapi", extras=["pytest"])
    deps = t.get_dependencies()
    assert "pytest-django" not in deps


def test_flask_with_pytest_extra_does_not_include_pytest_django():
    t = BackendAPITemplate(framework="flask", extras=["pytest"])
    deps = t.get_dependencies()
    assert "pytest-django" not in deps


# ---------------------------------------------------------------------------
# pytest.ini_options differs between Django and other frameworks
# ---------------------------------------------------------------------------


def test_django_pytest_ini_options_sets_settings_module(tmp_path):
    t = BackendAPITemplate(framework="django", extras=["pytest"])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")
    (tmp_path / "manage.py").write_text("", encoding="utf-8")
    t.post_install(tmp_path)
    content = pyproject.read_text(encoding="utf-8")
    assert "DJANGO_SETTINGS_MODULE" in content
    assert "config.settings" in content


def test_django_pytest_ini_options_does_not_add_starlette_warnings(tmp_path):
    t = BackendAPITemplate(framework="django", extras=["pytest"])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")
    (tmp_path / "manage.py").write_text("", encoding="utf-8")
    t.post_install(tmp_path)
    content = pyproject.read_text(encoding="utf-8")
    assert "starlette" not in content


def test_fastapi_pytest_ini_options_does_not_set_django_settings(tmp_path):
    t = BackendAPITemplate(framework="fastapi", extras=["pytest"])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")
    t.post_install(tmp_path)
    content = pyproject.read_text(encoding="utf-8")
    assert "DJANGO_SETTINGS_MODULE" not in content


# ---------------------------------------------------------------------------
# manage.py executable bit (Unix only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="chmod not applicable on Windows")
def test_django_manage_py_is_executable(tmp_path):
    t = BackendAPITemplate(framework="django", extras=[])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")
    manage = tmp_path / "manage.py"
    manage.write_text("#!/usr/bin/env python\n", encoding="utf-8")
    t.post_install(tmp_path)
    mode = manage.stat().st_mode
    assert mode & stat.S_IXUSR, "manage.py is not user-executable after post_install"


def test_non_django_post_install_does_not_chmod(tmp_path):
    """FastAPI post_install must not touch execute bits on any file."""
    t = BackendAPITemplate(framework="fastapi", extras=[])
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "demo"\n', encoding="utf-8")
    # No manage.py — if the code tried to chmod it, it would blow up
    t.post_install(tmp_path)  # must not raise
