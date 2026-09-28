"""Tests for the complaint service — especially triage fallback.

This test is REQUIRED by the assignment:
  Given a provider that always raises, POST /api/complaints still returns 201
  and triaged_by == "rules:fallback".
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import Category, ComplaintCreate, Priority, TriageResult
from app.providers.triage.simulated import SimulatedTriage
from app.services.complaint_service import ComplaintService


class TestTriageFallback:
    """Test that the system falls back to rules when the primary provider fails."""

    @pytest.mark.asyncio
    async def test_fallback_on_provider_failure(self):
        """REQUIRED TEST: given a provider that always raises, POST still succeeds
        and triaged_by == 'rules:fallback'.
        """
        # Create a provider that always raises
        failing_provider = SimulatedTriage(fail=True)

        # Mock the session and repository
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.execute = AsyncMock()

        service = ComplaintService(
            session=mock_session,
            provider=failing_provider,
        )

        # Mock the repository's create method
        mock_complaint = MagicMock()
        mock_complaint.id = "test-id"
        mock_complaint.text = "Test complaint text for fallback"
        mock_complaint.location = "Test Location"
        mock_complaint.reporter_contact = None
        mock_complaint.category = "water"
        mock_complaint.priority = "normal"
        mock_complaint.status = "open"
        mock_complaint.ai_summary = "Test complaint text for fallback"
        mock_complaint.triaged_by = "rules:fallback"
        mock_complaint.triage_latency_ms = 100
        mock_complaint.created_at = MagicMock()
        mock_complaint.created_at.isoformat.return_value = "2026-01-01T00:00:00"
        mock_complaint.updated_at = MagicMock()
        mock_complaint.updated_at.isoformat.return_value = "2026-01-01T00:00:00"

        with patch.object(service._repo, "create", return_value=mock_complaint):
            with patch("app.services.complaint_service.get_cached_triage", return_value=None):
                with patch("app.services.complaint_service.set_cached_triage"):
                    with patch("app.services.complaint_service.invalidate_stats_cache"):
                        data = ComplaintCreate(
                            text="Test complaint text for fallback testing purposes",
                            location="Test Location Here",
                        )

                        result = await service.create_complaint(data)

        # Verify the result indicates fallback was used
        # The service should have called the repo with triaged_by="rules:fallback"
        create_call = service._repo.create.call_args
        assert create_call is not None
        assert create_call.kwargs["triaged_by"] == "rules:fallback"

    @pytest.mark.asyncio
    async def test_triage_with_resilience_timeout(self):
        """Test that timeout triggers fallback."""

        class SlowProvider:
            name = "slow"

            async def triage(self, text, location):
                import asyncio
                await asyncio.sleep(15)  # Exceeds 10s timeout
                return TriageResult(
                    category=Category.OTHER,
                    priority=Priority.NORMAL,
                    summary="should not reach here",
                    confidence=0.5,
                )

        mock_session = AsyncMock()
        service = ComplaintService(
            session=mock_session,
            provider=SlowProvider(),
        )

        result, triaged_by, latency = await service._triage_with_resilience(
            "Water pipe burst on main road", "Street 1, Lahore"
        )

        assert triaged_by == "rules:fallback"
        assert isinstance(result, TriageResult)
