# ── tests/test_js_templates.py ─────────────────────────────────────────────────
# Tests for the four JavaScript project templates and the npm-init helper.
# Run with:  uv run pytest tests/test_js_templates.py -v
# ───────────────────────────────────────────────────────────────────────────────

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spawn.templates.js_templates import (
    VanillaJSTemplate,
    NodeExpressTemplate,
    ReactAppTemplate,
    NextJSAppTemplate,
)
from spawn.core.js_init import run_npm_init
from spawn.core.registry import TEMPLATES
from spawn.utils.next_steps import get_next_steps


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    return tmp_path


# ── Registry ───────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_js_templates_registered(self):
        assert 9  in TEMPLATES, "VanillaJS must be registered"
        assert 10 in TEMPLATES, "NodeExpress must be registered"
        assert 11 in TEMPLATES, "ReactApp must be registered"
        assert 12 in TEMPLATES, "NextJS must be registered"

    def test_js_template_classes(self):
        assert TEMPLATES[9]  is VanillaJSTemplate
        assert TEMPLATES[10] is NodeExpressTemplate
        assert TEMPLATES[11] is ReactAppTemplate
        assert TEMPLATES[12] is NextJSAppTemplate

    def test_total_template_count(self):
        # 8 Python + 4 JS = 12
        assert len(TEMPLATES) == 12


# ── VanillaJS ──────────────────────────────────────────────────────────────────

class TestVanillaJSTemplate:
    def _make(self) -> VanillaJSTemplate:
        return VanillaJSTemplate()

    def test_name(self):
        assert self._make().name == "Vanilla JS"

    def test_language(self):
        assert self._make().language == "js"

    def test_folders_include_src_and_assets(self):
        t = self._make()
        assert "src" in t.folders
        assert "assets" in t.folders
        assert "tests" in t.folders

    def test_starter_files_include_index_html(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert "index.html" in paths

    def test_starter_files_include_entry_point(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert "src/index.js" in paths

    def test_starter_files_include_gitignore(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert ".gitignore" in paths

    def test_gitignore_contains_node_modules(self):
        t = self._make()
        gitignore = next(c for p, c in t.starter_files if p == ".gitignore")
        assert "node_modules/" in gitignore

    def test_readme_contains_project_name(self):
        t = self._make()
        readme = t.get_readme_content({"project_name": "cool-site"})
        assert "cool-site" in readme

    def test_next_steps_exist(self):
        assert len(self._make().next_steps) > 0


# ── NodeExpress ────────────────────────────────────────────────────────────────

class TestNodeExpressTemplate:
    def _make(self) -> NodeExpressTemplate:
        return NodeExpressTemplate()

    def test_name(self):
        assert self._make().name == "Node.js / Express API"

    def test_language(self):
        assert self._make().language == "js"

    def test_folders_include_routes_and_controllers(self):
        t = self._make()
        assert "src/routes" in t.folders
        assert "src/controllers" in t.folders
        assert "src/middleware" in t.folders

    def test_entry_point_uses_express(self):
        t = self._make()
        src = next(c for p, c in t.starter_files if p == "src/index.js")
        assert "express" in src

    def test_env_example_present(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert ".env.example" in paths

    def test_readme_contains_project_name(self):
        t = self._make()
        readme = t.get_readme_content({"project_name": "payments-api"})
        assert "payments-api" in readme

    def test_next_steps_mention_npm(self):
        t = self._make()
        combined = " ".join(t.next_steps)
        assert "npm" in combined


# ── ReactApp ───────────────────────────────────────────────────────────────────

class TestReactAppTemplate:
    def _make(self) -> ReactAppTemplate:
        return ReactAppTemplate()

    def test_name(self):
        assert self._make().name == "React"

    def test_language(self):
        assert self._make().language == "js"

    def test_folders_include_components_and_hooks(self):
        t = self._make()
        assert "src/components" in t.folders
        assert "src/hooks" in t.folders

    def test_main_jsx_present(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert "src/main.jsx" in paths

    def test_app_jsx_present(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert "src/App.jsx" in paths

    def test_vite_config_present(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert "vite.config.js" in paths

    def test_readme_contains_project_name(self):
        t = self._make()
        readme = t.get_readme_content({"project_name": "dashboard"})
        assert "dashboard" in readme

    def test_next_steps_mention_vite(self):
        t = self._make()
        combined = " ".join(t.next_steps).lower()
        assert "vite" in combined


# ── NextJS ─────────────────────────────────────────────────────────────────────

class TestNextJSAppTemplate:
    def _make(self) -> NextJSAppTemplate:
        return NextJSAppTemplate()

    def test_name(self):
        assert self._make().name == "Next.js"

    def test_language(self):
        assert self._make().language == "js"

    def test_folders_include_app_and_components(self):
        t = self._make()
        assert "app" in t.folders
        assert "components" in t.folders
        assert "app/api" in t.folders

    def test_layout_jsx_present(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert "app/layout.jsx" in paths

    def test_page_jsx_present(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert "app/page.jsx" in paths

    def test_api_route_present(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert "app/api/hello/route.js" in paths

    def test_next_config_present(self):
        t = self._make()
        paths = [f[0] for f in t.starter_files]
        assert "next.config.js" in paths

    def test_readme_contains_project_name(self):
        t = self._make()
        readme = t.get_readme_content({"project_name": "storefront"})
        assert "storefront" in readme

    def test_next_steps_mention_npm_run_dev(self):
        t = self._make()
        combined = " ".join(t.next_steps)
        assert "npm run dev" in combined


# ── npm init helper ────────────────────────────────────────────────────────────

class TestRunNpmInit:
    def test_returns_false_when_node_missing(self, tmp_project: Path):
        with patch("spawn.core.js_init.shutil.which", return_value=None):
            result = run_npm_init(tmp_project)
        assert result is False

    def test_returns_false_when_npm_missing(self, tmp_project: Path):
        def which_side_effect(cmd):
            return "/usr/bin/node" if cmd == "node" else None

        with patch("spawn.core.js_init.shutil.which", side_effect=which_side_effect):
            result = run_npm_init(tmp_project)
        assert result is False

    def test_returns_true_on_success(self, tmp_project: Path):
        with (
            patch("spawn.core.js_init.shutil.which", return_value="/usr/bin/npm"),
            patch(
                "spawn.core.js_init.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
        ):
            result = run_npm_init(tmp_project)
        assert result is True

    def test_returns_false_on_subprocess_error(self, tmp_project: Path):
        with (
            patch("spawn.core.js_init.shutil.which", return_value="/usr/bin/npm"),
            patch(
                "spawn.core.js_init.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "npm", stderr=b"fail"),
            ),
        ):
            result = run_npm_init(tmp_project)
        assert result is False

    def test_npm_init_called_with_correct_args(self, tmp_project: Path):
        mock_run = MagicMock(return_value=MagicMock(returncode=0))
        with (
            patch("spawn.core.js_init.shutil.which", return_value="/usr/bin/npm"),
            patch("spawn.core.js_init.subprocess.run", mock_run),
        ):
            run_npm_init(tmp_project)

        mock_run.assert_called_once_with(
            ["npm", "init", "-y"],
            cwd=tmp_project,
            check=True,
            capture_output=True,
        )


# ── Next steps ─────────────────────────────────────────────────────────────────

class TestJSNextSteps:
    def test_vanilla_next_steps_exist(self):
        steps = get_next_steps(9, "my-project")
        assert len(steps) > 0

    def test_express_steps_mention_npm(self):
        steps = get_next_steps(10, "api")
        assert any("npm" in s for s in steps)

    def test_react_steps_mention_vite(self):
        steps = get_next_steps(11, "ui")
        assert any("vite" in s.lower() for s in steps)

    def test_nextjs_steps_mention_npm_run_dev(self):
        steps = get_next_steps(12, "web")
        assert any("npm run dev" in s for s in steps)

    def test_project_name_interpolated(self):
        steps = get_next_steps(9, "hello-world")
        assert any("hello-world" in s for s in steps)
