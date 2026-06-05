from spawn.templates.base import BaseTemplate


class DataScienceTemplate(BaseTemplate):
    def __init__(self):
        super().__init__(
            name="Data Science",
            folders=[
                "data",
                "notebooks",
                "src",
                "docs",
                "tests",
            ],
        )