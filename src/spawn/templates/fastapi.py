from spawn.templates.base import BaseTemplate


class FastAPITemplate(BaseTemplate):
    def __init__(self):
        super().__init__(
            name="FastAPI",
            folders=[
                "app",
                "src",
                "tests",
                "docs",
            ],
        )