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
pytest
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
