"""Contract-level tests for tooling inspection (#57)."""

import ast
import hashlib
import random
from dataclasses import replace
from pathlib import Path

import pytest

import spawn.inspection.tooling as tooling_module
from spawn.inspection.base import Analyzer
from spawn.inspection.discovery import discover_repository
from spawn.inspection.models import (
    AnalysisStatus,
    DetectionState,
    FindingCategory,
    InspectionReport,
    InspectionTarget,
    validate_report,
)
from spawn.inspection.tooling import ToolingAnalyzer

D, INF, U, N, NC = (
    DetectionState.DETECTED,
    DetectionState.INFERRED,
    DetectionState.UNKNOWN,
    DetectionState.NOT_DETECTED,
    DetectionState.NOT_CHECKED,
)
C = FindingCategory
HEADLINES = {
    (C.TOOL, "git"),
    (C.TOOL, "pytest"),
    (C.TOOL, "ruff"),
    (C.CI, "github-actions"),
    (C.CONTAINER, "docker"),
    (C.STRUCTURE, "tests-directory"),
}


def write(root: Path, rel: str, text: str | bytes = "") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8", newline="")


def run(root: Path, inventory=None):
    target = InspectionTarget(root.resolve())
    return ToolingAnalyzer().run(target, inventory or discover_repository(target))


def by(result):
    return {(f.category, f.subject): f for f in result.findings}


def state(result, cat, subject):
    f = by(result).get((cat, subject))
    return f.detection_state if f else None


def codes(result):
    return [d.code for d in result.diagnostics]


# ---------------------------------------------------------------- basics


def test_protocol_and_name():
    assert isinstance(ToolingAnalyzer(), Analyzer)
    assert ToolingAnalyzer.name == "tooling"


def test_empty_repo_only_headline_negatives(tmp_path):
    result = run(tmp_path)
    assert result.status is AnalysisStatus.COMPLETE and result.diagnostics == ()
    assert set(by(result)) == HEADLINES
    for f in result.findings:
        assert f.detection_state is N and f.evidence == () and f.detail
    assert "pytest.ini" in by(result)[(C.TOOL, "pytest")].detail


def test_unrelated_files_only_negatives(tmp_path):
    write(tmp_path, "README.md", "uses postgres and docker and pytest")
    write(tmp_path, "notes.txt", "x")
    write(tmp_path, ".env", "DATABASE_URL=postgres://x")
    assert set(by(run(tmp_path))) == HEADLINES


# ---------------------------------------------------------------- matrix

# (category, subject, files{path: content}) -> must be DETECTED
POSITIVE = [
    (C.TOOL, "ruff", {"ruff.toml": ""}),
    (C.TOOL, "ruff", {"sub/.ruff.toml": ""}),
    (C.TOOL, "ruff", {"pyproject.toml": "[tool.ruff]\n"}),
    (C.TOOL, "black", {"pyproject.toml": "[tool.black]\nline-length=88\n"}),
    (C.TOOL, "flake8", {".flake8": ""}),
    (C.TOOL, "flake8", {"setup.cfg": "[flake8]\nmax-line-length=99\n"}),
    (C.TOOL, "flake8", {"tox.ini": "[flake8]\nignore=E1\n"}),
    (C.TOOL, "mypy", {"mypy.ini": ""}),
    (C.TOOL, "mypy", {".mypy.ini": ""}),
    (C.TOOL, "mypy", {"pyproject.toml": "[tool.mypy]\nstrict=true\n"}),
    (C.TOOL, "mypy", {"setup.cfg": "[mypy]\nstrict=True\n"}),
    (C.TOOL, "pyright", {"pyrightconfig.json": "{}"}),
    (C.TOOL, "pyright", {"pyproject.toml": "[tool.pyright]\n"}),
    (C.TOOL, "pytest", {"pytest.ini": "[pytest]\n"}),
    (C.TOOL, "pytest", {"pyproject.toml": "[tool.pytest.ini_options]\naddopts=''\n"}),
    (C.TOOL, "pytest", {"setup.cfg": "[tool:pytest]\naddopts=-q\n"}),
    (C.TOOL, "pytest", {"tox.ini": "[pytest]\naddopts=-q\n"}),
    (C.TOOL, "eslint", {".eslintrc": "{}"}),
    (C.TOOL, "eslint", {"web/.eslintrc.cjs": ""}),
    (C.TOOL, "eslint", {"eslint.config.mjs": ""}),
    (C.TOOL, "eslint", {"package.json": '{"eslintConfig": {}}'}),
    (C.TOOL, "prettier", {".prettierrc": "{}"}),
    (C.TOOL, "prettier", {".prettierrc.toml": ""}),
    (C.TOOL, "prettier", {"prettier.config.js": ""}),
    (C.TOOL, "prettier", {"package.json": '{"prettier": {}}'}),
    (C.TOOL, "jest", {"jest.config.ts": ""}),
    (C.TOOL, "jest", {"package.json": '{"jest": {}}'}),
    (C.TOOL, "vitest", {"vitest.config.mjs": ""}),
    (C.TOOL, "pre-commit", {".pre-commit-config.yaml": "repos: []\n"}),
    (C.TOOL, "git", {".git": ""}),
    (C.CI, "github-actions", {".github/workflows/ci.yml": "x"}),
    (C.CI, "github-actions", {".github/workflows/release.yaml": "x"}),
    (C.CI, "gitlab-ci", {".gitlab-ci.yml": ""}),
    (C.CI, "circleci", {".circleci/config.yml": ""}),
    (C.CI, "jenkins", {"Jenkinsfile": ""}),
    (C.CI, "azure-pipelines", {"azure-pipelines.yml": ""}),
    (C.CONTAINER, "docker", {"Dockerfile": ""}),
    (C.CONTAINER, "docker", {"svc/Dockerfile.dev": ""}),
    (C.CONTAINER, "docker", {"api.Dockerfile": ""}),
    (C.CONTAINER, "docker-compose", {"docker-compose.yml": ""}),
    (C.CONTAINER, "docker-compose", {"deploy/compose.yaml": ""}),
    (C.STRUCTURE, "tests-directory", {"tests/test_a.py": ""}),
    (C.STRUCTURE, "tests-directory", {"__tests__/a.js": ""}),
    (C.STRUCTURE, "tests-directory", {"test/a.py": ""}),
    (C.STRUCTURE, "src-layout", {"src/pkg/__init__.py": ""}),
    (C.STRUCTURE, "spawn-generated", {".spawn/meta.json": "{}"}),
]


@pytest.mark.parametrize(("cat", "subject", "files"), POSITIVE)
def test_positive(tmp_path, cat, subject, files):
    for rel, text in files.items():
        write(tmp_path, rel, text)
    result = run(tmp_path)
    finding = by(result)[(cat, subject)]
    assert finding.detection_state is D
    assert finding.evidence
    assert all(not e.path.startswith("/") for e in finding.evidence)


# (category, subject, files) -> must NOT be DETECTED
NEGATIVE = [
    (C.TOOL, "ruff", {"ruff.txt": "", "pyproject.toml": "[tool.black]\n"}),
    (C.TOOL, "black", {"pyproject.toml": "[tool.ruff]\n"}),
    (C.TOOL, "flake8", {"setup.cfg": "[metadata]\nname=x\n"}),
    (C.TOOL, "mypy", {"pyproject.toml": "[tool.mypyx]\n"}),
    (C.TOOL, "pyright", {"pyproject.toml": "[tool.pytest]\n"}),
    (C.TOOL, "pytest", {"pyproject.toml": "[tool.pytest]\nx=1\n"}),
    (C.TOOL, "eslint", {"package.json": "{}"}),
    (C.TOOL, "prettier", {"package.json": '{"name":"x"}'}),
    (C.TOOL, "jest", {"jest.config.py": ""}),
    (C.TOOL, "vitest", {"vitest.config.json": ""}),
    (C.TOOL, "pre-commit", {".pre-commit-config.yml": ""}),
    (C.CI, "github-actions", {".github/workflows/notes.txt": ""}),
    (C.CI, "github-actions", {"sub/.github/workflows/ci.yml": ""}),
    (C.CI, "gitlab-ci", {"sub/.gitlab-ci.yml": ""}),
    (C.CI, "circleci", {"x/.circleci/config.yml": ""}),
    (C.CI, "jenkins", {"sub/Jenkinsfile": ""}),
    (C.CI, "azure-pipelines", {"azure-pipelines.yaml": ""}),
    (C.CONTAINER, "docker", {"Dockerfileish": "", "dockerfile": ""}),
    (C.CONTAINER, "docker-compose", {"docker-compose.json": ""}),
    (C.STRUCTURE, "tests-directory", {"src/tests/a.py": ""}),
    (C.STRUCTURE, "tests-directory", {"testing/a.py": ""}),
    (C.STRUCTURE, "src-layout", {"src/loose.py": ""}),
    (C.STRUCTURE, "src-layout", {"app/src/pkg/__init__.py": ""}),
    (C.STRUCTURE, "spawn-generated", {"meta.json": "{}"}),
]


@pytest.mark.parametrize(("cat", "subject", "files"), NEGATIVE)
def test_negative(tmp_path, cat, subject, files):
    for rel, text in files.items():
        write(tmp_path, rel, text)
    assert state(run(tmp_path), cat, subject) in (None, N)


@pytest.mark.parametrize(
    ("tool", "dep_file", "text"),
    [
        ("ruff", "pyproject.toml", '[project]\ndependencies=["ruff>=0.5"]\n'),
        ("black", "requirements.txt", "black==24\n"),
        ("flake8", "requirements-dev.txt", "flake8\n"),
        ("mypy", "pyproject.toml", '[dependency-groups]\ndev=["mypy"]\n'),
        ("pyright", "package.json", '{"devDependencies":{"pyright":"1"}}'),
        ("pytest", "requirements.txt", "pytest>=8\n"),
        ("eslint", "package.json", '{"devDependencies":{"eslint":"9"}}'),
        ("prettier", "package.json", '{"devDependencies":{"prettier":"3"}}'),
        ("jest", "package.json", '{"devDependencies":{"jest":"29"}}'),
        ("vitest", "package.json", '{"devDependencies":{"vitest":"2"}}'),
        ("pre-commit", "requirements.txt", "pre-commit\n"),
    ],
)
def test_dependency_without_config_is_inferred_with_detail(
    tmp_path, tool, dep_file, text
):
    write(tmp_path, dep_file, text)
    f = by(run(tmp_path))[(C.TOOL, tool)]
    assert f.detection_state is INF
    assert f.detail == "declared as a dependency but no configuration found"
    assert f.evidence[0].path == dep_file


def test_config_without_dependency_is_detected(tmp_path):
    write(tmp_path, "pyproject.toml", '[project]\nname="x"\n[tool.ruff]\n')
    assert state(run(tmp_path), C.TOOL, "ruff") is D


def test_config_beats_dependency(tmp_path):
    write(tmp_path, "pyproject.toml", '[project]\ndependencies=["ruff"]\n[tool.ruff]\n')
    f = by(run(tmp_path))[(C.TOOL, "ruff")]
    assert f.detection_state is D
    assert {e.indicator for e in f.evidence} == {"[tool.ruff] section"}


@pytest.mark.parametrize(
    ("db", "pkg_file", "text"),
    [
        ("postgres", "requirements.txt", "psycopg2-binary\n"),
        ("postgres", "package.json", '{"dependencies":{"pg":"8"}}'),
        ("mysql", "requirements.txt", "PyMySQL\n"),
        ("mysql", "package.json", '{"dependencies":{"mysql2":"3"}}'),
        ("mongodb", "requirements.txt", "motor\n"),
        ("mongodb", "package.json", '{"dependencies":{"mongoose":"8"}}'),
        ("redis", "requirements.txt", "redis\n"),
        ("redis", "package.json", '{"dependencies":{"ioredis":"5"}}'),
        ("sqlite", "requirements.txt", "aiosqlite\n"),
        ("sqlite", "package.json", '{"dependencies":{"better-sqlite3":"9"}}'),
    ],
)
def test_database_inferred_from_driver(tmp_path, db, pkg_file, text):
    write(tmp_path, pkg_file, text)
    f = by(run(tmp_path))[(C.DATABASE, db)]
    assert f.detection_state is INF and f.evidence
    assert (
        f.detail == "database driver declared; actual use and connectivity not verified"
    )


def test_database_not_inferred_from_prose_env_or_compose(tmp_path):
    write(tmp_path, "README.md", "postgres redis mongodb")
    write(tmp_path, ".env", "REDIS_URL=redis://x")
    write(tmp_path, "docker-compose.yml", "services:\n  db:\n    image: postgres\n")
    write(tmp_path, "data.sqlite", "x")
    assert not [k for k in by(run(tmp_path)) if k[0] is C.DATABASE]


# ---------------------------------------------------------------- git


def test_git_detected_via_skipped_dir(tmp_path):
    write(tmp_path, ".git/HEAD", "ref: refs/heads/main")
    inv = discover_repository(InspectionTarget(tmp_path.resolve()))
    assert ".git" in inv.skipped and ".git" not in inv.directories
    f = by(run(tmp_path, inv))[(C.TOOL, "git")]
    assert f.detection_state is D and f.evidence[0].path == ".git"


def test_git_file_instead_of_directory(tmp_path):
    write(tmp_path, ".git", "gitdir: ../elsewhere")
    assert state(run(tmp_path), C.TOOL, "git") is D


def test_git_inferred_from_gitignore_only(tmp_path):
    write(tmp_path, ".gitignore", "*.pyc")
    f = by(run(tmp_path))[(C.TOOL, "git")]
    assert f.detection_state is INF and f.detail and f.evidence[0].path == ".gitignore"


def test_nested_gitignore_is_not_git_evidence(tmp_path):
    write(tmp_path, "sub/.gitignore", "x")
    assert state(run(tmp_path), C.TOOL, "git") is N


def test_git_symlink_appears_in_skipped(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    root = tmp_path / "repo"
    root.mkdir()
    try:
        (root / ".git").symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    inv = discover_repository(InspectionTarget(root.resolve()))
    assert ".git" in inv.skipped
    assert state(run(root, inv), C.TOOL, "git") is D


# ---------------------------------------------------------------- CI / containers


def test_multiple_ci_and_container_files(tmp_path):
    for rel in (
        ".github/workflows/a.yml",
        ".github/workflows/b.yaml",
        ".github/workflows/sub/c.yml",
        "Dockerfile",
        "svc/Dockerfile",
        "svc/docker-compose.yml",
        "compose.yaml",
    ):
        write(tmp_path, rel)
    found = by(run(tmp_path))
    assert [e.path for e in found[(C.CI, "github-actions")].evidence] == [
        ".github/workflows/a.yml",
        ".github/workflows/b.yaml",
    ]
    assert [e.path for e in found[(C.CONTAINER, "docker")].evidence] == [
        "Dockerfile",
        "svc/Dockerfile",
    ]
    assert [e.path for e in found[(C.CONTAINER, "docker-compose")].evidence] == [
        "compose.yaml",
        "svc/docker-compose.yml",
    ]


def test_dockerignore_only_is_inferred(tmp_path):
    write(tmp_path, ".dockerignore", "node_modules")
    f = by(run(tmp_path))[(C.CONTAINER, "docker")]
    assert f.detection_state is INF and f.detail


def test_ci_content_is_never_parsed(tmp_path):
    write(tmp_path, ".github/workflows/ci.yml", "\xff not yaml: [")
    write(tmp_path, ".github/workflows/big.yml", b"\xff" * 2_000_000)
    result = run(tmp_path)
    assert state(result, C.CI, "github-actions") is D
    assert result.diagnostics == ()


# ---------------------------------------------------------------- structure / spawn


def test_spawn_metadata_is_marker_only_even_if_stale(tmp_path):
    write(
        tmp_path,
        ".spawn/meta.json",
        '{"intent":"backend_api","framework":"flask","spawn_version":"9"}',
    )
    write(tmp_path, "requirements.txt", "fastapi\n")
    result = run(tmp_path)
    f = by(result)[(C.STRUCTURE, "spawn-generated")]
    assert f.detection_state is D and f.detail is None
    assert result.diagnostics == ()
    assert "flask" not in repr(result).lower()
    assert not [k for k in by(result) if k[1] in ("flask", "backend_api")]


def test_spawn_metadata_missing(tmp_path):
    assert state(run(tmp_path), C.STRUCTURE, "spawn-generated") is None


@pytest.mark.parametrize("content", ["{bad", "[1, 2]", "null", b"\xff\xfe", ""])
def test_spawn_metadata_unusable_is_inferred_with_warning(tmp_path, content):
    write(tmp_path, ".spawn/meta.json", content)
    result = run(tmp_path)
    f = by(result)[(C.STRUCTURE, "spawn-generated")]
    assert f.detection_state is INF and f.detail and f.evidence
    assert codes(result) == ["tooling.malformed_metadata"]
    assert result.status is AnalysisStatus.PARTIAL


# ---------------------------------------------------------------- broken manifests


def test_malformed_pyproject_makes_headline_absence_unknown(tmp_path):
    write(tmp_path, "pyproject.toml", "[x")
    write(tmp_path, "Dockerfile")
    write(tmp_path, "package.json", '{"eslintConfig": {}}')
    result = run(tmp_path)
    found = by(result)
    for subject in ("ruff", "pytest"):
        f = found[(C.TOOL, subject)]
        assert f.detection_state is U and "pyproject.toml" in f.detail
    assert state(result, C.CONTAINER, "docker") is D
    assert state(result, C.TOOL, "eslint") is D  # unrelated detection survives
    assert state(result, C.STRUCTURE, "tests-directory") is N
    assert codes(result) == ["tooling.malformed_manifest"]
    assert result.status is AnalysisStatus.PARTIAL


def test_malformed_setup_cfg_and_other_detections(tmp_path):
    write(tmp_path, "setup.cfg", "no section header\n")
    write(tmp_path, "ruff.toml")
    result = run(tmp_path)
    assert state(result, C.TOOL, "ruff") is D
    f = by(result)[(C.TOOL, "pytest")]
    assert f.detection_state is U and "setup.cfg" in f.detail
    assert codes(result) == ["tooling.malformed_manifest"]


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"\xff\xfe\x00", "tooling.undecodable_file"),
        (b"#" * 1_000_001, "tooling.file_too_large"),
    ],
    ids=["undecodable", "too_large"],
)
def test_unreadable_manifest_diagnostics(tmp_path, content, code):
    write(tmp_path, "requirements.txt", content)
    result = run(tmp_path)
    assert codes(result) == [code]
    assert state(result, C.TOOL, "pytest") is U


def test_malformed_package_json_non_object(tmp_path):
    write(tmp_path, "package.json", "[1]")
    result = run(tmp_path)
    assert codes(result) == ["tooling.malformed_manifest"]
    assert state(result, C.TOOL, "ruff") is U


def test_manifest_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(tooling_module, "MAX_MANIFESTS", 2)
    for i in range(4):
        write(tmp_path, f"p{i}/package.json", "{}")
    write(tmp_path, "ruff.toml")
    result = run(tmp_path)
    assert codes(result) == ["tooling.manifest_limit_reached"]
    assert state(result, C.TOOL, "ruff") is D
    f = by(result)[(C.TOOL, "pytest")]
    assert f.detection_state is U and "manifests" in f.detail
    assert state(result, C.CONTAINER, "docker") is N


def test_internal_error_returns_not_checked(tmp_path, monkeypatch):
    write(tmp_path, "Dockerfile")

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(tooling_module, "_load", boom)
    write(tmp_path, "package.json", "{}")
    result = run(tmp_path)
    assert result.status is AnalysisStatus.FAILED
    assert codes(result) == ["tooling.internal_error"]
    found = by(result)
    assert found[(C.CONTAINER, "docker")].detection_state is D  # accumulated
    assert found[(C.TOOL, "pytest")].detection_state is NC
    assert found[(C.TOOL, "pytest")].evidence == ()


# ---------------------------------------------------------------- monorepo / polyglot


def test_monorepo_polyglot(tmp_path):
    write(
        tmp_path, "pyproject.toml", '[project]\ndependencies=["psycopg"]\n[tool.ruff]\n'
    )
    write(
        tmp_path, "web/package.json", '{"devDependencies":{"jest":"29"},"prettier":{}}'
    )
    write(tmp_path, "api/Dockerfile")
    write(tmp_path, "worker/Dockerfile")
    write(tmp_path, "web/.eslintrc.json", "{}")
    result = run(tmp_path)
    found = by(result)
    assert found[(C.TOOL, "jest")].detection_state is INF
    assert found[(C.TOOL, "prettier")].detection_state is D
    assert found[(C.TOOL, "eslint")].evidence[0].path == "web/.eslintrc.json"
    assert len(found[(C.CONTAINER, "docker")].evidence) == 2
    assert found[(C.DATABASE, "postgres")].detection_state is INF
    assert result.status is AnalysisStatus.COMPLETE


# ---------------------------------------------------------------- invariants


def _tree(root: Path) -> None:
    write(
        root,
        "pyproject.toml",
        '[project]\ndependencies=["redis","pytest"]\n[tool.ruff]\n',
    )
    write(root, "app/package.json", '{"devDependencies":{"eslint":"9"}}')
    write(root, ".github/workflows/ci.yml")
    write(root, "Dockerfile")
    write(root, "tests/test_a.py")
    write(root, "src/pkg/__init__.py")
    write(root, ".spawn/meta.json", "{}")
    write(root, ".git/HEAD", "x")


def test_deterministic_and_order_independent(tmp_path):
    _tree(tmp_path)
    target = InspectionTarget(tmp_path.resolve())
    inv = discover_repository(target)
    first = ToolingAnalyzer().run(target, inv)
    assert first == ToolingAnalyzer().run(target, inv)
    files = list(inv.files)
    random.Random(3).shuffle(files)
    assert first == ToolingAnalyzer().run(target, replace(inv, files=tuple(files)))
    keys = [(f.category.value, f.subject) for f in first.findings]
    assert keys == sorted(keys)
    for f in first.findings:
        ev = [(e.path, e.indicator, e.detail or "") for e in f.evidence]
        assert ev == sorted(ev)


def test_no_absolute_path_in_output(tmp_path):
    _tree(tmp_path)
    write(tmp_path, "bad/pyproject.toml", "[x")
    write(tmp_path, ".spawn/meta.json", "{bad")
    result = run(tmp_path)
    assert result.diagnostics
    blob = repr(result)
    assert str(tmp_path) not in blob and tmp_path.as_posix() not in blob


def test_contract_invariants_and_validation(tmp_path):
    _tree(tmp_path)
    write(tmp_path, "bad/setup.cfg", "oops")
    result = run(tmp_path)
    for f in result.findings:
        if f.detection_state in (D, INF):
            assert f.evidence
        if f.detection_state is INF:
            assert f.detail
        if f.detection_state is NC:
            assert f.evidence == ()
    report = InspectionReport(
        target=InspectionTarget(tmp_path.resolve()),
        findings=result.findings,
        analyzer_results=(result,),
        diagnostics=result.diagnostics,
    )
    assert validate_report(report) == []


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


def test_file_absent_from_inventory_is_ignored(tmp_path):
    write(tmp_path, "ruff.toml")
    write(tmp_path, "Dockerfile")
    write(tmp_path, "pyproject.toml", "[tool.black]\n")
    inv = replace(
        discover_repository(InspectionTarget(tmp_path.resolve())),
        files=("ruff.toml",),
    )
    result = run(tmp_path, inv)
    assert state(result, C.TOOL, "ruff") is D
    assert state(result, C.TOOL, "black") is None
    assert state(result, C.CONTAINER, "docker") is N


def test_never_reads_env_and_avoids_forbidden_apis():
    source = Path(tooling_module.__file__).read_text(encoding="utf-8")
    assert "read_project_metadata" not in source
    assert "DependencyAnalyzer" not in source
    banned_imports = {
        "subprocess",
        "socket",
        "urllib",
        "http",
        "requests",
        "shutil",
        "yaml",
    }
    banned_calls = {"walk", "glob", "rglob", "iterdir", "scandir", "exec", "eval"}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names = {(node.module or "").split(".")[0]}
        else:
            names = set()
        assert not names & banned_imports
        if isinstance(node, ast.Call):
            func = node.func
            called = (
                func.attr
                if isinstance(func, ast.Attribute)
                else getattr(func, "id", "")
            )
            assert called not in banned_calls
