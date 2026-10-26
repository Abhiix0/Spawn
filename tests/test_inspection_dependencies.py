"""Contract-level tests for dependency inspection (#56)."""

import ast
import hashlib
import json
import random
from dataclasses import replace
from pathlib import Path

import spawn.inspection._reading as reading_module
import spawn.inspection.dependencies as deps_module
from spawn.inspection.base import Analyzer
from spawn.inspection.dependencies import DependencyAnalyzer, parse_manifest
from spawn.inspection.discovery import discover_repository
from spawn.inspection.models import (
    AnalysisStatus,
    DetectionState,
    FindingCategory,
    InspectionReport,
    InspectionTarget,
    validate_report,
)


def write(root: Path, rel: str, text: str | bytes = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8", newline="")


def run(root: Path, inventory=None):
    target = InspectionTarget(root.resolve())
    return DependencyAnalyzer().run(target, inventory or discover_repository(target))


def deps(result):
    return {
        f.subject: f
        for f in result.findings
        if f.category is FindingCategory.DEPENDENCY
    }


def managers(result):
    return {
        f.subject: f
        for f in result.findings
        if f.category is FindingCategory.PACKAGE_MANAGER
    }


def codes(result):
    return [d.code for d in result.diagnostics]


# ---------------------------------------------------------------- success


def test_satisfies_analyzer_protocol():
    assert isinstance(DependencyAnalyzer(), Analyzer)
    assert DependencyAnalyzer.name == "dependency"


def test_empty_repo_is_complete_and_quiet(tmp_path):
    result = run(tmp_path)
    assert result.analyzer_name == "dependency"
    assert result.status is AnalysisStatus.COMPLETE
    assert result.findings == () and result.diagnostics == ()


def test_pyproject_all_supported_sections(tmp_path):
    write(
        tmp_path,
        "pyproject.toml",
        """
[project]
name = "x"
dependencies = ["fastapi[all]>=0.115.0", "Flask (>=2)", "numpy>=1; python_version>'3'"]
[project.optional-dependencies]
docs = ["Sphinx_RTD.theme==1"]
[dependency-groups]
dev = ["pytest>=8", {include-group = "docs"}]
[tool.poetry.dependencies]
python = "^3.12"
requests = "^2.0"
httpx = {version = ">=0.27", extras = ["http2"]}
[tool.poetry.dev-dependencies]
black = "*"
[tool.poetry.group.test.dependencies]
hypothesis = "^6"
[tool.uv]
dev-dependencies = ["ruff>=0.5"]
""",
    )
    result = run(tmp_path)
    assert result.status is AnalysisStatus.COMPLETE
    found = deps(result)
    assert set(found) == {
        "fastapi",
        "flask",
        "numpy",
        "sphinx-rtd-theme",
        "pytest",
        "requests",
        "httpx",
        "black",
        "hypothesis",
        "ruff",
    }
    assert "python" not in found
    ev = found["fastapi"].evidence[0]
    assert (ev.path, ev.indicator, ev.detail) == (
        "pyproject.toml",
        "fastapi in [project.dependencies]",
        ">=0.115.0",
    )
    assert found["flask"].evidence[0].detail == ">=2"
    assert found["numpy"].evidence[0].detail == ">=1"
    assert found["httpx"].evidence[0].detail == ">=0.27"
    assert (
        found["sphinx-rtd-theme"]
        .evidence[0]
        .indicator.endswith("[project.optional-dependencies.docs]")
    )
    assert found["pytest"].evidence[0].indicator.endswith("[dependency-groups.dev]")
    assert (
        found["hypothesis"]
        .evidence[0]
        .indicator.endswith("[tool.poetry.group.test.dependencies]")
    )
    assert found["ruff"].evidence[0].indicator.endswith("[tool.uv.dev-dependencies]")
    assert set(managers(result)) == {"poetry", "uv"}
    assert all(
        f.detection_state is DetectionState.DETECTED for f in managers(result).values()
    )
    assert all(f.detail is None for f in found.values())


def test_package_json_sections_and_normalization(tmp_path):
    write(
        tmp_path,
        "package.json",
        json.dumps(
            {
                "dependencies": {"React": "^18.2.0", "@Types/Node": "20"},
                "devDependencies": {"vite": "^5"},
                "peerDependencies": {"react-dom": "*"},
                "optionalDependencies": {"fsevents": "2"},
            }
        ),
    )
    result = run(tmp_path)
    found = deps(result)
    assert set(found) == {"react", "@types/node", "vite", "react-dom", "fsevents"}
    ev = found["vite"].evidence[0]
    assert ev.indicator == "vite in package.json devDependencies"
    assert ev.detail == "^5"
    assert managers(result) == {}  # package.json alone names no manager


def test_requirements_syntax(tmp_path):
    write(
        tmp_path,
        "requirements.txt",
        "﻿# comment\r\n"
        "numpy>=1.0  # inline\r\n"
        "-r base.txt\r\n"
        "--index-url https://u:secret@pypi.example/simple\r\n"
        "-e .\r\n"
        ".\r\n"
        "-e git+https://u:tok@host/x.git#egg=Editable_Pkg\r\n"
        "https://u:tok@host/y.tar.gz#egg=urlpkg\r\n"
        "pinned==1.0 \\\r\n    --hash=sha256:aa \\\r\n    --hash=sha256:bb\r\n"
        "pkg @ git+https://user:token@host/x.git\r\n"
        "Pkg_B[extra] ; python_version < '3.9'\r\n",
    )
    result = run(tmp_path)
    assert result.status is AnalysisStatus.COMPLETE
    found = deps(result)
    assert set(found) == {"numpy", "editable-pkg", "urlpkg", "pinned", "pkg", "pkg-b"}
    assert found["numpy"].evidence[0].indicator == "numpy in requirements.txt"
    assert found["pinned"].evidence[0].detail == "==1.0"
    assert found["pkg"].evidence[0].detail == "git+https://host/x.git"
    blob = repr(result)
    assert "token" not in blob and "secret" not in blob and "tok@" not in blob
    pip = managers(result)["pip"]
    assert pip.detection_state is DetectionState.INFERRED
    assert "not confirmed" in pip.detail


def test_detail_truncated_to_200(tmp_path):
    write(tmp_path, "requirements.txt", "pkg==" + "1" * 500 + "\n")
    assert len(deps(run(tmp_path))["pkg"].evidence[0].detail) == 200


def test_pep503_normalization():
    cases = {
        "Foo_Bar": "foo-bar",
        "a..b__c--d": "a-b-c-d",
        "Zope.Interface": "zope-interface",
    }
    for raw, expected in cases.items():
        parsed = parse_manifest("requirements.txt", f"{raw}==1\n")
        assert parsed.declarations[0].subject == expected


def test_same_dependency_merges_into_one_finding(tmp_path):
    write(
        tmp_path,
        "pyproject.toml",
        '[project]\ndependencies=["pytest>=8"]\n[dependency-groups]\ndev=["PyTest>=8.1"]\n',
    )
    write(tmp_path, "tests/requirements-test.txt", "pytest\n")
    found = deps(run(tmp_path))
    assert list(found) == ["pytest"]
    assert [(e.path, e.detail) for e in found["pytest"].evidence] == [
        ("pyproject.toml", ">=8.1"),  # [dependency-groups] sorts before [project]
        ("pyproject.toml", ">=8"),
        ("tests/requirements-test.txt", None),
    ]


def test_monorepo_with_ecosystem_collision(tmp_path):
    write(tmp_path, "api/requirements.txt", "redis==5\n")
    write(tmp_path, "web/package.json", '{"dependencies": {"redis": "^4"}}')
    result = run(tmp_path)
    assert [e.path for e in deps(result)["redis"].evidence] == [
        "api/requirements.txt",
        "web/package.json",
    ]


def test_package_manager_detection_table(tmp_path):
    for name in (
        "uv.lock",
        "poetry.lock",
        "Pipfile",
        "package-lock.json",
        "yarn.lock",
        "pnpm-workspace.yaml",
        "bun.lockb",
    ):
        write(tmp_path, name, "not parsed {{{")
    found = managers(run(tmp_path))
    assert set(found) == {"uv", "poetry", "pipenv", "npm", "yarn", "pnpm", "bun"}
    assert all(f.detection_state is DetectionState.DETECTED for f in found.values())
    assert found["pipenv"].evidence[0].path == "Pipfile"


def test_lockfiles_never_give_dependencies(tmp_path):
    write(tmp_path, "poetry.lock", '[[package]]\nname = "requests"\n')
    write(tmp_path, "Pipfile", '[packages]\nrequests = "*"\n')
    result = run(tmp_path)
    assert deps(result) == {}
    assert result.status is AnalysisStatus.COMPLETE


def test_package_manager_field_beats_stray_lockfile_without_winner(tmp_path):
    write(tmp_path, "package.json", '{"packageManager": "pnpm@9.1.0+sha1.abc"}')
    write(tmp_path, "package-lock.json", "{}")
    write(tmp_path, "yarn.lock", "")
    assert set(managers(run(tmp_path))) == {"pnpm", "npm", "yarn"}


def test_unknown_package_manager_field_ignored(tmp_path):
    write(tmp_path, "package.json", '{"packageManager": "deno@1"}')
    assert managers(run(tmp_path)) == {}


def test_pyproject_with_only_tool_ruff(tmp_path):
    write(tmp_path, "pyproject.toml", "[tool.ruff]\nline-length = 88\n")
    result = run(tmp_path)
    assert result.findings == () and result.status is AnalysisStatus.COMPLETE


# ---------------------------------------------------------------- failure


def test_malformed_manifests_do_not_block_others(tmp_path):
    write(tmp_path, "pyproject.toml", "[project\nbroken")
    write(tmp_path, "package.json", "{not json")
    write(tmp_path, "web/package.json", "[1, 2]")
    write(tmp_path, "requirements.txt", "ok==1\n")
    result = run(tmp_path)
    assert result.status is AnalysisStatus.PARTIAL
    assert codes(result) == ["dependency.malformed_manifest"] * 3
    assert {d.path for d in result.diagnostics} == {
        "pyproject.toml",
        "package.json",
        "web/package.json",
    }
    assert set(deps(result)) == {"ok"}


def test_package_json_bad_section_values(tmp_path):
    write(
        tmp_path,
        "package.json",
        '{"dependencies": null, "devDependencies": ["x"], "peerDependencies": {"ok": 1}}',
    )
    result = run(tmp_path)
    assert set(deps(result)) == {"ok"}
    assert deps(result)["ok"].evidence[0].detail is None
    assert codes(result) == ["dependency.malformed_manifest"]


def test_non_utf8_and_utf16_are_undecodable(tmp_path):
    write(tmp_path, "requirements.txt", "numpy==1\n".encode("utf-16"))
    write(tmp_path, "a/requirements.txt", b"caf\xe9==1\n")
    result = run(tmp_path)
    assert codes(result) == ["dependency.undecodable_file"] * 2
    assert result.status is AnalysisStatus.PARTIAL
    assert deps(result) == {}


def test_unreadable_file_listed_in_inventory(tmp_path):
    write(tmp_path, "package.json", "{}")
    inv = replace(
        discover_repository(InspectionTarget(tmp_path.resolve())),
        files=("package.json", "requirements.txt"),
    )
    result = run(tmp_path, inv)
    assert codes(result) == ["dependency.unreadable_file"]
    assert result.diagnostics[0].path == "requirements.txt"
    assert result.status is AnalysisStatus.PARTIAL


def test_dynamic_metadata_warns_without_guessing(tmp_path):
    write(
        tmp_path,
        "pyproject.toml",
        '[project]\nname="x"\ndynamic=["dependencies"]\n',
    )
    result = run(tmp_path)
    assert deps(result) == {}
    assert codes(result) == ["dependency.dynamic_metadata"]
    assert result.status is AnalysisStatus.PARTIAL


def test_unsupported_syntax_is_one_aggregated_count_only_warning(tmp_path):
    write(
        tmp_path,
        "requirements.txt",
        "ok==1\nhttps://host/a.whl\n-e git+https://u:tok@host/x.git\n@@@\n",
    )
    result = run(tmp_path)
    assert set(deps(result)) == {"ok"}
    assert codes(result) == ["dependency.unsupported_syntax"]
    message = result.diagnostics[0].message
    assert "3" in message and "host" not in message and "tok" not in message


def test_manifest_cap(tmp_path):
    for i in range(502):
        write(tmp_path, f"p{i:04d}/requirements.txt", f"pkg{i}==1\n")
    result = run(tmp_path)
    assert codes(result) == ["dependency.manifest_limit_reached"]
    assert len(deps(result)) == 500
    assert "pkg499" in deps(result) and "pkg500" not in deps(result)


def test_internal_error_returns_fatal_failed(tmp_path, monkeypatch):
    write(tmp_path, "uv.lock", "")
    write(tmp_path, "requirements.txt", "a==1\n")

    def boom(*args):
        raise RuntimeError(str(tmp_path))

    monkeypatch.setattr(deps_module, "parse_manifest", boom)
    result = run(tmp_path)
    assert result.status is AnalysisStatus.FAILED
    assert result.diagnostics[0].code == "dependency.internal_error"
    assert result.diagnostics[0].fatal
    assert str(tmp_path) not in repr(result)
    assert set(managers(result)) == {"uv"}


# ---------------------------------------------------------------- boundaries


def _padded_requirements(size: int) -> bytes:
    line = b"pkg==1\n"
    return line + b"#" * (size - len(line))


def test_size_boundary(tmp_path):
    write(tmp_path, "ok/requirements.txt", _padded_requirements(1_000_000))
    write(tmp_path, "big/requirements.txt", _padded_requirements(1_000_001))
    result = run(tmp_path)
    assert [(d.code, d.path) for d in result.diagnostics] == [
        ("dependency.file_too_large", "big/requirements.txt")
    ]
    assert [e.path for e in deps(result)["pkg"].evidence] == ["ok/requirements.txt"]


def test_read_is_bounded_to_limit_plus_one(tmp_path):
    write(tmp_path, "f.txt", b"x" * 50)
    seen = []
    real_open = Path.open

    class Spy:
        def __init__(self, fh):
            self.fh = fh

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.fh.close()

        def read(self, n=-1):
            seen.append(n)
            return self.fh.read(n)

    Path.open = lambda self, *a, **k: Spy(real_open(self, *a, **k))
    try:
        assert reading_module.read_text_limited(tmp_path / "f.txt", 10) is None
    finally:
        Path.open = real_open
    assert seen == [11]


def test_empty_files_are_quiet(tmp_path):
    write(tmp_path, "pyproject.toml", "")
    write(tmp_path, "package.json", "  \n")
    write(tmp_path, "requirements.txt", "")
    result = run(tmp_path)
    assert result.status is AnalysisStatus.COMPLETE
    assert deps(result) == {}
    assert set(managers(result)) == {"pip"}


# ---------------------------------------------------------------- determinism


def _tree(root: Path) -> None:
    write(root, "pyproject.toml", '[project]\ndependencies=["b>=1","a"]\n[tool.uv]\n')
    write(root, "requirements-dev.txt", "a==2\nc\n")
    write(root, "app/package.json", '{"dependencies":{"z":"1","y":"2"}}')
    write(root, "yarn.lock", "")


def test_deterministic_and_inventory_order_independent(tmp_path):
    _tree(tmp_path)
    target = InspectionTarget(tmp_path.resolve())
    inv = discover_repository(target)
    first = DependencyAnalyzer().run(target, inv)
    assert first == DependencyAnalyzer().run(target, inv)
    files = list(inv.files)
    random.Random(7).shuffle(files)
    assert first == DependencyAnalyzer().run(target, replace(inv, files=tuple(files)))
    assert [(f.category.value, f.subject) for f in first.findings] == sorted(
        (f.category.value, f.subject) for f in first.findings
    )
    for f in first.findings:
        keys = [(e.path, e.indicator, e.detail or "") for e in f.evidence]
        assert keys == sorted(keys)


def test_no_absolute_path_in_output(tmp_path):
    _tree(tmp_path)
    write(tmp_path, "bad/pyproject.toml", "[x")
    write(tmp_path, "bad/requirements.txt", b"\xff\xfe")
    result = run(tmp_path)
    assert result.diagnostics
    blob = repr(result)
    assert str(tmp_path) not in blob and tmp_path.as_posix() not in blob


def test_report_validates(tmp_path):
    _tree(tmp_path)
    write(tmp_path, "bad/pyproject.toml", "[x")
    result = run(tmp_path)
    report = InspectionReport(
        target=InspectionTarget(tmp_path.resolve()),
        findings=result.findings,
        analyzer_results=(result,),
        diagnostics=result.diagnostics,
    )
    assert validate_report(report) == []


# ---------------------------------------------------------------- read-only


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_read_only(tmp_path):
    _tree(tmp_path)
    before = _hash_tree(tmp_path)
    run(tmp_path)
    assert _hash_tree(tmp_path) == before


def test_file_absent_from_inventory_is_never_read(tmp_path):
    write(tmp_path, "requirements.txt", "listed==1\n")
    write(tmp_path, "hidden/requirements.txt", "hidden==1\n")
    write(tmp_path, "uv.lock", "")
    inv = replace(
        discover_repository(InspectionTarget(tmp_path.resolve())),
        files=("requirements.txt",),
    )
    result = run(tmp_path, inv)
    assert set(deps(result)) == {"listed"}
    assert "uv" not in managers(result)


def test_modules_are_static_and_traversal_free():
    banned_imports = {"subprocess", "socket", "urllib", "http", "requests", "shutil"}
    banned_calls = {"walk", "glob", "rglob", "iterdir", "scandir"}
    for module in (deps_module, reading_module):
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names = {(node.module or "").split(".")[0]}
            else:
                names = set()
            assert not names & banned_imports, module.__name__
            if isinstance(node, ast.Call):
                func = node.func
                called = (
                    func.attr
                    if isinstance(func, ast.Attribute)
                    else getattr(func, "id", "")
                )
                assert called not in banned_calls, module.__name__
