"""Time the installed onboarding CLI against the Phase 0 large-tree fixture."""

from __future__ import annotations

import json
import os
import subprocess
import sysconfig
import tempfile
from pathlib import Path
from time import perf_counter

from measure_inspection_baseline import _snapshot, materialize

from spawn.inspection import run_inspection


def main() -> int:
    scripts = Path(sysconfig.get_path("scripts"))
    spawn = scripts / ("spawn.exe" if os.name == "nt" else "spawn")
    with tempfile.TemporaryDirectory(prefix="spawn-onboard-") as temp:
        root = materialize("large_tree", Path(temp))
        before = _snapshot(root)
        start = perf_counter()
        inspection = run_inspection(root)
        inspect_seconds = perf_counter() - start
        start = perf_counter()
        completed = subprocess.run(
            [str(spawn), "onboard", str(root), "--json"],
            capture_output=True,
            check=True,
            encoding="utf-8",
        )
        onboard_seconds = perf_counter() - start
        report = json.loads(completed.stdout)
        unchanged = _snapshot(root) == before
        print(
            json.dumps(
                {
                    "fixture": "large_tree",
                    "source_files": sum(1 for _ in (root / "src").rglob("*.py")),
                    "inspection_seconds": round(inspect_seconds, 6),
                    "onboard_cli_seconds": round(onboard_seconds, 6),
                    "inspection_status": inspection.status.value,
                    "onboard_status": report["status"],
                    "diagnostic_counts": report["diagnostic_counts"],
                    "read_only": unchanged,
                },
                sort_keys=True,
            )
        )
        return 0 if unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
