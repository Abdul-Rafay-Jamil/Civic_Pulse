"""Complaint service — business rules, triage orchestration, state machine.

This layer sits between routes and repositories. It contains:
- Triage orchestration with timeout, retry (with jitter), and fallback
- Status state machine enforcement
- Statistics (delegated to cache + repository)
"""

import asyncio
import random
import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models import (
    Category,
    ComplaintCreate,
    Priority,
    Status,
    TriageResult,
    is_valid_transition,
)
from app.providers.cache import (
    get_cached_stats,
    get_cached_triage,
    invalidate_stats_cache,
    set_cached_stats,
    set_cached_triage,
)
from app.providers.triage.base import TriageProvider
from app.providers.triage.rules import RuleBasedTriage
from app.repositories.complaint_repository import ComplaintRepository

logger = get_logger(__name__)

# Timeout and retry constants (§2.5)
TRIAGE_TIMEOUT_SECONDS = 10.0
MAX_RETRIES = 1  # retry once
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class ComplaintService:
    """Business logic for complaint lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        provider: TriageProvider,
    ) -> None:
        self._repo = ComplaintRepository(session)
        self._provider = provider
        self._fallback = RuleBasedTriage()
        self._session = session

    async def create_complaint(self, data: ComplaintCreate) -> dict[str, Any]:
        """Validate → triage → persist. Returns the created complaint."""

        # Check triage cache first (content-hash deduplication)
        cached_triage = await get_cached_triage(data.text, data.location)
        if cached_triage is not None:
            triage_result = TriageResult(**cached_triage["result"])
            triaged_by = cached_triage["provider"]
            latency_ms = 0  # cached, no actual inference
            logger.info(
                "triage_cache_hit",
                provider=triaged_by,
            )
        else:
            # Perform triage with timeout, retry, and fallback
            triage_result, triaged_by, latency_ms = await self._triage_with_resilience(
                data.text, data.location
            )

            # Cache the result
            await set_cached_triage(
                data.text,
                data.location,
                {
                    "result": triage_result.model_dump(),
                    "provider": triaged_by,
                },
            )

        # Persist to database
        complaint = await self._repo.create(
            text=data.text,
            location=data.location,
            reporter_contact=data.reporter_contact,
            category=triage_result.category,
            priority=triage_result.priority,
            ai_summary=triage_result.summary,
            triaged_by=triaged_by,
            triage_latency_ms=latency_ms,
        )
        await self._session.commit()

        # Invalidate stats cache on write
        await invalidate_stats_cache()

        return self._complaint_to_dict(complaint)

    async def get_complaint(self, complaint_id: uuid.UUID) -> dict[str, Any] | None:
        """Fetch a single complaint by ID."""
        complaint = await self._repo.get_by_id(complaint_id)
        if complaint is None:
            return None
        return self._complaint_to_dict(complaint)

    async def list_complaints(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        category: Category | None = None,
        priority: Priority | None = None,
        status: Status | None = None,
    ) -> dict[str, Any]:
        """Paginated, filterable complaint list."""
        items, total = await self._repo.list_complaints(
            page=page,
            page_size=page_size,
            category=category,
            priority=priority,
            status=status,
        )
        return {
            "items": [self._complaint_to_dict(c) for c in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_status(
        self, complaint_id: uuid.UUID, new_status: Status
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Enforce the state machine. Returns (complaint_dict, error_message).

        If the transition is invalid, returns (None, "Cannot transition from X to Y").
        """
        complaint = await self._repo.get_by_id(complaint_id)
        if complaint is None:
            return None, "not_found"

        current_status = Status(complaint.status)
        if not is_valid_transition(current_status, new_status):
            error_msg = (
                f"Cannot transition from '{current_status.value}' to '{new_status.value}'. "
                f"Valid transitions from '{current_status.value}': "
                f"{', '.join(s.value for s in sorted({s for s in Status if is_valid_transition(current_status, s)}, key=lambda s: s.value)) or 'none (terminal state)'}"
            )
            return None, error_msg

        updated = await self._repo.update_status(complaint_id, new_status)
        await self._session.commit()

        # Invalidate stats cache on write
        await invalidate_stats_cache()

        if updated is None:
            return None, "not_found"
        return self._complaint_to_dict(updated), None

    async def get_stats(self) -> tuple[dict[str, Any], bool]:
        """Get aggregate stats. Returns (stats, cache_hit)."""
        cached, is_hit = await get_cached_stats()
        if cached is not None:
            return cached, True

        stats = await self._repo.get_stats()
        await set_cached_stats(stats)
        return stats, False

    async def get_provider_info(self) -> dict[str, Any]:
        """Active provider and recent triage outcomes."""
        outcomes = await self._repo.get_recent_triage_outcomes(limit=20)
        return {
            "active_provider": self._provider.name,
            "recent_outcomes": outcomes,
        }

    # ── Triage orchestration with resilience ──────────────────────────

    async def _triage_with_resilience(
        self, text: str, location: str
    ) -> tuple[TriageResult, str, int]:
        """Triage with timeout, single jittered retry, and fallback.

        Returns: (result, provider_name, latency_ms)
        """
        start = time.monotonic()

        # Try primary provider with retry
        last_error: Exception | None = None
        for attempt in range(1 + MAX_RETRIES):
            try:
                result = await asyncio.wait_for(
                    self._provider.triage(text, location),
                    timeout=TRIAGE_TIMEOUT_SECONDS,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                logger.info(
                    "triage_success",
                    provider=self._provider.name,
                    attempt=attempt + 1,
                    latency_ms=latency_ms,
                )
                return result, self._provider.name, latency_ms

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    "triage_timeout",
                    provider=self._provider.name,
                    attempt=attempt + 1,
                    timeout_s=TRIAGE_TIMEOUT_SECONDS,
                )
            except Exception as e:
                last_error = e
                # Only retry on retryable errors (timeout, 429, 5xx)
                if not self._is_retryable(e):
                    logger.warning(
                        "triage_non_retryable_error",
                        provider=self._provider.name,
                        error=str(e),
                        error_class=type(e).__name__,
                    )
                    break
                logger.warning(
                    "triage_retryable_error",
                    provider=self._provider.name,
                    attempt=attempt + 1,
                    error=str(e),
                    error_class=type(e).__name__,
                )

            # Jittered backoff before retry
            if attempt < MAX_RETRIES:
                jitter = random.uniform(0.5, 1.5)
                await asyncio.sleep(jitter)

        # Fallback to rules — a user must never see a 500 because a third party was rate-limited
        logger.warning(
            "triage_fallback",
            provider=self._provider.name,
            error=str(last_error),
            error_class=type(last_error).__name__ if last_error else "unknown",
        )
        result = await self._fallback.triage(text, location)
        latency_ms = int((time.monotonic() - start) * 1000)
        return result, "rules:fallback", latency_ms

    def _is_retryable(self, error: Exception) -> bool:
        """Only retry on timeout, 429, and 5xx. Never retry a 400."""
        if isinstance(error, asyncio.TimeoutError):
            return True
        error_str = str(error)
        return any(str(code) in error_str for code in RETRYABLE_STATUS_CODES)

    @staticmethod
    def _complaint_to_dict(complaint: Any) -> dict[str, Any]:
        """Convert a SQLAlchemy Complaint to a dict matching ComplaintResponse."""
        return {
            "id": str(complaint.id),
            "text": complaint.text,
            "location": complaint.location,
            "reporter_contact": complaint.reporter_contact,
            "category": complaint.category,
            "priority": complaint.priority,
            "status": complaint.status,
            "ai_summary": complaint.ai_summary,
            "triaged_by": complaint.triaged_by,
            "triage_latency_ms": complaint.triage_latency_ms,
            "created_at": complaint.created_at.isoformat() if complaint.created_at else None,
            "updated_at": complaint.updated_at.isoformat() if complaint.updated_at else None,
        }
