from spawn.templates.base import BaseTemplate


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
        )