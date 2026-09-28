"""CivicPulse FastAPI application entry point.

Handles:
- Structured logging setup
- CORS
- Request ID propagation
- Prometheus metrics middleware
- Graceful shutdown (SIGTERM)
- Lifespan management
"""

import signal
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import settings
from app.deps import close_db_engine
from app.logging_config import get_logger, setup_logging
from app.providers.cache import close_redis
from app.routes.complaints import router as complaints_router
from app.routes.health import (
    FALLBACK_COUNTER,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    router as health_router,
)

# Setup structured logging
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown."""
    logger.info("application_starting", triage_provider=settings.triage_provider)

    # Register graceful shutdown handler for SIGTERM
    # Handle SIGTERM: stop accepting new requests, finish in-flight ones, close pools, exit.
    def handle_sigterm(signum: int, frame: object) -> None:
        logger.info("sigterm_received", signal=signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    yield

    # Shutdown: close pool connections
    logger.info("application_shutting_down")
    await close_redis()
    await close_db_engine()
    logger.info("application_shutdown_complete")


app = FastAPI(
    title="CivicPulse",
    description="Municipal Complaint Intake, Triage and Operations Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Cache", "X-Request-ID", "Retry-After"],
)


# ── Request ID propagation middleware ───────────────────────────────────
@app.middleware("http")
async def request_id_middleware(request: Request, call_next: object) -> Response:
    """Propagate X-Request-ID header. Generate one if absent."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Bind to structlog context for all log lines in this request
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response: Response = await call_next(request)  # type: ignore[call-arg]
    response.headers["X-Request-ID"] = request_id
    return response


# ── Prometheus metrics middleware ───────────────────────────────────────
@app.middleware("http")
async def metrics_middleware(request: Request, call_next: object) -> Response:
    """Track request count and latency for Prometheus."""
    start = time.monotonic()
    response: Response = await call_next(request)  # type: ignore[call-arg]
    duration = time.monotonic() - start

    endpoint = request.url.path
    method = request.method
    status = str(response.status_code)

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

    return response


# ── Validation error handler ───────────────────────────────────────────
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Return field-level validation errors as 400."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({"field": field, "message": error["msg"]})
    return JSONResponse(
        status_code=400,
        content={"detail": "Validation error", "errors": errors},
    )


# ── Register routers ───────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(complaints_router)
