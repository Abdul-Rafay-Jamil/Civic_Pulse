"""Tests for the status state machine and domain models."""

import pytest

from app.models import (
    Category,
    Priority,
    Status,
    TriageResult,
    ComplaintCreate,
    is_valid_transition,
    VALID_TRANSITIONS,
)


class TestStatusStateMachine:
    """Test the explicit transition table (not a chain of ifs)."""

    def test_open_to_in_progress_valid(self):
        assert is_valid_transition(Status.OPEN, Status.IN_PROGRESS) is True

    def test_open_to_rejected_valid(self):
        assert is_valid_transition(Status.OPEN, Status.REJECTED) is True

    def test_in_progress_to_resolved_valid(self):
        assert is_valid_transition(Status.IN_PROGRESS, Status.RESOLVED) is True

    def test_in_progress_to_rejected_valid(self):
        assert is_valid_transition(Status.IN_PROGRESS, Status.REJECTED) is True

    def test_open_to_resolved_invalid(self):
        """Cannot skip in_progress to go directly to resolved."""
        assert is_valid_transition(Status.OPEN, Status.RESOLVED) is False

    def test_resolved_is_terminal(self):
        """Resolved is terminal — cannot transition to anything."""
        for target in Status:
            assert is_valid_transition(Status.RESOLVED, target) is False

    def test_rejected_is_terminal(self):
        """Rejected is terminal — cannot transition to anything."""
        for target in Status:
            assert is_valid_transition(Status.REJECTED, target) is False

    def test_in_progress_to_open_invalid(self):
        """Cannot go backwards."""
        assert is_valid_transition(Status.IN_PROGRESS, Status.OPEN) is False

    def test_transition_table_completeness(self):
        """Every status has an entry in the transition table."""
        for status in Status:
            assert status in VALID_TRANSITIONS


class TestTriageResult:
    """Test TriageResult validation."""

    def test_valid_triage_result(self):
        result = TriageResult(
            category=Category.WATER,
            priority=Priority.HIGH,
            summary="Burst pipe flooding street",
            confidence=0.95,
        )
        assert result.category == Category.WATER
        assert result.priority == Priority.HIGH
        assert result.confidence == 0.95

    def test_summary_max_length(self):
        """Summary must be ≤ 140 chars."""
        with pytest.raises(Exception):
            TriageResult(
                category=Category.WATER,
                priority=Priority.HIGH,
                summary="x" * 141,
                confidence=0.9,
            )

    def test_confidence_bounds(self):
        """Confidence must be 0.0–1.0."""
        with pytest.raises(Exception):
            TriageResult(
                category=Category.WATER,
                priority=Priority.HIGH,
                summary="test",
                confidence=1.5,
            )

    def test_invalid_category_rejected(self):
        """Invalid category strings should be rejected."""
        with pytest.raises(Exception):
            TriageResult(
                category="invalid_category",  # type: ignore
                priority=Priority.HIGH,
                summary="test",
                confidence=0.9,
            )


class TestComplaintCreate:
    """Test input validation."""

    def test_text_too_short(self):
        with pytest.raises(Exception):
            ComplaintCreate(text="short", location="Valid Location")

    def test_text_too_long(self):
        with pytest.raises(Exception):
            ComplaintCreate(text="x" * 2001, location="Valid Location")

    def test_location_too_short(self):
        with pytest.raises(Exception):
            ComplaintCreate(text="A valid complaint text for testing", location="ab")

    def test_valid_complaint(self):
        c = ComplaintCreate(
            text="Water supply has been disrupted for two days",
            location="Block C, North Nazimabad",
            reporter_contact="0300-1234567",
        )
        assert c.text == "Water supply has been disrupted for two days"
        assert c.reporter_contact == "0300-1234567"


class TestAdditionalSchemasAndCoverage:
    """Test other schemas and helper functions to ensure complete coverage."""

    def test_seed_uuid_idempotent(self):
        from app.seed import SEED_COMPLAINTS, _seed_uuid
        assert len(SEED_COMPLAINTS) >= 30
        assert _seed_uuid(0) == _seed_uuid(0)
        assert _seed_uuid(1) != _seed_uuid(2)

    def test_cache_helpers(self):
        from app.providers.cache import _content_hash, get_triage_cache_stats
        h1 = _content_hash("water leak", "street 5")
        h2 = _content_hash("water leak", "street 5")
        assert h1 == h2
        stats = get_triage_cache_stats()
        assert "hits" in stats
        assert "misses" in stats

    def test_triage_factory(self):
        from app.providers.triage.factory import create_triage_provider
        from app.providers.triage.rules import RuleBasedTriage
        from app.providers.triage.simulated import SimulatedTriage
        assert isinstance(create_triage_provider("rules"), RuleBasedTriage)
        assert isinstance(create_triage_provider("simulated"), SimulatedTriage)
        with pytest.raises(ValueError):
            create_triage_provider("invalid_provider_name")

    def test_status_update_and_other_schemas(self):
        from app.models import (
            ErrorResponse,
            HealthResponse,
            ProviderInfo,
            StatsResponse,
            StatusUpdate,
            ValidationErrorDetail,
        )
        su = StatusUpdate(status=Status.IN_PROGRESS)
        assert su.status == Status.IN_PROGRESS

        sr = StatsResponse(by_category={}, by_priority={}, by_status={}, total=0)
        assert sr.total == 0

        pi = ProviderInfo(active_provider="simulated", recent_outcomes=[])
        assert pi.active_provider == "simulated"

        hr = HealthResponse(status="healthy", details={"db": "ok"})
        assert hr.status == "healthy"

        er = ErrorResponse(
            detail="error",
            errors=[ValidationErrorDetail(field="text", message="required")],
        )
        assert len(er.errors) == 1
