"""Static engineering-tooling and repository-indicator inspection (Issue #57).

Emits TOOL, CI, CONTAINER, DATABASE and STRUCTURE findings. Files come only from
``DiscoveryInventory`` (files / directories / skipped); anything read is read in
binary with a 1 MB bound. Evidence means a static indicator exists: nothing here
claims a tool runs or passes, or that a database is in use. There is no YAML
parser, so YAML-based indicators are detected by path presence only; content of
CI, container and pre-commit files is never parsed. ``.env`` files are never read.

Matrix (anything else is out of scope):

TOOL (config files match at any depth; tables via tomllib / configparser / json)
- ruff: ruff.toml, .ruff.toml, pyproject [tool.ruff]
- black: pyproject [tool.black]
- flake8: .flake8, setup.cfg [flake8], tox.ini [flake8]
- mypy: mypy.ini, .mypy.ini, pyproject [tool.mypy], setup.cfg [mypy]
- pyright: pyrightconfig.json, pyproject [tool.pyright]
- pytest: pytest.ini, pyproject [tool.pytest.ini_options], setup.cfg
  [tool:pytest], tox.ini [pytest]
- eslint: .eslintrc[.js|.cjs|.mjs|.json|.yml|.yaml], eslint.config.{js,mjs,cjs,ts},
  package.json "eslintConfig"
- prettier: .prettierrc[.json|.yml|.yaml|.js|.cjs|.mjs|.toml],
  prettier.config.{js,cjs,mjs}, package.json "prettier"
- jest: jest.config.{js,ts,mjs,cjs,json}, package.json "jest"
- vitest: vitest.config.{js,ts,mjs,cjs}
- pre-commit: .pre-commit-config.yaml
- A config makes the tool DETECTED. Declared as a dependency (via the #56
  ``parse_manifest``) without any config: INFERRED.
- git: ".git" at the root (inventory.skipped or files) DETECTED; only a root
  .gitignore / .gitattributes INFERRED (archive exports drop .git).

CI (repository root only; presence only): github-actions
(.github/workflows/*.yml|yaml, exactly one level), gitlab-ci (.gitlab-ci.yml),
circleci (.circleci/config.yml), jenkins (Jenkinsfile), azure-pipelines
(azure-pipelines.yml).

CONTAINER (any depth): docker (Dockerfile, Dockerfile.*, *.Dockerfile DETECTED;
only .dockerignore INFERRED), docker-compose (docker-compose.y[a]ml,
compose.y[a]ml).

DATABASE (INFERRED only, from declared driver packages): postgres, mysql,
mongodb, redis, sqlite. READMEs, .env, data files and compose images are never
evidence.

STRUCTURE (repository root only): tests-directory (tests, test or __tests__),
src-layout (src/<pkg>/__init__.py), spawn-generated (.spawn/meta.json that is a
JSON object; a marker only, nothing is copied from it; present but unusable is
INFERRED plus ``tooling.malformed_metadata``).

Negatives: NOT_DETECTED (detail lists what was checked) only for the headline
set git, pytest, ruff, github-actions, docker, tests-directory. For the
manifest-dependent headlines (pytest, ruff) a broken manifest or the manifest
cap makes the absence UNKNOWN instead.

Diagnostics (warning): tooling.file_too_large, tooling.unreadable_file,
tooling.undecodable_file, tooling.malformed_manifest, tooling.malformed_metadata,
tooling.manifest_limit_reached. Fatal: tooling.internal_error.
"""

from __future__ import annotations

import configparser
import json
import tomllib
from pathlib import Path, PurePosixPath

from spawn.inspection._reading import MAX_FILE_SIZE, read_text_limited
from spawn.inspection.dependencies import parse_manifest
from spawn.inspection.models import (
    AnalysisStatus,
    AnalyzerResult,
    DetectionState,
    Diagnostic,
    DiscoveryInventory,
    Evidence,
    Finding,
    FindingCategory,
    InspectionTarget,
)

MAX_MANIFESTS = 500

_TOOL, _CI, _CONTAINER, _DB, _STRUCT = (
    FindingCategory.TOOL,
    FindingCategory.CI,
    FindingCategory.CONTAINER,
    FindingCategory.DATABASE,
    FindingCategory.STRUCTURE,
)

_JS = ("js", "cjs", "mjs")
_CONFIG_NAMES: dict[str, str] = {}  # config file basename -> tool subject
for _tool, _names in {
    "ruff": ["ruff.toml", ".ruff.toml"],
    "flake8": [".flake8"],
    "mypy": ["mypy.ini", ".mypy.ini"],
    "pyright": ["pyrightconfig.json"],
    "pytest": ["pytest.ini"],
    "eslint": [".eslintrc"]
    + [f".eslintrc.{e}" for e in (*_JS, "json", "yml", "yaml")]
    + [f"eslint.config.{e}" for e in (*_JS, "ts")],
    "prettier": [".prettierrc"]
    + [f".prettierrc.{e}" for e in (*_JS, "json", "yml", "yaml", "toml")]
    + [f"prettier.config.{e}" for e in _JS],
    "jest": [f"jest.config.{e}" for e in (*_JS, "ts", "json")],
    "vitest": [f"vitest.config.{e}" for e in (*_JS, "ts")],
    "pre-commit": [".pre-commit-config.yaml"],
}.items():
    _CONFIG_NAMES.update(dict.fromkeys(_names, _tool))

_TOOLS = frozenset(_CONFIG_NAMES.values()) | {"black"}
_PYPROJECT_TABLES = ("ruff", "black", "mypy", "pyright")
_PACKAGE_KEYS = {"eslintConfig": "eslint", "prettier": "prettier", "jest": "jest"}
_INI_SECTIONS = {
    "setup.cfg": [("flake8", "flake8"), ("mypy", "mypy"), ("tool:pytest", "pytest")],
    "tox.ini": [("flake8", "flake8"), ("pytest", "pytest")],
}
_CI_ROOT_FILES = {
    ".gitlab-ci.yml": "gitlab-ci",
    ".circleci/config.yml": "circleci",
    "Jenkinsfile": "jenkins",
    "azure-pipelines.yml": "azure-pipelines",
}
_COMPOSE_NAMES = frozenset(
    {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
)
_DB_DRIVERS = {
    "postgres": ("psycopg", "psycopg2", "psycopg2-binary", "asyncpg", "pg"),
    "mysql": ("pymysql", "mysqlclient", "mysql-connector-python", "mysql2"),
    "mongodb": ("pymongo", "motor", "mongodb", "mongoose"),
    "redis": ("redis", "ioredis"),
    "sqlite": ("aiosqlite", "better-sqlite3"),
}
_DRIVER_DB = {drv: db for db, drvs in _DB_DRIVERS.items() for drv in drvs}
_DECL_BASES = frozenset({"pyproject.toml", "package.json"})
_TESTS_DIRS = ("tests", "test", "__tests__")

# headline subject -> locations checked (used in NOT_DETECTED / UNKNOWN details)
_HEADLINES: dict[tuple[FindingCategory, str], str] = {
    (_TOOL, "git"): "root .git; root .gitignore, .gitattributes",
    (_TOOL, "pytest"): (
        "pytest.ini; [tool.pytest.ini_options] in pyproject.toml; "
        "[tool:pytest] in setup.cfg; [pytest] in tox.ini; pytest dependency"
    ),
    (_TOOL, "ruff"): (
        "ruff.toml, .ruff.toml; [tool.ruff] in pyproject.toml; ruff dependency"
    ),
    (_CI, "github-actions"): ".github/workflows/*.yml, .github/workflows/*.yaml",
    (_CONTAINER, "docker"): "Dockerfile, Dockerfile.*, *.Dockerfile, .dockerignore",
    (_STRUCT, "tests-directory"): "root directories tests, test, __tests__",
}
_MANIFEST_DEPENDENT = {(_TOOL, "pytest"), (_TOOL, "ruff")}

_LOAD_MESSAGES = {
    "file_too_large": f"File exceeds {MAX_FILE_SIZE} bytes; skipped.",
    "unreadable_file": "File could not be read; skipped.",
    "undecodable_file": "File is not valid UTF-8; skipped.",
}


def _is_manifest(rel: str) -> bool:
    name = PurePosixPath(rel).name
    return name in {"pyproject.toml", "package.json", "setup.cfg", "tox.ini"} or (
        name == "requirements.txt"
        or (name.startswith("requirements-") and name.endswith(".txt"))
    )


def _configs(base: str, text: str) -> list[tuple[str, str]]:
    """Return (tool, indicator) config tables in one manifest; raise on bad syntax."""
    if not text.strip():
        return []
    if base == "pyproject.toml":
        tool = tomllib.loads(text).get("tool")
        tool = tool if isinstance(tool, dict) else {}
        found = [
            (t, f"[tool.{t}] section")
            for t in _PYPROJECT_TABLES
            if isinstance(tool.get(t), dict)
        ]
        pytest = tool.get("pytest")
        if isinstance(pytest, dict) and isinstance(pytest.get("ini_options"), dict):
            found.append(("pytest", "[tool.pytest.ini_options] section"))
        return found
    if base == "package.json":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("package.json is not an object")
        return [(s, f'"{k}" key') for k, s in _PACKAGE_KEYS.items() if k in data]
    if base in _INI_SECTIONS:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(text)
        return [
            (tool, f"[{sec}] section")
            for sec, tool in _INI_SECTIONS[base]
            if parser.has_section(sec)
        ]
    return []


def _load(root: Path, rel: str) -> tuple[str | None, str | None]:
    """Return (text, None) or (None, problem_code)."""
    try:
        text = read_text_limited(root / rel)
    except UnicodeDecodeError:
        return None, "undecodable_file"
    except OSError:
        return None, "unreadable_file"
    return (text, None) if text is not None else (None, "file_too_large")


def _sorted_evidence(items: set[Evidence]) -> tuple[Evidence, ...]:
    return tuple(sorted(items, key=lambda e: (e.path, e.indicator, e.detail or "")))


class ToolingAnalyzer:
    """Engineering-tooling and repository-indicator analyzer (see module docstring)."""

    name = "tooling"

    def run(
        self, target: InspectionTarget, inventory: DiscoveryInventory
    ) -> AnalyzerResult:
        out: dict[tuple[FindingCategory, str], Finding] = {}
        diagnostics: list[Diagnostic] = []

        def warn(code: str, message: str, rel: str | None = None) -> None:
            diagnostics.append(Diagnostic(code, message, "warning", self.name, rel))

        def emit(cat, subject, state, evidence=(), detail=None) -> None:
            out[(cat, subject)] = Finding(
                cat, subject, state, _sorted_evidence(set(evidence)), detail
            )

        def present_or_absent(cat, subject, evidence, unsure: str | None = None):
            """DETECTED when evidence exists, else the headline negative (if any)."""
            if evidence:
                emit(cat, subject, DetectionState.DETECTED, evidence)
            elif (cat, subject) in _HEADLINES:
                checked = _HEADLINES[(cat, subject)]
                if unsure:
                    emit(
                        cat,
                        subject,
                        DetectionState.UNKNOWN,
                        detail=f"Could not determine: {unsure}. Checked: {checked}.",
                    )
                else:
                    emit(
                        cat,
                        subject,
                        DetectionState.NOT_DETECTED,
                        detail=f"Checked: {checked}.",
                    )

        try:
            root = Path(target.path)
            files = sorted(set(inventory.files))
            fileset = set(files)
            skipped = set(inventory.skipped)

            def named(match) -> list[Evidence]:
                return [
                    Evidence(rel, f"{PurePosixPath(rel).name} present")
                    for rel in files
                    if match(rel, PurePosixPath(rel).name)
                ]

            # git
            if ".git" in skipped or ".git" in fileset:
                present_or_absent(_TOOL, "git", [Evidence(".git", ".git present")])
            else:
                markers = [
                    Evidence(f, f"{f} present")
                    for f in (".gitattributes", ".gitignore")
                    if f in fileset
                ]
                if markers:
                    emit(
                        _TOOL,
                        "git",
                        DetectionState.INFERRED,
                        markers,
                        "no .git found, but git ignore/attributes files exist; "
                        "archive exports drop .git",
                    )
                else:
                    present_or_absent(_TOOL, "git", [])

            # CI (root only)
            workflows = named(
                lambda rel, n: (
                    rel.startswith(".github/workflows/")
                    and rel.count("/") == 2
                    and n.endswith((".yml", ".yaml"))
                )
            )
            present_or_absent(_CI, "github-actions", workflows)
            for path, subject in _CI_ROOT_FILES.items():
                if path in fileset:
                    emit(
                        _CI,
                        subject,
                        DetectionState.DETECTED,
                        [Evidence(path, f"{path} present")],
                    )

            # containers
            dockerfiles = named(
                lambda rel, n: (
                    n == "Dockerfile"
                    or n.startswith("Dockerfile.")
                    or n.endswith(".Dockerfile")
                )
            )
            ignores = named(lambda rel, n: n == ".dockerignore")
            if dockerfiles or not ignores:
                present_or_absent(_CONTAINER, "docker", dockerfiles)
            else:
                emit(
                    _CONTAINER,
                    "docker",
                    DetectionState.INFERRED,
                    ignores,
                    ".dockerignore present but no Dockerfile found",
                )
            compose = named(lambda rel, n: n in _COMPOSE_NAMES)
            if compose:
                emit(_CONTAINER, "docker-compose", DetectionState.DETECTED, compose)

            # structure (root only)
            test_dirs = [
                Evidence(d, f"{d}/ directory present")
                for d in sorted(set(inventory.directories))
                if d in _TESTS_DIRS
            ]
            present_or_absent(_STRUCT, "tests-directory", test_dirs)
            src_pkgs = named(
                lambda rel, n: (
                    n == "__init__.py"
                    and rel.startswith("src/")
                    and rel.count("/") == 2
                )
            )
            if src_pkgs:
                emit(_STRUCT, "src-layout", DetectionState.DETECTED, src_pkgs)
            meta = ".spawn/meta.json"
            if meta in fileset:
                text, problem = _load(root, meta)
                if text is not None:
                    try:
                        data = json.loads(text)
                        problem = None if isinstance(data, dict) else "not_an_object"
                    except ValueError:
                        problem = "malformed_json"
                if problem is None:
                    emit(
                        _STRUCT,
                        "spawn-generated",
                        DetectionState.DETECTED,
                        [Evidence(meta, "Spawn metadata marker present")],
                    )
                else:
                    warn("tooling.malformed_metadata", "Spawn metadata unusable.", meta)
                    emit(
                        _STRUCT,
                        "spawn-generated",
                        DetectionState.INFERRED,
                        [Evidence(meta, "Spawn metadata file present")],
                        "metadata file present but unreadable or malformed "
                        f"({problem})",
                    )

            # config files, then manifests (tables and declared dependencies)
            config: dict[str, set[Evidence]] = {}
            for ev in named(lambda rel, n: n in _CONFIG_NAMES):
                config.setdefault(
                    _CONFIG_NAMES[PurePosixPath(ev.path).name], set()
                ).add(ev)
            declared: dict[str, set[Evidence]] = {}
            broken: list[str] = []
            manifests = [rel for rel in files if _is_manifest(rel)]
            truncated = len(manifests) > MAX_MANIFESTS
            if truncated:
                manifests = manifests[:MAX_MANIFESTS]
                warn(
                    "tooling.manifest_limit_reached",
                    f"More than {MAX_MANIFESTS} manifests; the rest were skipped.",
                )
            for rel in manifests:
                base = PurePosixPath(rel).name
                text, problem = _load(root, rel)
                if text is None:
                    warn(f"tooling.{problem}", _LOAD_MESSAGES[problem], rel)
                    broken.append(rel)
                    continue
                bad = False
                try:
                    for tool, indicator in _configs(base, text):
                        config.setdefault(tool, set()).add(Evidence(rel, indicator))
                except (ValueError, configparser.Error):
                    bad = True
                if base not in ("setup.cfg", "tox.ini"):
                    parsed = parse_manifest(rel, text)
                    bad = bad or any(
                        p.code == "dependency.malformed_manifest"
                        for p in parsed.problems
                    )
                    for d in parsed.declarations:
                        if d.subject in _TOOLS or d.subject in _DRIVER_DB:
                            declared.setdefault(d.subject, set()).add(
                                Evidence(rel, f"{d.subject} in {d.section}", d.detail)
                            )
                if bad:
                    warn("tooling.malformed_manifest", "Could not parse manifest.", rel)
                    broken.append(rel)

            reasons = []
            if broken:
                reasons.append(
                    f"unreadable or malformed: {', '.join(sorted(set(broken)))}"
                )
            if truncated:
                reasons.append(f"more than {MAX_MANIFESTS} manifests; some not read")
            unsure = "; ".join(reasons) or None

            for tool in sorted(_TOOLS):
                if config.get(tool):
                    present_or_absent(_TOOL, tool, config[tool])
                elif declared.get(tool):
                    emit(
                        _TOOL,
                        tool,
                        DetectionState.INFERRED,
                        declared[tool],
                        "declared as a dependency but no configuration found",
                    )
                else:
                    gate = unsure if (_TOOL, tool) in _MANIFEST_DEPENDENT else None
                    present_or_absent(_TOOL, tool, [], gate)
            for db, drivers in _DB_DRIVERS.items():
                evidence = {e for d in drivers for e in declared.get(d, ())}
                if evidence:
                    emit(
                        _DB,
                        db,
                        DetectionState.INFERRED,
                        evidence,
                        "database driver declared; actual use and connectivity "
                        "not verified",
                    )
        except Exception as exc:  # noqa: BLE001 - run() must never raise
            diagnostics.append(
                Diagnostic(
                    "tooling.internal_error",
                    f"Internal error ({type(exc).__name__}).",
                    "error",
                    self.name,
                    fatal=True,
                )
            )
            for key in _HEADLINES:
                out.setdefault(key, Finding(*key, DetectionState.NOT_CHECKED, ()))
        findings = sorted(out.values(), key=lambda f: (f.category.value, f.subject))
        if any(d.fatal for d in diagnostics):
            status = AnalysisStatus.FAILED
        else:
            status = AnalysisStatus.PARTIAL if diagnostics else AnalysisStatus.COMPLETE
        return AnalyzerResult(self.name, status, tuple(findings), tuple(diagnostics))
