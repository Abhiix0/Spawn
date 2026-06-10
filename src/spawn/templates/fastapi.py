from spawn.templates.base import BaseTemplate
from spawn.templates.files import FASTAPI_MAIN_CONTENT


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
            starter_files=[
                ("app/main.py", FASTAPI_MAIN_CONTENT),
            ],
        )
