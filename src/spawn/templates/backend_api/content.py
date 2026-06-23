MAIN_CONTENT = """\
from fastapi import FastAPI

from app.core.config import settings
from app.api.routes.health import router as health_router

app = FastAPI(title=settings.APP_NAME)

app.include_router(health_router)
"""

HEALTH_ROUTER_CONTENT = """\
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def health_check():
    return {{"status": "running"}}
"""

CONFIG_CONTENT = """\
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    APP_NAME: str = "{project_name}"
    DEBUG: bool = False


settings = Settings()
"""

TEST_HEALTH_CONTENT = """\
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {{"status": "running"}}
"""

ENV_EXAMPLE_CONTENT = """\
APP_NAME={project_name}
DEBUG=True
"""

BACKEND_API_README_CONTENT = """\
# {project_name}

Generated with [Spawn](https://github.com/your-org/spawn).

## Getting Started

Install dependencies and start the development server:

```bash
uv run uvicorn app.main:app --reload
```

## Running Tests

```bash
uv run pytest
```

## Endpoints

| Method | Path | Description  |
|--------|------|--------------|
| GET    | /    | Health check |

## Project Structure

```
{project_name}/
├── app/
│   ├── api/
│   │   └── routes/
│   │       └── health.py   # Health check route
│   ├── core/
│   │   └── config.py       # App settings (pydantic-settings)
│   ├── models/             # SQLAlchemy / domain models
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/           # Business logic
│   └── main.py             # FastAPI app entry point
├── tests/
│   └── test_health.py
├── .env.example
└── README.md
```
"""

INIT_CONTENT = ""


# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------

FLASK_APP_INIT_CONTENT = """\
from flask import Flask
from app.config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    from app.routes.health import health_bp
    app.register_blueprint(health_bp)

    return app
"""

FLASK_CONFIG_CONTENT = """\
import os


class Config:
    APP_NAME: str = os.getenv("APP_NAME", "{project_name}")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
"""

FLASK_HEALTH_CONTENT = """\
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/")
def health_check():
    return jsonify({"status": "running"})
"""

FLASK_RUN_CONTENT = """\
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", True))
"""

FLASK_TEST_HEALTH_CONTENT = """\
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json() == {"status": "running"}
"""

FLASK_ENV_EXAMPLE_CONTENT = """\
APP_NAME={project_name}
DEBUG=True
"""

FLASK_README_CONTENT = """\
# {project_name}

Generated with [Spawn](https://github.com/Abhiix0/spawn).

## Getting Started

Install dependencies and start the development server:

```bash
uv run python run.py
```

## Running Tests

```bash
uv run pytest
```

## Endpoints

| Method | Path | Description  |
|--------|------|--------------|
| GET    | /    | Health check |

## Project Structure

```
{project_name}/
├── app/
│   ├── routes/
│   │   └── health.py   # Health check blueprint
│   ├── models/         # Domain models
│   ├── services/       # Business logic
│   ├── config.py       # App configuration
│   └── __init__.py     # App factory
├── run.py              # Entry point
├── tests/
│   └── test_health.py
├── .env.example
└── README.md
```
"""

# ---------------------------------------------------------------------------
# Django
# ---------------------------------------------------------------------------

DJANGO_MANAGE_CONTENT = """\
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
"""

DJANGO_SETTINGS_CONTENT = """\
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-change-me-in-production"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "apps.health",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
"""

DJANGO_URLS_CONTENT = """\
from django.urls import path, include

urlpatterns = [
    path("", include("apps.health.urls")),
]
"""

DJANGO_ASGI_CONTENT = """\
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
"""

DJANGO_WSGI_CONTENT = """\
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
"""

DJANGO_HEALTH_VIEWS_CONTENT = """\
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "running"})
"""

DJANGO_HEALTH_URLS_CONTENT = """\
from django.urls import path
from apps.health.views import health_check

urlpatterns = [
    path("", health_check, name="health_check"),
]
"""

DJANGO_HEALTH_TESTS_CONTENT = """\
from django.test import TestCase, Client


class HealthCheckTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "running"})
"""

DJANGO_README_CONTENT = """\
# {project_name}

Generated with [Spawn](https://github.com/Abhiix0/spawn).

## Getting Started

Install dependencies and start the development server:

```bash
uv run python manage.py runserver
```

## Running Tests

```bash
uv run python manage.py test
```

## Endpoints

| Method | Path | Description  |
|--------|------|--------------|
| GET    | /    | Health check |

## Project Structure

```
{project_name}/
├── manage.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   └── health/
│       ├── views.py
│       ├── urls.py
│       └── tests.py
└── README.md
```
"""

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

DOCKERFILE_FASTAPI_CONTENT = """\
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv && uv sync

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

DOCKERFILE_FLASK_CONTENT = """\
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv && uv sync

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
"""

DOCKERFILE_DJANGO_CONTENT = """\
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv && uv sync

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
"""

DOCKERIGNORE_CONTENT = """\
.venv
__pycache__
*.pyc
*.pyo
.env
.git
.gitignore
"""
