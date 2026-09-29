"""Complaint routes — HTTP layer. Parse, validate, serialise, status codes.

No business rules here. No SQL here. All logic delegated to services.
"""

from typing import Any
import uuid

from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session, get_triage_provider
from app.logging_config import get_logger
from app.models import (
    Category,
    ComplaintCreate,
    ComplaintResponse,
    PaginatedComplaints,
    Priority,
    Status,
    StatusUpdate,
)
from app.providers.cache import check_rate_limit
from app.providers.triage.base import TriageProvider
from app.services.complaint_service import ComplaintService

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["complaints"])


def _get_service(
    session: AsyncSession = Depends(get_db_session),
    provider: TriageProvider = Depends(get_triage_provider),
) -> ComplaintService:
    """Wire up the service with its dependencies."""
    return ComplaintService(session=session, provider=provider)


@router.post("/complaints", status_code=201, response_model=ComplaintResponse)
async def create_complaint(
    data: ComplaintCreate,
    request: Request,
    service: ComplaintService = Depends(_get_service),
) -> dict[str, Any]:
    """Validate → triage → persist. 201 Created.

    429 when the caller exceeds the rate limit.
    400 with field-level errors on validation failure.
    """
    # Rate limiting (distributed, Redis-backed)
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = await check_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    result = await service.create_complaint(data)
    return result


@router.get("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    complaint_id: uuid.UUID,
    service: ComplaintService = Depends(_get_service),
) -> dict[str, Any]:
    """200 / 404."""
    result = await service.get_complaint(complaint_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return result


@router.get("/complaints", response_model=PaginatedComplaints)
async def list_complaints(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: Category | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    status: Status | None = Query(default=None),
    service: ComplaintService = Depends(_get_service),
) -> dict[str, Any]:
    """Filter by category, priority, status; paginate (page, page_size ≤ 100); return total."""
    return await service.list_complaints(
        page=page,
        page_size=page_size,
        category=category,
        priority=priority,
        status=status,
    )


@router.patch("/complaints/{complaint_id}/status", response_model=ComplaintResponse)
async def update_complaint_status(
    complaint_id: uuid.UUID,
    body: StatusUpdate,
    service: ComplaintService = Depends(_get_service),
) -> dict[str, Any]:
    """Enforce the state machine. Invalid transition → 409 naming the attempted transition."""
    result, error = await service.update_status(complaint_id, body.status)
    if error == "not_found":
        raise HTTPException(status_code=404, detail="Complaint not found")
    if error is not None:
        raise HTTPException(status_code=409, detail=error)
    return result  # type: ignore[return-value]


@router.get("/stats")
async def get_stats(
    response: Response,
    service: ComplaintService = Depends(_get_service),
) -> dict[str, Any]:
    """Aggregates, Redis-cached, TTL 30s, X-Cache: HIT|MISS."""
    stats, cache_hit = await service.get_stats()
    response.headers["X-Cache"] = "HIT" if cache_hit else "MISS"
    return stats


@router.get("/meta/providers")
async def get_providers(
    service: ComplaintService = Depends(_get_service),
) -> dict[str, Any]:
    """Active triage provider and the last 20 triage outcomes."""
    return await service.get_provider_info()
