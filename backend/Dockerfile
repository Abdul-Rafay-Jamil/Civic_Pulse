# Backend Dockerfile — multi-stage, pinned, non-root, exec-form CMD
# Stage 1: Builder — install dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Cache-friendly COPY order: requirements before source
COPY pyproject.toml ./
COPY app/ ./app/
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime — slim image, non-root user
FROM python:3.12-slim AS runtime

# Create non-root user
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid 1001 --create-home appuser

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY app/ ./app/

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Exec-form CMD — receives signals properly for graceful shutdown
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
