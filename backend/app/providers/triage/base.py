"""TriageProvider protocol — the interface all providers implement."""

from typing import Protocol, runtime_checkable

from app.models import TriageResult


@runtime_checkable
class TriageProvider(Protocol):
    """Protocol for triage providers.

    Every provider must implement `triage()` returning a validated TriageResult.
    The `name` property identifies the provider for the `triaged_by` column.
    """

    @property
    def name(self) -> str:
        """Human-readable provider identifier, e.g. 'llm:groq'."""
        ...

    async def triage(self, text: str, location: str) -> TriageResult:
        """Classify a complaint into category, priority, and summary."""
        ...
