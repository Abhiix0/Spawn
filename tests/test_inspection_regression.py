"""End-to-end inspection regression suite (#60).

Layering: analyzer unit tests own parser details, the orchestrator tests own
merge/status rules, and THIS suite owns archetype-level invariants and
cross-analyzer behaviour on generated trees (``tests/fixtures/inspection_corpus.py``).
It asserts compact ``{category: {subject: state}}`` tables, never full snapshots,
and does not re-test parser edge cases.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import pytest
from fixtures import inspection_corpus as corpus
from typer.testing import CliRunner

from spawn.cli.app import app
from spawn.inspection import (
    AnalysisStatus,
    DetectionState,
    InspectionError,
    from_json,
    run_inspection,
    to_json,
    validate_report,
)
from spawn.inspection.discovery import discover_repository, validate_inspection_root

ND = "not_detected"
D, INF, U = "detected", "inferred", "unknown"

# What every tree reports when nothing is present.
BASE = {
    "ci": {"github-actions": ND},
    "container": {"docker": ND},
    "structure": {"tests-directory": ND},
    "tool": {"git": ND, "pytest": ND, "ruff": ND},
}
ANALYZERS = ["dependency", "framework", "language", "tooling"]


def table(**over: dict[str, str]) -> dict[str, dict[str, str]]:
    out = {cat: dict(subj) for cat, subj in BASE.items()}
    for cat, subj in over.items():
        out.setdefault(cat, {}).update(subj)
    return out


PY_DEPS = {"dependency": {"httpx": D}, "language": {"python": D}}
PY_TOOLS = {"pytest": D, "ruff": D}
WEB_DEPS = {"eslint": D, "react": D, "typescript": D}

# archetype -> (report status, findings table, diagnostic codes in report + analyzers)
EXPECTED = {
    "python_project": (
        "complete",
        table(
            ci={"github-actions": D},
            container={"docker": D},
            package_manager={"uv": D},
            structure={"src-layout": D, "tests-directory": D},
            tool=PY_TOOLS,
            **PY_DEPS,
        ),
        set(),
    ),
    "node_project": (
        "complete",
        table(
            dependency=WEB_DEPS,
            framework={"react": D},
            language={"javascript": D, "typescript": D},
            package_manager={"npm": D},
            tool={"eslint": INF},
        ),
        set(),
    ),
    "monorepo": (
        "complete",
        table(
            dependency={**WEB_DEPS, "httpx": D},
            framework={"react": INF},
            language={"go": D, "javascript": D, "python": D, "typescript": D},
            tool={"eslint": INF, **PY_TOOLS},
        ),
        set(),
    ),
    "empty": ("complete", table(), set()),
    "unknown": ("complete", table(), set()),
    "config_only": (
        "complete",
        table(container={"docker": D}, tool={"pre-commit": D, "ruff": D}),
        set(),
    ),
    "malformed": (
        "partial",
        table(
            language={"python": D, "typescript": D},
            tool={"pytest": U, "ruff": U},
        ),
        {
            "dependency.malformed_manifest",
            "dependency.undecodable_file",
            "framework.malformed_manifest",
            "framework.unreadable_file",
            "language.malformed_manifest",
            "tooling.malformed_manifest",
            "tooling.undecodable_file",
        },
    ),
    "lockfiles": (
        "complete",
        table(
            dependency={**WEB_DEPS, "httpx": D},
            framework={"react": INF},
            language={"javascript": D, "python": D},
            package_manager={"npm": D, "uv": D, "yarn": D},
            tool={"eslint": INF, **PY_TOOLS},
        ),
        set(),
    ),
    "spawn_generated": (
        "complete",
        table(
            structure={"spawn-generated": D, "src-layout": D},
            tool=PY_TOOLS,
            **PY_DEPS,
        ),
        set(),
    ),
    "spawn_meta_malformed": (
        "partial",
        table(structure={"spawn-generated": INF}, tool=PY_TOOLS, **PY_DEPS),
        {"orchestrator.meta_unreadable", "tooling.malformed_metadata"},
    ),
    "ambiguous_frameworks": (
        "complete",
        table(
            dependency={"express": D, "fastapi": D, "flask": D},
            framework={"django": D, "express": D, "fastapi": INF, "flask": D},
            language={"javascript": D, "python": D},
        ),
        set(),
    ),
    "size_limits": (
        "partial",
        table(
            dependency={"react": D},
            framework={"react": INF},
            language={"javascript": D, "python": D},
            tool={"pytest": U, "ruff": U},
        ),
        {
            "dependency.file_too_large",
            "framework.file_too_large",
            "language.manifest_too_large",
            "tooling.file_too_large",
        },
    ),
    "special_files": ("complete", table(tool=PY_TOOLS, **PY_DEPS), set()),
}
assert set(EXPECTED) == set(corpus.ARCHETYPES)

MANIFESTS = ("pyproject.toml", "package.json", "requirements.txt", "go.mod")


def inspect_tree(tmp_path, name):
    root = corpus.materialize(name, tmp_path / "with space")
    return root, run_inspection(root)


def states(report):
    out: dict[str, dict[str, str]] = {}
    for f in report.findings:
        out.setdefault(f.category.value, {})[f.subject] = f.detection_state.value
    return out


def diag_codes(report):
    return {d.code for d in report.diagnostics} | {
        d.code for r in report.analyzer_results for d in r.diagnostics
    }


def snapshot(root: Path):
    snap = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for n in [*dirnames, *filenames]:
            p = Path(dirpath, n)
            st = p.lstat()
            digest = (
                hashlib.sha256(p.read_bytes()).hexdigest()
                if p.is_file() and not p.is_symlink()
                else None
            )
            snap[p.relative_to(root).as_posix()] = (st.st_size, st.st_mtime_ns, digest)
    return snap


def stable(report):
    d = report.to_dict()
    d.pop("generated_at")
    return d


@pytest.fixture(scope="module", params=corpus.ARCHETYPES)
def archetype(request, tmp_path_factory):
    """Inspected once per archetype; tests below must not mutate the tree."""
    root, report = inspect_tree(tmp_path_factory.mktemp("corpus"), request.param)
    return request.param, root, report


# --- expected table ----------------------------------------------------------


def test_expected_table(archetype):
    name, _, report = archetype
    status, findings, codes = EXPECTED[name]
    assert report.status.value == status
    assert states(report) == findings
    assert diag_codes(report) == codes


def test_summary_origin(archetype):
    name, root, report = archetype
    spawn = name == "spawn_generated"
    assert report.summary.name == root.name
    assert report.summary.origin == ("spawn" if spawn else "external")
    assert (report.summary.spawn_version == "1.0.9") == spawn


# --- invariants over every archetype -----------------------------------------


def test_report_is_valid(archetype):
    assert validate_report(archetype[2]) == []


def test_evidence_rules(archetype):
    _, root, report = archetype
    inv = discover_repository(validate_inspection_root(root))
    known = {*inv.files, *inv.directories, *inv.skipped}
    for f in report.findings:
        if f.detection_state in (DetectionState.DETECTED, DetectionState.INFERRED):
            assert f.evidence, f
        for e in f.evidence:
            assert not e.path.startswith("/") and ":" not in e.path[:2]
            assert "\\" not in e.path
            assert ".." not in e.path.split("/")
            assert e.path in known, e.path


def test_no_absolute_path_leak(archetype):
    _, root, report = archetype
    text = to_json(report).replace("\\\\", "\\")
    for p in (str(root), root.as_posix(), str(root.parent), root.parent.as_posix()):
        assert p not in text


def test_deterministic_and_location_independent(archetype, tmp_path):
    name, root, report = archetype
    other = tmp_path / "elsewhere" / name
    shutil.copytree(root, other, symlinks=True)
    assert stable(run_inspection(root)) == stable(report)
    assert stable(run_inspection(other)) == stable(report)


def test_json_round_trip(archetype):
    text = to_json(archetype[2])
    assert to_json(from_json(text)) == text


def test_canonical_ordering(archetype):
    report = archetype[2]
    keys = [(f.category.value, f.subject) for f in report.findings]
    assert keys == sorted(keys) and len(set(keys)) == len(keys)
    assert [r.analyzer_name for r in report.analyzer_results] == ANALYZERS
    for f in report.findings:
        ev = [(e.path, e.indicator, e.detail or "") for e in f.evidence]
        assert ev == sorted(ev)


def test_filesystem_untouched(archetype):
    _, root, _ = archetype
    before = snapshot(root)
    run_inspection(root)
    assert snapshot(root) == before


def test_findings_come_from_analyzers(archetype):
    report = archetype[2]
    produced = {
        (f.category, f.subject, f.detection_state)
        for r in report.analyzer_results
        for f in r.findings
    }
    for f in report.findings:
        assert (f.category, f.subject, f.detection_state) in produced


def test_dependency_only_frameworks_stay_inferred(archetype):
    for f in archetype[2].findings:
        if f.category.value != "framework":
            continue
        direct = [e for e in f.evidence if e.path.rsplit("/", 1)[-1] not in MANIFESTS]
        if f.detection_state == DetectionState.DETECTED:
            assert direct, f
        elif f.detection_state == DetectionState.INFERRED:
            assert f.detail and not direct, f


# --- archetype-specific behaviour --------------------------------------------


def test_ambiguous_frameworks_do_not_cross_languages(tmp_path):
    _, report = inspect_tree(tmp_path, "ambiguous_frameworks")
    ev = {f.subject: {e.path for e in f.evidence} for f in report.findings}
    assert ev["express"] == {"package.json", "server.js"}
    assert "app.py" in ev["flask"] and "server.js" not in ev["flask"]
    assert ev["django"] == {"examples/demo.py"}
    assert ev["fastapi"] == {"pyproject.toml"}


def test_size_limit_boundary(tmp_path):
    root = corpus.materialize("size_limits", tmp_path)
    start = time.perf_counter()
    report = run_inspection(root)
    assert time.perf_counter() - start < 15  # 1 MB of blanks must not hang
    paths = {e.path for f in report.findings for e in f.evidence}
    assert "ok/package.json" in paths and "big/package.json" not in paths
    assert "vue" not in {f.subject for f in report.findings}
    flagged = {d.path for r in report.analyzer_results for d in r.diagnostics}
    assert flagged == {"big/package.json"}


def test_utf16_requirements_not_decoded(tmp_path):
    _, report = inspect_tree(tmp_path, "malformed")
    assert "flask" not in {f.subject for f in report.findings}
    assert {r.status.value for r in report.analyzer_results} == {"partial"}


def test_excluded_dirs_and_symlinks(tmp_path):
    root = corpus.materialize("special_files", tmp_path)
    linked = corpus.add_symlinks(root)
    report = run_inspection(root)
    assert not {"vue", "go"} & {f.subject for f in report.findings}
    for f in report.findings:
        for e in f.evidence:
            assert not e.path.startswith(("node_modules/", "build/", "dist/", ".venv/"))
    if not linked:
        pytest.skip("symlinks unavailable")
    skipped = {
        d.path for d in report.diagnostics if d.code == "discovery.symlink_skipped"
    }
    assert skipped == {"link.txt", "linkdir"}
    assert report.status == AnalysisStatus.COMPLETE  # symlink_skipped is info-level
    assert states(report) == EXPECTED["special_files"][1]


@pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permissions and a non-root user",
)
def test_unreadable_subdirectory(tmp_path):
    root = corpus.materialize("python_project", tmp_path)
    locked = root / "locked"
    locked.mkdir()
    locked.chmod(0)
    try:
        report = run_inspection(root)
    finally:
        locked.chmod(0o755)
    assert [(d.path, d.code) for d in report.diagnostics] == [
        ("locked", "discovery.permission_denied")
    ]
    assert report.status == AnalysisStatus.PARTIAL
    assert states(report) == EXPECTED["python_project"][1]


def test_crlf_manifest_same_as_lf(tmp_path):
    root = corpus.materialize("python_project", tmp_path)
    base = states(run_inspection(root))
    pp = root / "pyproject.toml"
    pp.write_bytes(pp.read_bytes().replace(b"\n", b"\r\n"))
    assert states(run_inspection(root)) == base


def test_uppercase_extensions(tmp_path):
    (tmp_path / "Main.PY").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "stats.R").write_text("x <- 1\n", encoding="utf-8")
    assert states(run_inspection(tmp_path))["language"] == {"python": D, "r": D}


@pytest.mark.skipif(sys.platform == "win32", reason="non-UTF-8 names need POSIX")
@pytest.mark.xfail(
    strict=True,
    raises=UnicodeEncodeError,
    reason="production bug: undecodable names reach to_json as lone surrogates "
    "(structure.top_level_files); to_json(...) is not valid UTF-8 (see #60 report)",
)
def test_non_utf8_filename(tmp_path):
    root = corpus.materialize("python_project", tmp_path)
    try:
        with open(os.fsencode(root) + b"/bad\xff.txt", "wb") as fh:
            fh.write(b"x")
    except (OSError, UnicodeError):
        pytest.skip("filesystem rejects non-UTF-8 names")
    report = run_inspection(root)
    assert validate_report(report) == []
    to_json(report).encode("utf-8")


# --- failure paths -----------------------------------------------------------


def test_malformed_manifest_isolated_to_its_analyzer(tmp_path):
    root = corpus.materialize("python_project", tmp_path)
    (root / "pyproject.toml").write_text("[project\n", encoding="utf-8")
    report = run_inspection(root)
    by = {r.analyzer_name: r for r in report.analyzer_results}
    assert by["dependency"].status == AnalysisStatus.PARTIAL
    assert any(d.path == "pyproject.toml" for d in by["dependency"].diagnostics)
    assert report.status == AnalysisStatus.PARTIAL
    found = states(report)
    assert found["container"] == {"docker": D}
    assert found["ci"] == {"github-actions": D}
    assert found["package_manager"] == {"uv": D}


def test_crashing_analyzer_is_contained(tmp_path, monkeypatch):
    from spawn.inspection.dependencies import DependencyAnalyzer

    def boom(self, target, inventory):
        raise RuntimeError("secret detail")

    monkeypatch.setattr(DependencyAnalyzer, "run", boom)
    root = corpus.materialize("python_project", tmp_path)
    report = run_inspection(root)
    by = {r.analyzer_name: r for r in report.analyzer_results}
    assert by["dependency"].status == AnalysisStatus.FAILED
    assert [(d.code, d.fatal) for d in by["dependency"].diagnostics] == [
        ("orchestrator.analyzer_crashed", True)
    ]
    assert "secret detail" not in to_json(report)
    assert report.status == AnalysisStatus.PARTIAL
    found = states(report)
    assert "dependency" not in found
    assert found["language"] == {"python": D}
    assert found["container"] == {"docker": D}
    assert validate_report(report) == []


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_bad_root_raises(tmp_path, kind):
    bad = tmp_path / "nope"
    if kind == "file":
        bad.write_text("x", encoding="utf-8")
    with pytest.raises(InspectionError):
        run_inspection(bad)


@pytest.mark.parametrize("name", ["python_project", "malformed"])
def test_cli_json_round_trip(tmp_path, name):
    root = corpus.materialize(name, tmp_path)
    result = CliRunner().invoke(app, ["inspect", str(root), "--json"])
    assert result.exit_code == 0, result.output
    report = from_json(result.stdout)
    assert json.loads(result.stdout)["status"] == EXPECTED[name][0]
    assert states(report) == EXPECTED[name][1]
    assert validate_report(report) == []
