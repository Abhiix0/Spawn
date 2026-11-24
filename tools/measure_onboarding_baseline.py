"""Measure inspection and onboarding on the Phase 0 fixture and exclusions."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sysconfig
import tempfile
from pathlib import Path
from statistics import median
from time import perf_counter

from measure_inspection_baseline import _snapshot, materialize

from spawn.inspection import run_inspection


def _add_exclusions(root: Path) -> None:
    for name in ("node_modules", ".audit-scratch"):
        shutil.copytree(root / "src", root / name)
    git = root / ".git"
    (git / "info").mkdir(parents=True)
    (git / "info/exclude").write_text(".audit-scratch/\n", encoding="utf-8")
    header = struct.pack(">4sII", b"DIRC", 2, 0)
    (git / "index").write_bytes(
        header + hashlib.sha1(header, usedforsecurity=False).digest()
    )


def _measure(root: Path, spawn: Path) -> dict:
    before = _snapshot(root)
    commands = {
        "inspection_cli": ["inspect", ".", "--json"],
        "onboarding_cli": ["onboard", "."],
        "onboarding_json": ["onboard", ".", "--json"],
    }
    samples = {name: [] for name in ("inspection_core", *commands)}
    for _ in range(3):
        start = perf_counter()
        inspection = run_inspection(root)
        samples["inspection_core"].append(perf_counter() - start)
        for name, args in commands.items():
            start = perf_counter()
            result = subprocess.run(
                [str(spawn), *args],
                cwd=root,
                capture_output=True,
                check=True,
                encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8", "NO_COLOR": "1"},
            )
            samples[name].append(perf_counter() - start)
            if name == "onboarding_json":
                onboarding = json.loads(result.stdout)
    return {
        "fixture": root.name,
        "medians_seconds": {
            name: round(median(times), 6) for name, times in samples.items()
        },
        "source_files": sum(1 for _ in (root / "src").rglob("*.py")),
        "inspection_files": inspection.structure.file_count,
        "inspection_status": inspection.status.value,
        "onboarding_status": onboarding["status"],
        "read_only": before == _snapshot(root),
    }


def main() -> int:
    scripts = Path(sysconfig.get_path("scripts"))
    spawn = scripts / ("spawn.exe" if os.name == "nt" else "spawn")
    with tempfile.TemporaryDirectory(prefix="spawn-onboard-") as temp:
        root = materialize("large_tree", Path(temp))
        base = _measure(root, spawn)
        print(json.dumps(base, sort_keys=True), flush=True)
        with_exclusions = root.rename(root.with_name("large_tree_with_exclusions"))
        _add_exclusions(with_exclusions)
        excluded = _measure(with_exclusions, spawn)
        print(json.dumps(excluded, sort_keys=True), flush=True)
        return 0 if base["read_only"] and excluded["read_only"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
