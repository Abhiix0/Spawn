"""Paired release measurements with the two existing baseline fixture helpers."""

import argparse
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from measure_inspection_baseline import _snapshot, materialize
from measure_onboarding_baseline import _add_exclusions

_WORKER = """
import json, sys, time
from pathlib import Path
kind, mode = sys.argv[1:]
start = time.perf_counter()
if mode == "core":
    if kind == "inspect":
        from spawn.inspection import run_inspection as run
    elif kind == "onboard":
        from spawn.onboarding import build_onboarding_report as run
    else:
        from spawn.diagnostics.service import run_diagnostics as run
    report = run(Path("."))
    details = {"status": report.status.value}
    if kind == "diagnose":
        details.update(coverage=report.coverage.value, outcomes=report.outcome_counts)
    else:
        details["files"] = (report.structure.file_count if kind == "inspect"
                            else report.file_count)
    code = 0
else:
    from spawn.cli.app import main
    sys.argv = ["spawn", "--version"] if kind == "startup" else ["spawn", kind, "."]
    if mode == "json":
        sys.argv.append("--json")
    details = {}
    try:
        main()
    except SystemExit as exc:
        code = exc.code or 0
    else:
        code = 0
elapsed = time.perf_counter() - start
try:
    import resource
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
except ImportError:
    rss = None
print(json.dumps({"inner": elapsed, "code": code, "peak_rss": rss, **details}),
      file=sys.stderr)
"""


def sample(source, root, kind, mode):
    start = perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, "-c", _WORKER, kind, mode],
            cwd=root,
            capture_output=True,
            encoding="utf-8",
            timeout=30,
            env={
                **os.environ,
                "PYTHONPATH": str(source),
                "NO_COLOR": "1",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
    except subprocess.TimeoutExpired:
        return {"timeout": True}
    wall = perf_counter() - start
    if result.returncode or not result.stderr:
        return {"worker_exit": result.returncode}
    row = json.loads(result.stderr.splitlines()[-1])
    row["wall"] = wall
    if mode == "json":
        doc = json.loads(result.stdout)
        row["status"] = doc["status"]
        if kind == "diagnose":
            row.update(coverage=doc["coverage"], outcomes=doc["outcome_counts"])
    return row


def measure(root, sources, *, runs, worst):
    before = _snapshot(root)
    plan = []
    for kind in ("inspect", "onboard", "startup", "diagnose"):
        if worst and kind != "diagnose":
            continue
        for mode in ("human",) if kind == "startup" else ("core", "human", "json"):
            versions = (
                ("candidate",) if kind == "diagnose" else ("baseline", "candidate")
            )
            plan.append((kind, mode, versions))
    rows = {}
    for i in range(runs):
        for kind, mode, versions in plan:
            for version in versions[::-1] if i % 2 else versions:
                key = (kind, mode, version)
                row = sample(sources[version], root, kind, mode)
                rows.setdefault(key, []).append(row)
    summary = {}
    for key, values in rows.items():
        metric = "inner" if key[1] == "core" else "wall"
        times = [item[metric] for item in values if metric in item]
        summary["/".join(key)] = {
            "seconds": [statistics.median(times), min(times), max(times)]
            if times
            else None,
            "samples": values,
        }
    return {
        "fixture": root.name,
        "read_only": before == _snapshot(root),
        "results": summary,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_src", type=Path)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if args.runs < 3:
        parser.error("Use at least three paired runs")
    sources = {
        "baseline": args.baseline_src.resolve(),
        "candidate": Path(__file__).resolve().parents[1] / "src",
    }
    with TemporaryDirectory() as temp:
        base = Path(temp)
        small = materialize("large_tree", base)
        # Reuse the baseline manifest with a single representative source file.
        small.rename(base / "large")
        large = base / "large"
        small = base / "small"
        small.mkdir()
        (small / "pyproject.toml").write_bytes((large / "pyproject.toml").read_bytes())
        (small / "api.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
        worst = base / "entry-limit"
        worst.mkdir()
        for index in range(10_001):
            (worst / f"file-{index:05}.txt").touch()
        for root in (small, large, base / "large-excluded", worst):
            if root.name == "large-excluded":
                large.rename(root)
                _add_exclusions(root)
            print(
                json.dumps(measure(root, sources, runs=args.runs, worst=root == worst)),
                flush=True,
            )


if __name__ == "__main__":
    main()
