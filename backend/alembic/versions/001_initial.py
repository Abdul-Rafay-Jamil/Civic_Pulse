"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    category_enum = sa.Enum(
        "water", "electricity", "sanitation", "roads", "streetlights", "other",
        name="category_enum",
    )
    priority_enum = sa.Enum("high", "normal", "low", name="priority_enum")
    status_enum = sa.Enum(
        "open", "in_progress", "resolved", "rejected",
        name="status_enum",
    )

    op.create_table(
        "complaints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("reporter_contact", sa.String(200), nullable=True),
        sa.Column("category", category_enum, nullable=False),
        sa.Column("priority", priority_enum, nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="open"),
        sa.Column("ai_summary", sa.String(140), nullable=True),
        sa.Column("triaged_by", sa.String(50), nullable=False),
        sa.Column("triage_latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # DB-level constraints matching app-level validation
        sa.CheckConstraint(
            "length(text) >= 10 AND length(text) <= 2000",
            name="ck_text_length",
        ),
        sa.CheckConstraint(
            "length(location) >= 3 AND length(location) <= 200",
            name="ck_location_length",
        ),
    )

    # Index on (status, priority) — serves the dashboard filter query:
    #   SELECT … WHERE status = ? AND priority = ? ORDER BY created_at
    op.create_index("ix_status_priority", "complaints", ["status", "priority"])

    # Index on created_at — serves the default chronological listing:
    #   SELECT … ORDER BY created_at DESC LIMIT ? OFFSET ?
    op.create_index("ix_created_at", "complaints", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_created_at", table_name="complaints")
    op.drop_index("ix_status_priority", table_name="complaints")
    op.drop_table("complaints")
    op.execute("DROP TYPE IF EXISTS category_enum")
    op.execute("DROP TYPE IF EXISTS priority_enum")
    op.execute("DROP TYPE IF EXISTS status_enum")
