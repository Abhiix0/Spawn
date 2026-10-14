from __future__ import annotations

from spawn.core.exceptions import SpawnError


class InspectionError(SpawnError):
    """Raised when an inspection cannot be performed (invalid target, fatal
    discovery error, or unrecoverable orchestration failure).

    exit_code = 7  (codes 1-6 are reserved by the generation pipeline;
    8 and 9 remain available for future inspection sub-errors).
    """

    exit_code = 7
