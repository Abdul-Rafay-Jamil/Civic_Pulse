"""Health, readiness, and metrics routes.

/health — Liveness. Process is alive. Must NOT touch the database.
/ready  — Readiness. 200 only if Postgres and Redis are both reachable;
          503 naming the failed dependency.
/metrics — Prometheus text format.
"""

from fastapi import APIRouter, Response
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from app.logging_config import get_logger
from app.providers.cache import redis_health_check

logger = get_logger(__name__)

router = APIRouter(tags=["health"])

# ── Prometheus metrics ──────────────────────────────────────────────────
registry = CollectorRegistry()

REQUEST_COUNT = Counter(
    "civicpulse_request_total",
    "Total HTTP request count",
    ["method", "endpoint", "status"],
    registry=registry,
)

REQUEST_LATENCY = Histogram(
    "civicpulse_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    registry=registry,
)

TRIAGE_LATENCY = Histogram(
    "civicpulse_triage_duration_seconds",
    "Triage call latency in seconds",
    ["provider"],
    registry=registry,
)

FALLBACK_COUNTER = Counter(
    "civicpulse_triage_fallback_total",
    "Number of times triage fell back to rules",
    registry=registry,
)


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe. Process is alive. Must NOT touch the database.

    Kubernetes uses this for liveness — a failing liveness probe restarts the pod.
    """
    return {"status": "healthy"}


@router.get("/ready")
async def ready() -> Response:
    """Readiness probe. 200 only if Postgres and Redis are both reachable.

    503 naming the failed dependency. Kubernetes uses this for readiness —
    a failing readiness probe removes the pod from the Service.
    """
    from app.deps import check_db_health

    failures: list[str] = []

    # Check PostgreSQL
    db_ok = await check_db_health()
    if not db_ok:
        failures.append("postgres")

    # Check Redis
    redis_ok = await redis_health_check()
    if not redis_ok:
        failures.append("redis")

    if failures:
        detail = f"Dependencies unavailable: {', '.join(failures)}"
        logger.warning("readiness_check_failed", failures=failures)
        return Response(
            content=f'{{"status": "unhealthy", "detail": "{detail}"}}',
            status_code=503,
            media_type="application/json",
        )

    return Response(
        content='{"status": "healthy", "details": {"postgres": "ok", "redis": "ok"}}',
        status_code=200,
        media_type="application/json",
    )


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus text format metrics."""
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )
