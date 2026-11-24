"""Internal composition of inspection and developer workflow projections."""

from dataclasses import dataclass
from pathlib import Path

from spawn.inspection.development_workflows import (
    DevelopmentWorkflows,
    discover_development_workflows,
)
from spawn.inspection.discovery import discover_repository, validate_inspection_root
from spawn.inspection.entry_points import (
    PythonEntryPoints,
    discover_python_entry_points,
)
from spawn.inspection.models import InspectionReport
from spawn.inspection.orchestrator import ANALYZERS, _inspect_inventory


@dataclass(frozen=True)
class PythonOnboarding:
    inspection: InspectionReport
    entry_points: PythonEntryPoints
    workflows: DevelopmentWorkflows


def inspect_python_onboarding(path: str | Path) -> PythonOnboarding:
    """Discover once and share the inventory across three independent results."""
    target = validate_inspection_root(path)
    inventory = discover_repository(target)
    entry_points = discover_python_entry_points(target, inventory)
    return PythonOnboarding(
        _inspect_inventory(target, inventory, ANALYZERS),
        entry_points,
        discover_development_workflows(target, inventory, entry_points),
    )
