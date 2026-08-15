import shutil
import subprocess
from pathlib import Path

from spawn.templates.base import BaseTemplate
from spawn.utils.console import console
from spawn.templates.web_js.content import (
    # Vanilla
    VANILLA_INDEX_HTML,
    VANILLA_STYLE_CSS,
    VANILLA_SCRIPT_JS,
    VANILLA_PACKAGE_JSON,
    VANILLA_README_CONTENT,
    # Express
    EXPRESS_SERVER_JS,
    EXPRESS_HEALTH_ROUTE_JS,
    EXPRESS_PACKAGE_JSON,
    EXPRESS_ENV_EXAMPLE,
    EXPRESS_README_CONTENT,
    # React
    REACT_INDEX_HTML,
    REACT_MAIN_JSX,
    REACT_APP_JSX,
    REACT_APP_CSS,
    REACT_VITE_CONFIG,
    REACT_PACKAGE_JSON,
    REACT_README_CONTENT,
    # Next.js
    NEXTJS_LAYOUT_JS,
    NEXTJS_PAGE_JS,
    NEXTJS_GLOBALS_CSS,
    NEXTJS_CONFIG_JS,
    NEXTJS_PACKAGE_JSON,
    NEXTJS_README_CONTENT,
    # Extras
    ESLINTRC_CONTENT,
    PRETTIERRC_CONTENT,
    GITHUB_ACTIONS_CI_NODE,
)

# ---------------------------------------------------------------------------
# Framework definitions
# ---------------------------------------------------------------------------

VANILLA_FOLDERS: list[str] = []

VANILLA_FILES = [
    ("index.html", VANILLA_INDEX_HTML),
    ("style.css", VANILLA_STYLE_CSS),
    ("script.js", VANILLA_SCRIPT_JS),
    ("package.json", VANILLA_PACKAGE_JSON),
]

EXPRESS_FOLDERS = ["routes"]

EXPRESS_FILES = [
    ("server.js", EXPRESS_SERVER_JS),
    ("routes/health.js", EXPRESS_HEALTH_ROUTE_JS),
    ("package.json", EXPRESS_PACKAGE_JSON),
    (".env.example", EXPRESS_ENV_EXAMPLE),
]

REACT_FOLDERS = ["src"]

REACT_FILES = [
    ("index.html", REACT_INDEX_HTML),
    ("src/main.jsx", REACT_MAIN_JSX),
    ("src/App.jsx", REACT_APP_JSX),
    ("src/App.css", REACT_APP_CSS),
    ("vite.config.js", REACT_VITE_CONFIG),
    ("package.json", REACT_PACKAGE_JSON),
]

NEXTJS_FOLDERS = ["app"]

NEXTJS_FILES = [
    ("app/layout.js", NEXTJS_LAYOUT_JS),
    ("app/page.js", NEXTJS_PAGE_JS),
    ("app/globals.css", NEXTJS_GLOBALS_CSS),
    ("next.config.js", NEXTJS_CONFIG_JS),
    ("package.json", NEXTJS_PACKAGE_JSON),
]


class WebJSTemplate(BaseTemplate):
    """
    JavaScript/Node project template. Mirrors BackendAPITemplate's shape:
    `framework` selects vanilla/express/react/nextjs, `extras` toggles
    eslint/prettier/github-actions. Unlike the Python templates, this one
    has no uv/pip dependencies -- npm packages live in the generated
    package.json and are installed via `npm install` in post_install().
    """

    def __init__(
        self,
        framework: str | None = None,
        extras: list[str] | None = None,
    ):
        self.framework = framework
        self.extras = extras or []

        if framework == "express":
            folders = EXPRESS_FOLDERS
            files = EXPRESS_FILES
        elif framework == "react":
            folders = REACT_FOLDERS
            files = REACT_FILES
        elif framework == "nextjs":
            folders = NEXTJS_FOLDERS
            files = NEXTJS_FILES
        else:
            # Default to vanilla for None or "vanilla"
            folders = VANILLA_FOLDERS
            files = VANILLA_FILES

        super().__init__(
            name="Web (JavaScript)",
            folders=folders,
            starter_files=files,
        )

        if framework == "express":
            self.next_steps = [
                "cd {project_name}",
                "npm install",
                "npm run dev",
            ]
        elif framework == "react":
            self.next_steps = [
                "cd {project_name}",
                "npm install",
                "npm run dev",
            ]
        elif framework == "nextjs":
            self.next_steps = [
                "cd {project_name}",
                "npm install",
                "npm run dev",
            ]
        else:
            self.next_steps = [
                "cd {project_name}",
                "npm install",
                "npm start",
            ]

    def get_readme_content(self, context: dict) -> str | None:
        if self.framework == "express":
            return EXPRESS_README_CONTENT.format_map(context)
        if self.framework == "react":
            return REACT_README_CONTENT.format_map(context)
        if self.framework == "nextjs":
            return NEXTJS_README_CONTENT.format_map(context)
        return VANILLA_README_CONTENT.format_map(context)

    def get_dependencies(self) -> list[str]:
        # No uv/pip dependencies for JS templates -- npm packages are
        # declared directly in the generated package.json instead.
        return []

    def post_install(self, project_path: Path) -> None:
        if "eslint" in self.extras:
            (project_path / ".eslintrc.json").write_text(
                ESLINTRC_CONTENT, encoding="utf-8"
            )

        if "prettier" in self.extras:
            (project_path / ".prettierrc").write_text(
                PRETTIERRC_CONTENT, encoding="utf-8"
            )

        if "github-actions" in self.extras:
            workflows_path = project_path / ".github" / "workflows"
            workflows_path.mkdir(parents=True, exist_ok=True)
            (workflows_path / "ci.yml").write_text(
                GITHUB_ACTIONS_CI_NODE, encoding="utf-8"
            )

        node_ok = shutil.which("node")
        npm_ok = shutil.which("npm")

        if not (node_ok and npm_ok):
            console.print(
                "[yellow]node/npm not found on PATH -- skipping `npm install`. "
                "Install Node.js from nodejs.org, then run `npm install` "
                "inside the project yourself.[/yellow]"
            )
            return

        console.print("[dim]Running npm install...[/dim]")
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=project_path,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            console.print(
                "[yellow]`npm install` failed -- run it manually inside "
                f"the project.\n{e.stderr}[/yellow]"
            )
