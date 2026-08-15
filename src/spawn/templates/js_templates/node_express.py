from pathlib import Path
from .base import BaseTemplate


class NodeExpressTemplate(BaseTemplate):
    name = "Node.js / Express API"
    language = "js"

    def get_dirs(self) -> list[str]:
        return ["src", "src/routes", "src/middleware", "src/controllers", "tests"]

    def get_files(self) -> dict[str, str]:
        return {
            "README.md": f"# {self.project_name}\n\nA Node.js Express API project.\n",
            ".gitignore": "node_modules/\ndist/\n.env\n*.log\n",
            ".env.example": "PORT=3000\nNODE_ENV=development\n",
            "src/index.js": (
                'const express = require("express");\n\n'
                "const app = express();\n"
                "const PORT = process.env.PORT || 3000;\n\n"
                "app.use(express.json());\n\n"
                'app.get("/", (req, res) => {\n'
                '  res.json({ message: "Hello from {}!" });\n'.format(self.project_name)
                + "});\n\n"
                "app.listen(PORT, () => {\n"
                '  console.log(`Server running on http://localhost:${PORT}`);\n'
                "});\n\n"
                "module.exports = app;\n"
            ),
            "src/routes/index.js": (
                'const express = require("express");\n'
                "const router = express.Router();\n\n"
                '// Add your routes here\n\n'
                "module.exports = router;\n"
            ),
            "tests/app.test.js": (
                '// Add your tests here\n'
            ),
        }
