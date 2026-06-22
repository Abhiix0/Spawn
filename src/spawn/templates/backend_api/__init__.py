from spawn.templates.base import BaseTemplate
from spawn.templates.backend_api.content import (
    MAIN_CONTENT,
    HEALTH_ROUTER_CONTENT,
    CONFIG_CONTENT,
    TEST_HEALTH_CONTENT,
    ENV_EXAMPLE_CONTENT,
    BACKEND_API_README_CONTENT,
    INIT_CONTENT,
)


class BackendAPITemplate(BaseTemplate):
    def __init__(self, framework: str | None = None):
        self.framework = framework
        super().__init__(
            name="Backend API",
            folders=[
                "app/api/routes",
                "app/core",
                "app/models",
                "app/schemas",
                "app/services",
                "tests",
            ],
            starter_files=[
                ("app/__init__.py", INIT_CONTENT),
                ("app/api/__init__.py", INIT_CONTENT),
                ("app/api/routes/__init__.py", INIT_CONTENT),
                ("app/api/routes/health.py", HEALTH_ROUTER_CONTENT),
                ("app/main.py", MAIN_CONTENT),
                ("app/core/__init__.py", INIT_CONTENT),
                ("app/core/config.py", CONFIG_CONTENT),
                ("tests/__init__.py", INIT_CONTENT),
                ("tests/test_health.py", TEST_HEALTH_CONTENT),
                (".env.example", ENV_EXAMPLE_CONTENT),
            ],
        )

    def get_readme_content(self, context: dict) -> str | None:
        return BACKEND_API_README_CONTENT.format_map(context)
