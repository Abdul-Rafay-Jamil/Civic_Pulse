"""Simulated triage provider — deterministic fake for CI.

Seeded, no network, configurable failure injection.
"""

import hashlib

from app.models import Category, Priority, TriageResult


class SimulatedTriage:
    """Deterministic triage for CI — no network calls, repeatable results.

    If `fail=True` is configured, every call raises to test fallback.
    If `malformed=True`, returns invalid data to test validation.
    """

    def __init__(
        self,
        *,
        fail: bool = False,
        malformed: bool = False,
    ) -> None:
        self._fail = fail
        self._malformed = malformed

    @property
    def name(self) -> str:
        return "simulated"

    async def triage(self, text: str, location: str) -> TriageResult:
        """Return deterministic results based on content hash."""
        if self._fail:
            raise RuntimeError("SimulatedTriage: configured to fail for testing")

        if self._malformed:
            # Return something that should fail validation upstream
            raise ValueError("SimulatedTriage: malformed response injection")

        # Deterministic: hash the text to pick category and priority
        digest = hashlib.sha256(text.encode()).hexdigest()
        hash_int = int(digest[:8], 16)

        categories = list(Category)
        priorities = list(Priority)

        category = categories[hash_int % len(categories)]
        priority = priorities[(hash_int >> 8) % len(priorities)]

        summary = text[:130].strip() if len(text) > 130 else text.strip()
        # Replace newlines for clean summary
        summary = summary.replace("\n", " ")

        confidence = 0.85

        return TriageResult(
            category=category,
            priority=priority,
            summary=summary,
            confidence=confidence,
        )
