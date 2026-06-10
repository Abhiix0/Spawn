from spawn.templates.base import BaseTemplate
from spawn.templates.files import DATA_SCIENCE_MAIN_CONTENT


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
            starter_files=[
                ("main.py", DATA_SCIENCE_MAIN_CONTENT),
            ],
        )
