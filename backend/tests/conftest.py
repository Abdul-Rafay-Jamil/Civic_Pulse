"""Shared test fixtures."""

import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Set test environment before any app imports (use setdefault to preserve CI env vars)
os.environ.setdefault("TRIAGE_PROVIDER", "simulated")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://civicpulse:civicpulse@localhost:5432/civicpulse")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.main import app
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


@pytest.fixture
def client() -> TestClient:
    """Synchronous test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def simulated_provider() -> SimulatedTriage:
    """Simulated triage provider for deterministic tests."""
    return SimulatedTriage()


@pytest.fixture
def failing_provider() -> SimulatedTriage:
    """Provider that always raises — for testing fallback."""
    return SimulatedTriage(fail=True)


@pytest.fixture
def rules_provider() -> RuleBasedTriage:
    """Rule-based provider."""
    return RuleBasedTriage()
