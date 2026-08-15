"""
Tests for the "web-js" template (WebJSTemplate).

Replaces the old tests/test_js_templates.py, which imported from the
deleted spawn.templates.js_templates module (VanillaJSTemplate, etc.)
and broke CI at collection time. This file tests the current
slug-keyed registry (TEMPLATES: dict[str, TemplateMetadata]) and the
WebJSTemplate class that lives at spawn.templates.web_js.
"""

import json
import subprocess
from pathlib import Path

import pytest

from spawn.core.registry import (
    TEMPLATES,
    get_metadata,
    get_template,
    instantiate_template,
)
from spawn.core.models import ProjectConfig
from spawn.templates.web_js import WebJSTemplate

FRAMEWORKS = ["vanilla", "express", "react", "nextjs"]


# ---------------------------------------------------------------------------
# Registry wiring
# ---------------------------------------------------------------------------

def test_web_js_registered():
    assert "web-js" in TEMPLATES


def test_web_js_metadata_shape():
    meta = get_metadata("web-js")
    assert meta is not None
    assert meta.slug == "web-js"
    assert meta.template_class is WebJSTemplate
    assert set(meta.available_frameworks) == set(FRAMEWORKS)
    assert "eslint" in meta.available_extras
    assert "prettier" in meta.available_extras
    assert "github-actions" in meta.available_extras


def test_get_template_returns_instance():
    instance = get_template("web-js")
    assert isinstance(instance, WebJSTemplate)


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_instantiate_template_forwards_framework_and_extras(framework):
    config = ProjectConfig(
        name="proj",
        template="web-js",
        use_git=True,
        generate_claude_md=False,
        framework=framework,
        extras=["eslint"],
    )
    instance = instantiate_template(config)
    assert isinstance(instance, WebJSTemplate)
    assert instance.framework == framework
    assert "eslint" in instance.extras


# ---------------------------------------------------------------------------
# generate() end-to-end for every framework
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_generate_creates_valid_project(tmp_path: Path, framework):
    """
    Mirrors the real spawn create call path: BaseTemplate.generate()
    mkdir's folders, then runs every starter_files entry through
    str.format_map(context). Any unescaped literal brace in a starter
    file (CSS, JSON, JSX, etc.) raises here, which is exactly the bug
    that slipped through last time (unescaped CSS { } broke the
    format_map call).
    """
    project_path = tmp_path / f"proj-{framework}"
    project_path.mkdir()
    context = {"project_name": project_path.name}

    template = WebJSTemplate(framework=framework, extras=[])
    template.generate(project_path, context)

    for folder in template.folders:
        assert (project_path / folder).is_dir()

    for relative_path, _ in template.starter_files:
        file_path = project_path / relative_path
        assert file_path.is_file(), f"missing {relative_path}"


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_generate_produces_valid_package_json(tmp_path: Path, framework):
    project_path = tmp_path / f"proj-{framework}"
    project_path.mkdir()
    context = {"project_name": project_path.name}

    template = WebJSTemplate(framework=framework, extras=[])
    template.generate(project_path, context)

    pkg = project_path / "package.json"
    assert pkg.is_file()
    data = json.loads(pkg.read_text(encoding="utf-8"))
    assert data.get("name")


def test_get_dependencies_is_empty():
    # JS deps live in package.json, not uv/pip; get_dependencies() must
    # stay a no-op so the generator's `uv add {deps}` step doesn't run
    # with an empty/garbage arg list.
    template = WebJSTemplate(framework="vanilla", extras=[])
    assert template.get_dependencies() == []


# ---------------------------------------------------------------------------
# post_install(): npm resolution on Windows (the WinError 2 regression)
# ---------------------------------------------------------------------------

def test_post_install_resolves_npm_cmd_on_windows(tmp_path, monkeypatch):
    """
    subprocess.run(["npm", ...], shell=False) cannot launch a bare
    "npm" name on Windows because the real executable is npm.cmd.
    post_install() must resolve the executable via shutil.which() and
    pass that resolved path to subprocess.run, not the literal string
    "npm".
    """
    calls = []

    def fake_which(name):
        if name == "npm":
            return r"C:\Program Files\nodejs\npm.cmd"
        if name == "node":
            return r"C:\Program Files\nodejs\node.exe"
        return None

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr(subprocess, "run", fake_run)

    template = WebJSTemplate(framework="react", extras=[])
    template.post_install(tmp_path)

    assert calls, "npm install was never invoked"
    assert calls[0][0] == r"C:\Program Files\nodejs\npm.cmd"


def test_post_install_missing_node_does_not_raise(tmp_path, monkeypatch):
    # If node/npm aren't on PATH, post_install should degrade to a
    # no-op (user runs npm install manually) instead of crashing the
    # rest of `spawn create`.
    monkeypatch.setattr("shutil.which", lambda name: None)

    template = WebJSTemplate(framework="vanilla", extras=[])
    template.post_install(tmp_path)  # must not raise


def test_post_install_file_not_found_does_not_abort(tmp_path, monkeypatch):
    """
    Reproduces the exact WinError 2 crash: npm resolves via which(),
    but subprocess.run still raises FileNotFoundError. This must be
    caught, not propagated, so the rest of `spawn create` (git init,
    README, etc.) already having succeeded isn't undone by an
    unhandled exception here.
    """
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")

    def raise_not_found(cmd, *args, **kwargs):
        raise FileNotFoundError(2, "The system cannot find the file specified")

    monkeypatch.setattr(subprocess, "run", raise_not_found)

    template = WebJSTemplate(framework="nextjs", extras=[])
    template.post_install(tmp_path)  # must not raise
