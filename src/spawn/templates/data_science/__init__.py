from spawn.templates.base import BaseTemplate
from spawn.templates.data_science.content import DATA_SCIENCE_MAIN_CONTENT


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
            next_steps=[
                "cd {project_name}",
                "uv add pandas numpy matplotlib",
                "uv run python main.py",
            ],
        )
