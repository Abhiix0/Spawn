"""Contract-level tests for static framework detection (#55)."""

import re
import time
import warnings
from dataclasses import replace
from pathlib import Path

import pytest

from spawn.inspection.discovery import discover_repository
import spawn.inspection.frameworks as fw
from spawn.inspection.frameworks import (
    IMPORTS,
    PY_IMPORT_MODULES,
    FrameworkDetector,
    _dependency_names,
)
from spawn.inspection.languages import MAX_FILE_SIZE
from spawn.inspection.models import (
    AnalysisStatus,
    DetectionState,
    Evidence,
    FindingCategory,
    InspectionTarget,
)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(root: Path):
    target = InspectionTarget(root.resolve())
    return FrameworkDetector().run(target, discover_repository(target))


def test_detects_framework_imports_and_multiple_frameworks(tmp_path):
    write(tmp_path, "api/main.py", "from fastapi import FastAPI\napp = FastAPI()\n")
    write(
        tmp_path, "web/app.tsx", "import React from 'react';\nexport default React;\n"
    )
    result = run(tmp_path)
    by_subject = {f.subject: f for f in result.findings}
    assert set(by_subject) == {"fastapi", "react"}
    assert all(f.category is FindingCategory.FRAMEWORK for f in result.findings)
    assert all(f.detection_state is DetectionState.DETECTED for f in result.findings)
    assert by_subject["fastapi"].evidence[0].path == "api/main.py"


def test_dependency_only_is_inferred_with_explanation(tmp_path):
    write(tmp_path, "requirements.txt", "fastapi>=0.100\n")
    result = run(tmp_path)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.subject == "fastapi"
    assert finding.detection_state is DetectionState.INFERRED
    assert finding.detail
    assert finding.evidence[0].path == "requirements.txt"


def test_framework_name_in_directory_or_readme_is_not_evidence(tmp_path):
    write(tmp_path, "fastapi/README.md", "React, Django, FastAPI")
    write(tmp_path, "README.md", "This directory will use Next.js someday")
    assert run(tmp_path).findings == ()


def test_framework_specific_config_is_direct_evidence(tmp_path):
    write(tmp_path, "next.config.js", "module.exports = {}\n")
    result = run(tmp_path)
    assert result.findings[0].subject == "nextjs"
    assert result.findings[0].detection_state is DetectionState.DETECTED
    assert result.findings[0].evidence[0].path == "next.config.js"


def test_malformed_manifest_is_diagnostic_and_partial(tmp_path):
    write(tmp_path, "package.json", "{bad json")
    result = run(tmp_path)
    assert result.status.value == "partial"
    assert result.findings == ()
    assert result.diagnostics[0].code == "framework.malformed_manifest"


def test_unrecognized_dependency_is_not_reported_as_framework(tmp_path):
    write(
        tmp_path, "package.json", '{"dependencies": {"some-unknown-framework": "1.0"}}'
    )
    assert run(tmp_path).findings == ()


def _write_bytes(root: Path, rel: str, data: bytes) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_bytes(data)


def _subjects(result):
    return {f.subject: f.detection_state for f in result.findings}


@pytest.mark.parametrize("filler", ["\n", " "])
def test_whitespace_only_source_file_is_processed_quickly(tmp_path, filler):
    write(tmp_path, "blank.py", filler * 1_000_000)
    start = time.perf_counter()
    result = run(tmp_path)
    assert time.perf_counter() - start < 5.0
    assert result.findings == ()


def test_all_import_patterns_are_anchored_without_newline_spanning():
    assert len(IMPORTS) == 7
    assert all(p.startswith("(?m)^[ \\t]*") for p in IMPORTS.values())
    assert PY_IMPORT_MODULES == {"django", "fastapi", "flask", "pydantic", "starlette"}


def test_imports_inside_strings_are_not_evidence(tmp_path):
    src = (
        'TEMPLATE = """\nfrom django.db import models\nimport flask\n'
        'from fastapi import FastAPI\n"""\n'
    )
    write(tmp_path, "t.py", src)
    result = run(tmp_path)
    assert result.findings == ()
    assert result.status is AnalysisStatus.COMPLETE


def test_commented_and_docstring_imports_are_not_evidence(tmp_path):
    write(
        tmp_path,
        "a.py",
        '"""\nimport flask\n"""\n# from flask import Flask\n#import django\n',
    )
    assert run(tmp_path).findings == ()


def test_real_import_with_string_mention_reports_only_real(tmp_path):
    write(tmp_path, "pkg/a.py", 'import flask\nS = """\nimport django\n"""\n')
    result = run(tmp_path)
    assert _subjects(result) == {"flask": DetectionState.DETECTED}
    assert result.findings[0].evidence[0].path == "pkg/a.py"


def test_submodule_from_import_is_detected(tmp_path):
    write(tmp_path, "a.py", "from fastapi.responses import JSONResponse\n")
    assert _subjects(run(tmp_path)) == {"fastapi": DetectionState.DETECTED}


def test_multi_nested_and_try_imports_are_detected(tmp_path):
    write(tmp_path, "a.py", "import os, flask\n")
    write(tmp_path, "b.py", "def f():\n    import django\n")
    write(
        tmp_path, "c.py", "try:\n    import starlette\nexcept ImportError:\n    pass\n"
    )
    assert set(_subjects(run(tmp_path))) == {"flask", "django", "starlette"}


def test_relative_imports_are_ignored(tmp_path):
    write(tmp_path, "a.py", "from .django import x\nfrom . import flask\n")
    assert run(tmp_path).findings == ()


def test_lookalike_modules_are_ignored(tmp_path):
    write(
        tmp_path,
        "a.py",
        "import flask_cors\nfrom fastapi_users import x\nimport rest_framework\n",
    )
    assert run(tmp_path).findings == ()


def test_syntax_error_is_diagnostic_and_other_files_still_detected(tmp_path):
    write(tmp_path, "bad.py", "import flask\ndef (:\n")
    write(tmp_path, "good.py", "import django\n")
    result = run(tmp_path)
    assert _subjects(result) == {"django": DetectionState.DETECTED}
    assert result.status is AnalysisStatus.PARTIAL
    d = result.diagnostics[0]
    assert d.code == "framework.unparseable_source"
    assert d.path == "bad.py"
    assert d.message == (
        "Could not parse Python source (SyntaxError); imports not analyzed."
    )


def test_null_byte_file_is_diagnostic(tmp_path):
    _write_bytes(tmp_path, "n.py", b"import flask\x00\n")
    result = run(tmp_path)
    assert result.findings == ()
    assert result.diagnostics[0].code == "framework.unparseable_source"


def test_recursion_error_is_diagnostic(tmp_path, monkeypatch):
    write(tmp_path, "a.py", "import flask\n")

    def deep(*args, **kwargs):
        raise RecursionError

    monkeypatch.setattr(fw.ast, "parse", deep)
    result = run(tmp_path)
    assert result.findings == ()
    assert result.diagnostics[0].code == "framework.unparseable_source"


def test_python_syntax_warnings_do_not_escape(tmp_path):
    write(tmp_path, "a.py", 'x = "\\d"\nimport flask\n')
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = run(tmp_path)
    assert _subjects(result) == {"flask": DetectionState.DETECTED}


def test_patterns_apply_only_to_their_own_language(tmp_path):
    write(tmp_path, "a.py", "import React from 'react'\n")
    write(tmp_path, "b.js", "from flask import Flask\n")
    write(tmp_path, "c.tsx", "import React from 'react';\n")
    result = run(tmp_path)
    assert _subjects(result) == {"react": DetectionState.DETECTED}
    assert [e.path for e in result.findings[0].evidence] == ["c.tsx"]


def test_large_valid_python_parses_quickly(tmp_path):
    line = b"x = 1\n"
    _write_bytes(tmp_path, "big.py", line * (MAX_FILE_SIZE // len(line)))
    start = time.perf_counter()
    result = run(tmp_path)
    assert time.perf_counter() - start < 5.0
    assert result.status is AnalysisStatus.COMPLETE


def test_file_of_exactly_the_byte_limit_is_accepted(tmp_path):
    head = b"import flask\n"
    _write_bytes(tmp_path, "ok.py", head + b"#" * (MAX_FILE_SIZE - len(head)))
    assert (tmp_path / "ok.py").stat().st_size == MAX_FILE_SIZE
    assert _subjects(run(tmp_path)) == {"flask": DetectionState.DETECTED}


def test_one_byte_over_limit_is_rejected(tmp_path):
    head = b"import flask\n"
    _write_bytes(tmp_path, "big.py", head + b"#" * (MAX_FILE_SIZE + 1 - len(head)))
    result = run(tmp_path)
    assert result.findings == ()
    assert result.status.value == "partial"
    assert result.diagnostics[0].code == "framework.file_too_large"


def test_multibyte_file_under_char_limit_but_over_byte_limit_is_rejected(tmp_path):
    text = "é" * 600_000  # 600k characters, 1.2M bytes
    _write_bytes(tmp_path, "wide.py", text.encode())
    assert run(tmp_path).diagnostics[0].code == "framework.file_too_large"


def test_reads_are_bounded(tmp_path, monkeypatch):
    _write_bytes(tmp_path, "big.py", b"x" * (MAX_FILE_SIZE * 3))
    target = InspectionTarget(tmp_path.resolve())
    inventory = discover_repository(target)
    sizes = []
    real_open = Path.open

    def spy(self, *args, **kwargs):
        fh = real_open(self, *args, **kwargs)
        real_read = fh.read

        def read(n=-1):
            sizes.append(n)
            return real_read(n)

        fh.read = read
        return fh

    monkeypatch.setattr(Path, "open", spy)
    FrameworkDetector().run(target, inventory)
    assert sizes == [MAX_FILE_SIZE + 1]


def test_bom_crlf_and_empty_files(tmp_path):
    _write_bytes(
        tmp_path, "package.json", b'\xef\xbb\xbf{"dependencies": {"react": "1"}}'
    )
    _write_bytes(tmp_path, "requirements.txt", b"\xef\xbb\xbfflask\r\ndjango>=4\r\n")
    write(tmp_path, "empty.py", "")
    write(tmp_path, "empty/requirements.txt", "")
    result = run(tmp_path)
    assert set(_subjects(result)) == {"react", "flask", "django"}
    assert result.status.value == "complete"


@pytest.mark.parametrize("data", [b"\xff\xfe\x00bad", "import flask".encode("utf-16")])
def test_non_utf8_file_is_diagnostic(tmp_path, data):
    _write_bytes(tmp_path, "app.py", data)
    result = run(tmp_path)
    assert result.findings == ()
    assert result.status.value == "partial"
    assert result.diagnostics[0].code == "framework.unreadable_file"


@pytest.mark.parametrize("body", ["tool = 1\n", "[tool]\npoetry = 1\n"])
def test_non_table_tool_or_poetry_does_not_raise(tmp_path, body):
    write(tmp_path, "pyproject.toml", "[project]\nname='x'\n" + body)
    assert run(tmp_path).status.value == "complete"


def test_list_root_and_non_list_dependencies_do_not_raise(tmp_path):
    write(tmp_path, "package.json", "[]")
    write(tmp_path, "pyproject.toml", "[project]\ndependencies = 'flask'\n")
    result = run(tmp_path)
    assert result.findings == ()
    assert [d.code for d in result.diagnostics] == ["framework.malformed_manifest"]


def test_unexpected_exception_yields_failed_result(tmp_path, monkeypatch):
    write(tmp_path, "requirements.txt", "flask\n")
    target = InspectionTarget(tmp_path.resolve())
    inventory = discover_repository(target)

    def boom(*args, **kwargs):
        raise RuntimeError(str(tmp_path))

    monkeypatch.setattr("spawn.inspection.frameworks._dependency_names", boom)
    result = FrameworkDetector().run(target, inventory)
    assert result.status is AnalysisStatus.FAILED
    assert result.diagnostics[-1].code == "framework.internal_error"
    assert result.diagnostics[-1].fatal
    assert str(tmp_path) not in result.diagnostics[-1].message


def test_diagnostics_do_not_leak_paths_or_raw_exception_text(tmp_path, monkeypatch):
    write(tmp_path, "app.py", "import flask\n")
    write(tmp_path, "package.json", "{}")
    target = InspectionTarget(tmp_path.resolve())
    inventory = discover_repository(target)

    def deny(self, *args, **kwargs):
        raise OSError(f"cannot open {tmp_path}")

    monkeypatch.setattr(Path, "open", deny)
    result = FrameworkDetector().run(target, inventory)
    assert [d.code for d in result.diagnostics] == ["framework.unreadable_file"] * 2
    assert all(str(tmp_path) not in d.message for d in result.diagnostics)
    assert all("OSError" in d.message for d in result.diagnostics)


def test_malformed_json_message_has_no_raw_exception_text(tmp_path):
    write(tmp_path, "package.json", "{bad json")
    message = run(tmp_path).diagnostics[0].message
    assert message == "Could not parse manifest (JSONDecodeError)."


def test_state_comes_from_evidence_kind_not_indicator_wording(tmp_path, monkeypatch):
    write(tmp_path, "requirements.txt", "flask\n")
    write(tmp_path, "app/main.py", "import fastapi\n")
    monkeypatch.setattr(
        fw, "Evidence", lambda path, indicator: Evidence(path, "reworded")
    )
    assert _subjects(run(tmp_path)) == {
        "flask": DetectionState.INFERRED,
        "fastapi": DetectionState.DETECTED,
    }


def test_import_plus_dependency_is_detected_with_both_evidence(tmp_path):
    write(tmp_path, "requirements.txt", "flask\n")
    write(tmp_path, "a.py", "from flask import Flask\n")
    finding = run(tmp_path).findings[0]
    assert finding.detection_state is DetectionState.DETECTED
    assert [e.path for e in finding.evidence] == ["a.py", "requirements.txt"]


def test_pep508_names_are_extracted(tmp_path):
    write(
        tmp_path,
        "pyproject.toml",
        "[project]\nname='x'\ndependencies = [\n"
        "  'Flask (>=2)',\n  'FastAPI[all]>=1; python_version<\"3.12\"',\n"
        "  'Django @ https://example.test/d.zip',\n  42,\n]\n",
    )
    assert set(_subjects(run(tmp_path))) == {"flask", "fastapi", "django"}


def test_names_are_normalized_per_pep503():
    names = _dependency_names("requirements.txt", "Py_Dantic\nPydantic.Core\nFlask\n")
    assert names == {"py-dantic", "pydantic-core", "flask"}


def test_optional_dependencies_groups_and_poetry_groups(tmp_path):
    write(
        tmp_path,
        "pyproject.toml",
        "[project]\nname='x'\n"
        "[project.optional-dependencies]\nweb = ['flask']\n"
        "[dependency-groups]\ndev = ['fastapi', {include-group = 'web'}]\n"
        "[tool.poetry]\nname='x'\n"
        "[tool.poetry.group.docs.dependencies]\npython = '^3.12'\ndjango = '*'\n",
    )
    assert set(_subjects(run(tmp_path))) == {"flask", "fastapi", "django"}


def test_pipfile_is_parsed_as_toml(tmp_path):
    write(
        tmp_path,
        "Pipfile",
        '[packages]\nFlask = {version = "*", extras = ["async"]}\n'
        '[dev-packages]\nfastapi = "*"\n',
    )
    assert set(_subjects(run(tmp_path))) == {"flask", "fastapi"}
    write(tmp_path, "sub/Pipfile", "[packages\n")
    result = run(tmp_path)
    assert result.diagnostics[0].code == "framework.malformed_manifest"
    assert result.diagnostics[0].path == "sub/Pipfile"


def test_manifest_parsing_emits_no_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _dependency_names("pyproject.toml", "[project]\ndependencies=['a>=1']\n")
        _dependency_names("requirements.txt", "a>=1\n")


def test_monorepo_nested_manifests(tmp_path):
    write(
        tmp_path,
        "services/api/pyproject.toml",
        "[project]\nname='api'\ndependencies=['fastapi']\n",
    )
    write(tmp_path, "services/web/package.json", '{"dependencies": {"next": "1"}}')
    write(tmp_path, "services/web/next.config.js", "module.exports={}")
    result = run(tmp_path)
    assert _subjects(result) == {
        "fastapi": DetectionState.INFERRED,
        "nextjs": DetectionState.DETECTED,
    }
    assert [e.path for f in result.findings for e in f.evidence] == [
        "services/api/pyproject.toml",
        "services/web/next.config.js",
        "services/web/package.json",
    ]


def test_deterministic_across_runs_and_inventory_order(tmp_path):
    write(tmp_path, "b/requirements.txt", "flask\n")
    write(tmp_path, "a/app.py", "import flask\n")
    write(tmp_path, "c/package.json", '{"dependencies": {"react": "1"}}')
    target = InspectionTarget(tmp_path.resolve())
    inventory = discover_repository(target)
    first = FrameworkDetector().run(target, inventory)
    assert FrameworkDetector().run(target, inventory) == first
    flipped = replace(inventory, files=tuple(reversed(inventory.files)))
    assert FrameworkDetector().run(target, flipped) == first


# ─── ISEC-01 bounded framework regex work ──────────────────────────────────


@pytest.mark.parametrize(
    "framework, positive_line",
    [
        ("react", "import React from 'react';"),
        ("nextjs", "import Link from 'next/link';"),
        ("vue", "import { ref } from 'vue';"),
        ("nuxt", "import { useAsyncData } from 'nuxt/app';"),
        ("angular", "import { Component } from '@angular/core';"),
        ("svelte", "import { onMount } from 'svelte';"),
        ("express", "import express from 'express';"),
        ("express", "const express = require('express');"),
    ],
)
def test_framework_import_patterns_positives_and_hostiles(framework, positive_line):
    pattern = IMPORTS[framework]
    # Positive case matches
    assert re.search(pattern, positive_line) is not None

    # Hostile line with trailing spaces does not match and completes fast
    hostile = "import from " + (" " * 500)
    start = time.perf_counter()
    assert re.search(pattern, hostile) is None
    assert time.perf_counter() - start < 1.0


def test_framework_import_line_boundaries_and_length_limit(tmp_path):
    # Overlong line (>1000 characters) followed by a valid import
    overlong = "// " + ("x" * 2000)
    valid = "import React from 'react';"
    write(tmp_path, "src/app.js", f"{overlong}\n{valid}\n")

    result = run(tmp_path)
    assert "react" in _subjects(result)
    assert result.status is AnalysisStatus.COMPLETE


def test_large_app_js_inspection_bounded_time(tmp_path):
    # 64 KB of spaces after import from
    hostile_js = "import from " + (" " * 64000)
    write(tmp_path, "src/app.js", hostile_js)
    start = time.perf_counter()
    result = run(tmp_path)
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0
    assert result.status is AnalysisStatus.COMPLETE

