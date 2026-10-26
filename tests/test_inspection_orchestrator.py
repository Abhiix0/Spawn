"""Orchestrator tests (#58)."""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import pytest

from spawn.inspection import (
    AnalysisStatus as S,
    AnalyzerResult,
    DetectionState as D,
    Diagnostic,
    Evidence,
    Finding,
    FindingCategory as C,
    InspectionError,
    from_json,
    run_inspection,
    to_json,
    validate_report,
)
from spawn.inspection import orchestrator as orch


class Fake:
    def __init__(
        self, name, findings=(), diagnostics=(), status=S.COMPLETE, raises=None
    ):
        self.name = name
        self._r = (findings, diagnostics, status)
        self._raises = raises

    def run(self, target, inventory):
        if self._raises:
            raise self._raises
        f, d, s = self._r
        return AnalyzerResult(self.name, s, tuple(f), tuple(d))


def fnd(
    subject="x", state=D.DETECTED, ev=(("a.txt", "ind", None),), detail=None, cat=C.TOOL
):
    return Finding(cat, subject, state, tuple(Evidence(*e) for e in ev), detail)


def diag(sev="warning", fatal=False, source="fake"):
    return Diagnostic("fake.code", "msg", sev, source, None, fatal)


def inspect(tmp_path, analyzers):
    return orch._inspect(tmp_path, analyzers)


def make_tree(root: Path, files: dict[str, str]):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        h.update(str(p.relative_to(root)).encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def dumped(report):
    d = report.to_dict()
    d.pop("generated_at")
    return d


PY_NODE = {
    "pyproject.toml": '[project]\nname="demo"\ndependencies=["fastapi"]\n',
    "app/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
    "package.json": '{"name":"web","dependencies":{"express":"^4"}}',
    "index.js": "const express = require('express')\n",
    "tests/test_a.py": "def test_a(): pass\n",
}


# --- roots -----------------------------------------------------------------


def test_bad_path_raises(tmp_path):
    with pytest.raises(InspectionError):
        run_inspection(tmp_path / "missing")


def test_file_root_raises(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x")
    with pytest.raises(InspectionError):
        run_inspection(f)


def test_discovery_failure_gives_failed_report(tmp_path, monkeypatch):
    def boom(_):
        raise InspectionError(f"nope {tmp_path}")

    monkeypatch.setattr(orch, "discover_repository", boom)
    r = run_inspection(tmp_path)
    assert r.status == S.FAILED and r.findings == ()
    assert [x.status for x in r.analyzer_results] == [S.SKIPPED] * 4
    (d,) = r.diagnostics
    assert (d.code, d.source, d.severity, d.fatal) == (
        "discovery.root_scan_failed",
        "discovery",
        "error",
        True,
    )
    assert str(tmp_path) not in to_json(r)
    assert validate_report(r) == []


def test_discover_called_once(tmp_path, monkeypatch):
    calls = []
    real = orch.discover_repository
    monkeypatch.setattr(
        orch, "discover_repository", lambda t: calls.append(1) or real(t)
    )
    run_inspection(tmp_path)
    assert len(calls) == 1


# --- real analyzers --------------------------------------------------------


def test_full_success_python_node(tmp_path):
    make_tree(tmp_path, PY_NODE)
    r = run_inspection(tmp_path)
    assert validate_report(r) == []
    assert r.status == S.COMPLETE
    assert [x.analyzer_name for x in r.analyzer_results] == [
        "dependency",
        "framework",
        "language",
        "tooling",
    ]
    subjects = {(f.category, f.subject) for f in r.findings}
    assert (C.LANGUAGE, "python") in subjects and (C.LANGUAGE, "javascript") in subjects
    assert r.summary.name == tmp_path.name and r.summary.origin == "external"
    assert r.summary.primary_language in {"python", "javascript"}
    assert r.structure.top_level_files == ("index.js", "package.json", "pyproject.toml")
    assert r.structure.top_level_directories == ("app", "tests")
    assert r.structure.file_count == 5 and r.structure.directory_count == 2
    keys = [(f.category.value, f.subject) for f in r.findings]
    assert keys == sorted(keys)


def test_empty_directory(tmp_path):
    r = run_inspection(tmp_path)
    assert r.status == S.COMPLETE and validate_report(r) == []
    assert r.summary.name == tmp_path.name
    assert all(f.detection_state == D.NOT_DETECTED for f in r.findings)
    assert r.summary.primary_language is None


def test_unknown_project(tmp_path):
    make_tree(tmp_path, {"notes.xyz": "hi"})
    r = run_inspection(tmp_path)
    assert r.summary.primary_language is None and r.summary.primary_framework is None


def test_polyglot_tie_break_by_subject(tmp_path):
    make_tree(tmp_path, {"a.py": "x=1\n", "b.js": "var x\n"})
    r = run_inspection(tmp_path)
    langs = {
        f.subject: len(f.evidence)
        for f in r.findings
        if f.category == C.LANGUAGE and f.detection_state == D.DETECTED
    }
    assert langs["python"] == langs["javascript"]
    assert r.summary.primary_language == "javascript"


def test_spawn_generated(tmp_path):
    meta = {"intent": "cli", "spawn_version": "9.9.9", "generator": "spawn"}
    make_tree(tmp_path, {".spawn/meta.json": json.dumps(meta), "main.py": "x=1\n"})
    r = run_inspection(tmp_path)
    assert r.summary.origin == "spawn" and r.summary.spawn_version == "9.9.9"
    assert r.recorded_metadata.intent == "cli"
    assert validate_report(r) == []


@pytest.mark.parametrize("kind", ["malformed", "oversized", "list"])
def test_meta_unreadable(tmp_path, kind):
    text = {"malformed": "{nope", "oversized": " " * 1_000_001, "list": "[]"}[kind]
    make_tree(tmp_path, {".spawn/meta.json": text})
    r = run_inspection(tmp_path)
    assert r.recorded_metadata is None and r.status == S.PARTIAL
    (d,) = [d for d in r.diagnostics if d.code == "orchestrator.meta_unreadable"]
    assert d.path == ".spawn/meta.json" and d.severity == "warning" and not d.fatal
    assert str(tmp_path) not in to_json(r)


def test_symlinked_meta_ignored(tmp_path):
    real = tmp_path / "real.json"
    real.write_text('{"spawn_version":"1"}')
    (tmp_path / ".spawn").mkdir()
    try:
        (tmp_path / ".spawn" / "meta.json").symlink_to(real)
    except OSError:
        pytest.skip("symlinks unavailable")
    r = run_inspection(tmp_path)
    assert r.recorded_metadata is None
    assert not [d for d in r.diagnostics if d.code == "orchestrator.meta_unreadable"]


def test_root_basename_empty_is_none(tmp_path, monkeypatch):
    class T:
        pass

    from spawn.inspection import InspectionTarget

    root = Path(tmp_path.anchor)
    monkeypatch.setattr(
        orch, "validate_inspection_root", lambda p: InspectionTarget(root)
    )
    monkeypatch.setattr(
        orch, "discover_repository", lambda t: orch.DiscoveryInventory((), (), (), ())
    )
    assert orch._inspect(root, []).summary.name is None


def test_read_only_and_deterministic(tmp_path):
    make_tree(tmp_path, PY_NODE)
    before = tree_hash(tmp_path)
    a, b = run_inspection(tmp_path), run_inspection(tmp_path)
    assert tree_hash(tmp_path) == before
    assert dumped(a) == dumped(b)


def test_json_roundtrip_and_no_abs_path(tmp_path):
    make_tree(tmp_path, PY_NODE)
    r = run_inspection(tmp_path)
    text = to_json(r)
    assert str(tmp_path) not in text and tmp_path.as_posix() not in text
    assert dumped(from_json(text)) == dumped(r)


def test_real_analyzer_alone_matches_pipeline(tmp_path):
    make_tree(tmp_path, PY_NODE)
    full = run_inspection(tmp_path)
    for a in orch.ANALYZERS:
        solo = orch._inspect(tmp_path, [a])
        assert [x.findings for x in solo.analyzer_results] == [
            x.findings for x in full.analyzer_results if x.analyzer_name == a.name
        ]


# --- isolation -------------------------------------------------------------


def test_crash_isolated(tmp_path):
    good = Fake("good", [fnd("keep")])
    r = inspect(
        tmp_path, [Fake("bad", raises=RuntimeError(f"secret {tmp_path}")), good]
    )
    bad = next(x for x in r.analyzer_results if x.analyzer_name == "bad")
    assert bad.status == S.FAILED and bad.findings == ()
    (d,) = bad.diagnostics
    assert (d.code, d.fatal, d.source, d.severity) == (
        "orchestrator.analyzer_crashed",
        True,
        "orchestrator",
        "error",
    )
    assert d.message == "Fake raised RuntimeError"
    assert [f.subject for f in r.findings] == ["keep"]
    assert r.status == S.PARTIAL and validate_report(r) == []


def test_failed_but_valid_result_keeps_findings(tmp_path):
    r = inspect(tmp_path, [Fake("a", [fnd("kept")], [diag(fatal=True)], S.FAILED)])
    assert r.analyzer_results[0].status == S.FAILED
    assert [f.subject for f in r.findings] == ["kept"]


class WrongType:
    name = "wt"

    def run(self, t, i):
        return "nope"


def test_invalid_results(tmp_path):
    r = inspect(tmp_path, [WrongType(), Fake("x")])
    x = {a.analyzer_name: a for a in r.analyzer_results}
    assert x["wt"].status == S.FAILED
    assert x["wt"].diagnostics[0].code == "orchestrator.invalid_analyzer_result"

    class Liar(Fake):
        def run(self, t, i):
            return AnalyzerResult("other", S.COMPLETE, (fnd("zz"),), ())

    r = inspect(tmp_path, [Liar("liar")])
    assert r.analyzer_results[0].status == S.FAILED and r.findings == ()
    assert (
        r.analyzer_results[0].diagnostics[0].code
        == "orchestrator.invalid_analyzer_result"
    )


def test_invalid_finding_dropped(tmp_path):
    bad = fnd("bad", D.DETECTED, ev=())
    r = inspect(tmp_path, [Fake("a", [bad, fnd("ok")])])
    assert [f.subject for f in r.findings] == ["ok"]
    (d,) = r.diagnostics
    assert d.code == "orchestrator.invalid_finding" and d.severity == "warning"
    assert "tool/bad" in d.message
    assert r.status == S.PARTIAL and validate_report(r) == []


# --- aggregation -----------------------------------------------------------

ORDER = [D.DETECTED, D.INFERRED, D.UNKNOWN, D.NOT_DETECTED, D.NOT_CHECKED]


def _state_finding(state):
    ev = () if state == D.NOT_CHECKED else (("p.txt", state.value, None),)
    return fnd("s", state, ev, detail=f"d-{state.value}")


@pytest.mark.parametrize("hi,lo", itertools.combinations(ORDER, 2))
def test_precedence_matrix(tmp_path, hi, lo):
    for order in ([hi, lo], [lo, hi]):
        r = inspect(
            tmp_path, [Fake(f"a{i}", [_state_finding(s)]) for i, s in enumerate(order)]
        )
        (f,) = r.findings
        assert f.detection_state == hi
        assert f.detail == f"d-{hi.value}"
        assert validate_report(r) == []


def test_evidence_merge_sorted_and_deduped(tmp_path):
    a = fnd("s", ev=(("b.txt", "i", None), ("a.txt", "z", None)))
    b = fnd("s", ev=(("a.txt", "z", None), ("a.txt", "y", "d")))
    r = inspect(tmp_path, [Fake("a", [a]), Fake("b", [b])])
    assert [(e.path, e.indicator, e.detail) for e in r.findings[0].evidence] == [
        ("a.txt", "y", "d"),
        ("a.txt", "z", None),
        ("b.txt", "i", None),
    ]


def test_detail_resolution(tmp_path):
    r = inspect(
        tmp_path,
        [
            Fake("a", [fnd("s", detail="zeta")]),
            Fake("b", [fnd("s", detail=None)]),
            Fake("c", [fnd("s", detail="alpha")]),
            Fake("d", [fnd("s", D.INFERRED, detail="ignored")]),
        ],
    )
    assert r.findings[0].detail == "alpha"


def test_inferred_winner_keeps_detail(tmp_path):
    r = inspect(
        tmp_path,
        [
            Fake("a", [fnd("s", D.INFERRED, detail="why")]),
            Fake("b", [fnd("s", D.UNKNOWN, ev=())]),
        ],
    )
    assert r.findings[0].detail == "why" and validate_report(r) == []


def test_findings_keep_analyzer_copy(tmp_path):
    r = inspect(
        tmp_path, [Fake("a", [fnd("s", D.UNKNOWN, ev=())]), Fake("b", [fnd("s")])]
    )
    by = {x.analyzer_name: x for x in r.analyzer_results}
    assert by["a"].findings[0].detection_state == D.UNKNOWN


def test_permuted_output_is_stable(tmp_path):
    fs = [fnd("b"), fnd("a"), fnd("a", cat=C.CI), fnd("c", cat=C.LANGUAGE)]
    ev = fnd("m", ev=(("z", "i", None), ("a", "i", None)))
    outs = set()
    for perm in itertools.permutations(fs):
        for names in (("x", "y"), ("y", "x")):
            r = inspect(
                tmp_path, [Fake(names[0], perm[:2]), Fake(names[1], perm[2:] + (ev,))]
            )
            d = dumped(r)
            d["analyzer_results"] = [x["analyzer_name"] for x in d["analyzer_results"]]
            outs.add(json.dumps(d["findings"]) + json.dumps(d["analyzer_results"]))
    assert len(outs) == 1


# --- status ----------------------------------------------------------------


@pytest.mark.parametrize(
    "given,diags,expected",
    [
        (S.COMPLETE, [], S.COMPLETE),
        (S.PARTIAL, [], S.COMPLETE),
        (S.FAILED, [], S.COMPLETE),
        (S.COMPLETE, [diag("info")], S.COMPLETE),
        (S.COMPLETE, [diag("warning")], S.PARTIAL),
        (S.COMPLETE, [diag("error")], S.PARTIAL),
        (S.COMPLETE, [diag("info", fatal=True)], S.FAILED),
        (S.COMPLETE, [diag("warning"), diag("error", fatal=True)], S.FAILED),
        (S.SKIPPED, [], S.SKIPPED),
    ],
)
def test_analyzer_status_table(tmp_path, given, diags, expected):
    r = inspect(tmp_path, [Fake("a", diagnostics=diags, status=given)])
    assert r.analyzer_results[0].status == expected
    exp_report = S.PARTIAL if expected in (S.PARTIAL, S.FAILED) else S.COMPLETE
    assert r.status == exp_report
    assert r.analyzer_results[0].diagnostics == tuple(diags)
    assert r.diagnostics == ()


def test_discovery_diagnostics_severity(tmp_path, monkeypatch):
    def inv(sev):
        d = Diagnostic("discovery.x", "m", sev, "discovery", "p")
        return orch.DiscoveryInventory((), (), (), (d,))

    monkeypatch.setattr(orch, "discover_repository", lambda t: inv("info"))
    assert orch._inspect(tmp_path, []).status == S.COMPLETE
    monkeypatch.setattr(orch, "discover_repository", lambda t: inv("warning"))
    r = orch._inspect(tmp_path, [])
    assert r.status == S.PARTIAL and len(r.diagnostics) == 1


def test_report_diagnostics_sorted(tmp_path, monkeypatch):
    ds = tuple(Diagnostic("c", "m", "info", "discovery", p) for p in ("z", "a", None))
    monkeypatch.setattr(
        orch, "discover_repository", lambda t: orch.DiscoveryInventory((), (), (), ds)
    )
    assert [d.path for d in orch._inspect(tmp_path, []).diagnostics] == [None, "a", "z"]
