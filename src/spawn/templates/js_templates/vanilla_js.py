from pathlib import Path
from .base import BaseTemplate


class VanillaJSTemplate(BaseTemplate):
    name = "Vanilla JS"
    language = "js"

    def get_dirs(self) -> list[str]:
        return ["src", "tests", "assets"]

    def get_files(self) -> dict[str, str]:
        return {
            "README.md": f"# {self.project_name}\n\nA vanilla JavaScript project.\n",
            ".gitignore": "node_modules/\ndist/\n.env\n*.log\n",
            "src/index.js": '// Entry point\nconsole.log("Hello from {}");\n'.format(
                self.project_name
            ),
            "index.html": (
                "<!DOCTYPE html>\n"
                '<html lang="en">\n'
                "<head>\n"
                '  <meta charset="UTF-8" />\n'
                '  <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
                f"  <title>{self.project_name}</title>\n"
                "</head>\n"
                "<body>\n"
                f"  <h1>{self.project_name}</h1>\n"
                '  <script type="module" src="src/index.js"></script>\n'
                "</body>\n"
                "</html>\n"
            ),
            "src/style.css": (
                "* {\n"
                "  margin: 0;\n"
                "  padding: 0;\n"
                "  box-sizing: border-box;\n"
                "}\n\n"
                "body {\n"
                "  font-family: sans-serif;\n"
                "  padding: 2rem;\n"
                "}\n"
            ),
        }
