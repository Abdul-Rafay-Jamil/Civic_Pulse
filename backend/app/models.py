"""Domain models and enums for CivicPulse."""

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Category(str, enum.Enum):
    """Complaint category — assigned by triage."""

    WATER = "water"
    ELECTRICITY = "electricity"
    SANITATION = "sanitation"
    ROADS = "roads"
    STREETLIGHTS = "streetlights"
    OTHER = "other"


class Priority(str, enum.Enum):
    """Complaint priority — assigned by triage."""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class Status(str, enum.Enum):
    """Complaint lifecycle status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


# ── Status state machine ────────────────────────────────────────────────
# Explicit transition table — not a chain of ifs.
VALID_TRANSITIONS: dict[Status, set[Status]] = {
    Status.OPEN: {Status.IN_PROGRESS, Status.REJECTED},
    Status.IN_PROGRESS: {Status.RESOLVED, Status.REJECTED},
    Status.RESOLVED: set(),      # terminal
    Status.REJECTED: set(),      # terminal
}


def is_valid_transition(current: Status, target: Status) -> bool:
    """Return True if *current* → *target* is a legal status transition."""
    return target in VALID_TRANSITIONS.get(current, set())


# ── Triage result ────────────────────────────────────────────────────────
class TriageResult(BaseModel):
    """Structured output returned by every triage provider."""

    category: Category
    priority: Priority
    summary: str = Field(max_length=140)
    confidence: float = Field(ge=0.0, le=1.0)


# ── API schemas ──────────────────────────────────────────────────────────
class ComplaintCreate(BaseModel):
    """Schema for creating a new complaint (POST body)."""

    text: str = Field(min_length=10, max_length=2000)
    location: str = Field(min_length=3, max_length=200)
    reporter_contact: str | None = Field(default=None, max_length=200)


class StatusUpdate(BaseModel):
    """Schema for updating complaint status (PATCH body)."""

    status: Status


class ComplaintResponse(BaseModel):
    """Schema returned to the client for a single complaint."""

    id: uuid.UUID
    text: str
    location: str
    reporter_contact: str | None
    category: Category
    priority: Priority
    status: Status
    ai_summary: str | None
    triaged_by: str
    triage_latency_ms: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedComplaints(BaseModel):
    """Paginated list of complaints."""

    items: list[ComplaintResponse]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    """Aggregate statistics."""

    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_status: dict[str, int]
    total: int


class ProviderInfo(BaseModel):
    """Active triage provider information."""

    active_provider: str
    recent_outcomes: list[dict]


class HealthResponse(BaseModel):
    """Health/readiness check response."""

    status: str
    details: dict[str, str] = {}


class ValidationErrorDetail(BaseModel):
    """Single field-level validation error."""

    field: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str
    errors: list[ValidationErrorDetail] = []
