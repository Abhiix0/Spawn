"""spawn.inspection — Project Inspection Contract (Issue #53).

Public surface.  Downstream modules (#54–#59) import from here.

    from spawn.inspection import (
        SCHEMA_VERSION,
        DetectionState, AnalysisStatus, FindingCategory,
        Evidence, Diagnostic, Finding,
        AnalyzerResult,
        InspectionTarget, DiscoveryInventory,
        InspectionReport,
        validate_report,
        Analyzer,
        InspectionError,
        ReportDecodeError,
        to_json, from_dict, from_json,
    )
"""

from spawn.inspection.base import Analyzer
from spawn.inspection.exceptions import InspectionError
from spawn.inspection.models import (
    SCHEMA_VERSION,
    AnalyzerResult,
    AnalysisStatus,
    Diagnostic,
    DiscoveryInventory,
    DetectionState,
    Evidence,
    Finding,
    FindingCategory,
    InspectionReport,
    InspectionTarget,
    validate_report,
)
from spawn.inspection.serialization import (
    ReportDecodeError,
    from_dict,
    from_json,
    to_json,
)

__all__ = [
    "SCHEMA_VERSION",
    "Analyzer",
    "AnalyzerResult",
    "AnalysisStatus",
    "Diagnostic",
    "DiscoveryInventory",
    "DetectionState",
    "Evidence",
    "Finding",
    "FindingCategory",
    "InspectionError",
    "InspectionReport",
    "InspectionTarget",
    "ReportDecodeError",
    "from_dict",
    "from_json",
    "to_json",
    "validate_report",
]
