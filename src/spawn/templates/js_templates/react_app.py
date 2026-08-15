from pathlib import Path
from .base import BaseTemplate


class ReactAppTemplate(BaseTemplate):
    name = "React"
    language = "js"

    def get_dirs(self) -> list[str]:
        return ["src", "src/components", "src/hooks", "src/assets", "public"]

    def get_files(self) -> dict[str, str]:
        return {
            "README.md": f"# {self.project_name}\n\nA React project bootstrapped with Vite.\n",
            ".gitignore": "node_modules/\ndist/\n.env\n*.log\n.DS_Store\n",
            "src/main.jsx": (
                'import React from "react";\n'
                'import ReactDOM from "react-dom/client";\n'
                'import App from "./App";\n'
                'import "./index.css";\n\n'
                'ReactDOM.createRoot(document.getElementById("root")).render(\n'
                "  <React.StrictMode>\n"
                "    <App />\n"
                "  </React.StrictMode>\n"
                ");\n"
            ),
            "src/App.jsx": (
                'import React from "react";\n\n'
                "function App() {\n"
                "  return (\n"
                "    <div>\n"
                f"      <h1>{self.project_name}</h1>\n"
                "    </div>\n"
                "  );\n"
                "}\n\n"
                "export default App;\n"
            ),
            "src/index.css": (
                "* {\n"
                "  margin: 0;\n"
                "  padding: 0;\n"
                "  box-sizing: border-box;\n"
                "}\n\n"
                "body {\n"
                "  font-family: sans-serif;\n"
                "}\n"
            ),
            "src/components/.gitkeep": "",
            "src/hooks/.gitkeep": "",
            "public/index.html": (
                "<!DOCTYPE html>\n"
                '<html lang="en">\n'
                "  <head>\n"
                '    <meta charset="UTF-8" />\n'
                '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
                f"    <title>{self.project_name}</title>\n"
                "  </head>\n"
                '  <body>\n    <div id="root"></div>\n  </body>\n'
                "</html>\n"
            ),
            "vite.config.js": (
                'import { defineConfig } from "vite";\n'
                'import react from "@vitejs/plugin-react";\n\n'
                "export default defineConfig({\n"
                "  plugins: [react()],\n"
                "});\n"
            ),
        }
