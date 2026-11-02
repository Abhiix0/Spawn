from __future__ import annotations

from pathlib import Path

import spawn
from spawn.inspection import DetectionState, FindingCategory, run_inspection

EMBEDDED = """\
TEMPLATE = '''
from django.db import models
import flask
from fastapi import FastAPI
from pydantic import BaseModel
'''
"""


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def diag_codes(report):
    return {d.code for d in report.diagnostics} | {
        d.code for r in report.analyzer_results for d in r.diagnostics
    }


def frameworks(report):
    return {
        f.subject: f.detection_state
        for f in report.findings
        if f.category == FindingCategory.FRAMEWORK
    }


def make_generator_repo(root: Path) -> None:
    write(root, "pyproject.toml", '[project]\nname = "gen"\ndependencies = ["typer"]\n')
    write(root, "gen/templates.py", EMBEDDED)
    write(root, "gen/__init__.py", "")


def test_generator_repo_with_embedded_framework_code(tmp_path):
    make_generator_repo(tmp_path)
    report = run_inspection(tmp_path)
    assert frameworks(report) == {}
    assert report.summary.primary_framework is None
    assert "framework.unparseable_source" not in diag_codes(report)


def test_positive_control_real_import_still_detected(tmp_path):
    make_generator_repo(tmp_path)
    write(tmp_path, "app.py", "from flask import Flask\n")
    report = run_inspection(tmp_path)
    assert frameworks(report) == {"flask": DetectionState.DETECTED}
    assert report.summary.primary_framework == "flask"


def test_self_inspection_of_spawn_templates():
    root = Path(spawn.__file__).resolve().parent / "templates"
    assert root.is_dir()
    report = run_inspection(root)
    assert frameworks(report) == {}
    assert report.summary.primary_framework is None
    assert "framework.unparseable_source" not in diag_codes(report)
