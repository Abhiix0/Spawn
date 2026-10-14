"""Analyzer interface — Issue #53.

Defines the Protocol that all inspection analyzers (#55, #56, #57, and
future analyzers) must satisfy.

An analyzer is any object with:
  - a ``name: str`` class attribute (stable slug, e.g. "language")
  - a ``run(target, inventory) -> AnalyzerResult`` method

Using Protocol (structural subtyping) rather than ABC means analyzers do
not need to import or inherit from this module.  A plain class with the
right shape satisfies the interface.  Tests can use anonymous objects.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from spawn.inspection.models import AnalyzerResult, DiscoveryInventory, InspectionTarget


@runtime_checkable
class Analyzer(Protocol):
    """The interface every inspection analyzer must satisfy.

    Contracts on ``run()``:
    - MUST NOT raise.  Exceptions must be caught internally; emit a
      Diagnostic(fatal=True) and return a result with status=FAILED.
    - MUST NOT modify the target repository or any file under target.path.
    - MUST NOT execute repository code or spawn subprocesses.
    - MUST NOT make network requests.
    - MAY return zero findings (valid when the subject is not present).
    - The ``analyzer_name`` on the returned AnalyzerResult MUST equal
      ``self.name``.
    """

    name: str
    """Stable slug identifying this analyzer.
    Lowercase, hyphen-separated.  Examples: "language", "dependency", "tooling".
    Used as the ``analyzer_name`` on AnalyzerResult and as the ``source``
    prefix in Diagnostic codes.
    """

    def run(
        self,
        target: InspectionTarget,
        inventory: DiscoveryInventory,
    ) -> AnalyzerResult:
        """Run analysis and return findings and diagnostics.

        Parameters
        ----------
        target:
            The validated, resolved inspection root.  Use ``target.path``
            to build absolute paths when opening files.
        inventory:
            The pre-built file/directory listing from the #54 discovery
            module.  Analyzers use this instead of traversing the filesystem
            themselves to ensure consistent, deterministic file enumeration.

        Returns
        -------
        AnalyzerResult
            Always returned; never raises.  If analysis fails fatally,
            return an AnalyzerResult with status=FAILED and a Diagnostic
            with fatal=True.
        """
        ...
