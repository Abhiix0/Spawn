from spawn.templates.base import BaseTemplate
from spawn.templates.ml_project.content import ML_MAIN_CONTENT


class MLProjectTemplate(BaseTemplate):
    def __init__(self):
        super().__init__(
            name="ML Project",
            folders=[
                "data",
                "models",
                "src",
                "docs",
                "tests",
            ],
            starter_files=[
                ("main.py", ML_MAIN_CONTENT),
            ],
        )
