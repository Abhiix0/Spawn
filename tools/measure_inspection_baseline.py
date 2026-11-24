"""Measure inspection on the committed deterministic large-tree fixture.

Run from the repository root with ``uv run python tools/measure_inspection_baseline.py``.
The measured repository is a temporary fixture. Its source files are never run.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from spawn.inspection import run_inspection, validate_report

sys.path.insert(0, str(Path(__file__).parents[1] / "tests"))
from fixtures.inspection_corpus import materialize


def _snapshot(root: Path) -> str:
    digest = hashlib.sha256()
    for current, directories, filenames in os.walk(root, followlinks=False):
        directories.sort()
        filenames.sort()
        current_path = Path(current)
        for name in (*directories, *filenames):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode("utf-8"))
            if path.is_symlink():
                digest.update(os.readlink(path).encode("utf-8"))
            elif path.is_file():
                digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="spawn-phase0-") as temp:
        root = materialize("large_tree", Path(temp))
        before = _snapshot(root)
        start = time.perf_counter()
        report = run_inspection(root)
        elapsed = time.perf_counter() - start
        after = _snapshot(root)
        source_count = sum(1 for _ in (root / "src").rglob("*.py"))
        result = {
            "fixture": "large_tree",
            "source_files": source_count,
            "elapsed_seconds": round(elapsed, 6),
            "report_status": report.status.value,
            "contract_errors": validate_report(report),
            "read_only": before == after,
        }
        print(json.dumps(result, sort_keys=True))
        return 0 if result["read_only"] and not result["contract_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
