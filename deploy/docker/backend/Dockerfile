# =============================================================================
# Urban Heat Mitigation Platform - Backend Dockerfile (Production)
# Multi-stage build: builder -> runtime
# =============================================================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Install runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -m -s /bin/bash appuser && \
    mkdir -p /app /app/uploads /app/models /app/data && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copy wheels from builder
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY --chown=appuser:appuser backend/app ./app
COPY --chown=appuser:appuser backend/alembic.ini .
COPY --chown=appuser:appuser backend/alembic ./alembic

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

USER appuser
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--limit-max-requests", "10000", "--timeout-graceful-shutdown", "30"]
