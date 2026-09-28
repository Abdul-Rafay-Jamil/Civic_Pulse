"""Complaint repository — persistence layer. All SQL lives here."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Complaint
from app.models import Category, Priority, Status


class ComplaintRepository:
    """Handles all database operations for complaints."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        text: str,
        location: str,
        reporter_contact: str | None,
        category: Category,
        priority: Priority,
        ai_summary: str | None,
        triaged_by: str,
        triage_latency_ms: int,
    ) -> Complaint:
        """Insert a new complaint and return it."""
        complaint = Complaint(
            id=uuid.uuid4(),
            text=text,
            location=location,
            reporter_contact=reporter_contact,
            category=category.value,
            priority=priority.value,
            status=Status.OPEN.value,
            ai_summary=ai_summary,
            triaged_by=triaged_by,
            triage_latency_ms=triage_latency_ms,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._session.add(complaint)
        await self._session.flush()
        await self._session.refresh(complaint)
        return complaint

    async def get_by_id(self, complaint_id: uuid.UUID) -> Complaint | None:
        """Fetch a single complaint by ID, or None."""
        result = await self._session.execute(
            select(Complaint).where(Complaint.id == complaint_id)
        )
        return result.scalar_one_or_none()

    async def list_complaints(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        category: Category | None = None,
        priority: Priority | None = None,
        status: Status | None = None,
    ) -> tuple[list[Complaint], int]:
        """Return a paginated, filterable list plus total count.

        Uses the ix_status_priority and ix_created_at indexes.
        """
        query = select(Complaint)
        count_query = select(func.count()).select_from(Complaint)

        if category is not None:
            query = query.where(Complaint.category == category.value)
            count_query = count_query.where(Complaint.category == category.value)
        if priority is not None:
            query = query.where(Complaint.priority == priority.value)
            count_query = count_query.where(Complaint.priority == priority.value)
        if status is not None:
            query = query.where(Complaint.status == status.value)
            count_query = count_query.where(Complaint.status == status.value)

        # Total count
        total_result = await self._session.execute(count_query)
        total = total_result.scalar_one()

        # Paginated items — ordered by created_at DESC (uses ix_created_at)
        offset = (page - 1) * page_size
        query = query.order_by(Complaint.created_at.desc()).offset(offset).limit(page_size)
        result = await self._session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def update_status(
        self, complaint_id: uuid.UUID, new_status: Status
    ) -> Complaint | None:
        """Update the status of a complaint. Returns the updated complaint or None."""
        now = datetime.now(timezone.utc)
        await self._session.execute(
            update(Complaint)
            .where(Complaint.id == complaint_id)
            .values(status=new_status.value, updated_at=now)
        )
        await self._session.flush()
        return await self.get_by_id(complaint_id)

    async def get_stats(self) -> dict[str, Any]:
        """Compute aggregate counts by category, priority, and status."""
        # By category
        cat_result = await self._session.execute(
            select(Complaint.category, func.count())
            .group_by(Complaint.category)
        )
        by_category = {row[0]: row[1] for row in cat_result.all()}

        # By priority
        pri_result = await self._session.execute(
            select(Complaint.priority, func.count())
            .group_by(Complaint.priority)
        )
        by_priority = {row[0]: row[1] for row in pri_result.all()}

        # By status
        status_result = await self._session.execute(
            select(Complaint.status, func.count())
            .group_by(Complaint.status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}

        # Total
        total_result = await self._session.execute(
            select(func.count()).select_from(Complaint)
        )
        total = total_result.scalar_one()

        return {
            "by_category": by_category,
            "by_priority": by_priority,
            "by_status": by_status,
            "total": total,
        }

    async def get_recent_triage_outcomes(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the last N triage outcomes for /api/meta/providers."""
        result = await self._session.execute(
            select(
                Complaint.id,
                Complaint.triaged_by,
                Complaint.triage_latency_ms,
                Complaint.created_at,
            )
            .order_by(Complaint.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "complaint_id": str(row[0]),
                "provider": row[1],
                "latency_ms": row[2],
                "fallback": "fallback" in (row[1] or ""),
                "timestamp": row[3].isoformat() if row[3] else None,
            }
            for row in result.all()
        ]

    async def complaint_exists_by_id(self, complaint_id: uuid.UUID) -> bool:
        """Check if a complaint exists."""
        result = await self._session.execute(
            select(func.count()).select_from(Complaint).where(Complaint.id == complaint_id)
        )
        return result.scalar_one() > 0
