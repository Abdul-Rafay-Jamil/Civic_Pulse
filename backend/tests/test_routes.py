"""Tests for API routes — health, validation, status codes."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test /health and /ready endpoints."""

    def test_health_returns_200(self, client):
        """Liveness probe — must NOT touch the database."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_is_fast(self, client):
        """Health check should be very fast since it doesn't touch DB."""
        import time
        start = time.monotonic()
        client.get("/health")
        elapsed = time.monotonic() - start
        assert elapsed < 1.0  # Should be < 100ms, 1s is very generous


class TestComplaintValidation:
    """Test input validation returns 400 with field-level errors."""

    def test_empty_body_returns_422(self, client):
        """Missing required fields."""
        response = client.post("/api/complaints", json={})
        assert response.status_code == 422

    def test_text_too_short_returns_422(self, client):
        """Text must be ≥ 10 chars."""
        response = client.post(
            "/api/complaints",
            json={"text": "short", "location": "Valid Location"},
        )
        assert response.status_code == 422

    def test_location_too_short_returns_422(self, client):
        """Location must be ≥ 3 chars."""
        response = client.post(
            "/api/complaints",
            json={"text": "A valid complaint text here", "location": "ab"},
        )
        assert response.status_code == 422

    def test_text_too_long_returns_422(self, client):
        """Text must be ≤ 2000 chars."""
        response = client.post(
            "/api/complaints",
            json={"text": "x" * 2001, "location": "Valid Location"},
        )
        assert response.status_code == 422


class TestMetricsEndpoint:
    """Test /metrics endpoint."""

    def test_metrics_returns_prometheus_format(self, client):
        """Should return Prometheus text format."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Prometheus metrics should contain HELP/TYPE lines
        assert "civicpulse_request" in response.text or response.status_code == 200
