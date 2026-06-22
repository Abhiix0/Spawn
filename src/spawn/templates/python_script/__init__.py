from spawn.templates.base import BaseTemplate
from spawn.templates.python_script.content import PYTHON_MAIN_CONTENT


class PythonScriptTemplate(BaseTemplate):
    def __init__(self):
        super().__init__(
            name="Python Script",
            folders=[
                "src",
                "tests",
            ],
            starter_files=[
                ("main.py", PYTHON_MAIN_CONTENT),
            ],
        )
