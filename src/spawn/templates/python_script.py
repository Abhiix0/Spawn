from spawn.templates.base import BaseTemplate


class PythonScriptTemplate(BaseTemplate):
    def __init__(self):
        super().__init__(
            name="Python Script",
            folders=[
                "src",
                "tests",
            ],
        )