"""SQLAlchemy ORM model for the complaints table."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


class Complaint(Base):
    """Complaint database model — mirrors §2.3 schema exactly."""

    __tablename__ = "complaints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(
        Text,
        nullable=False,
        comment="10–2000 chars, enforced in DB and app",
    )
    location = Column(
        String(200),
        nullable=False,
        comment="3–200 chars",
    )
    reporter_contact = Column(String(200), nullable=True)
    category = Column(
        Enum("water", "electricity", "sanitation", "roads", "streetlights", "other", name="category_enum"),
        nullable=False,
    )
    priority = Column(
        Enum("high", "normal", "low", name="priority_enum"),
        nullable=False,
    )
    status = Column(
        Enum("open", "in_progress", "resolved", "rejected", name="status_enum"),
        nullable=False,
        server_default="open",
    )
    ai_summary = Column(String(140), nullable=True, comment="One line, ≤ 140 chars")
    triaged_by = Column(
        String(50),
        nullable=False,
        comment="llm:groq | llm:ollama | rules | rules:fallback",
    )
    triage_latency_ms = Column(Integer, nullable=False, comment="Triage call duration in ms")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # DB-level constraints matching the app-level validation
    __table_args__ = (
        CheckConstraint("length(text) >= 10 AND length(text) <= 2000", name="ck_text_length"),
        CheckConstraint("length(location) >= 3 AND length(location) <= 200", name="ck_location_length"),
        # Index on (status, priority) — serves the dashboard filter query:
        #   SELECT … WHERE status = ? AND priority = ? ORDER BY created_at
        Index("ix_status_priority", "status", "priority"),
        # Index on created_at — serves the default chronological listing:
        #   SELECT … ORDER BY created_at DESC LIMIT ? OFFSET ?
        Index("ix_created_at", "created_at"),
    )
