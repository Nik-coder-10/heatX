# =============================================================================
# Urban Heat Mitigation Platform - Celery Worker Dockerfile
# Multi-stage build for minimal size
# =============================================================================

FROM python:3.14-slim AS builder

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

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    C_FORCE_ROOT=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1001 appuser && \
    useradd -u 1001 -g appuser -m -s /bin/bash appuser && \
    mkdir -p /app /app/uploads /app/models /app/data && \
    chown -R appuser:appuser /app

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY --chown=appuser:appuser backend/app ./app

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD celery -A app.celery_worker status || exit 1

USER appuser

CMD ["celery", "-A", "app.celery_worker", "worker", "--loglevel=info", "--concurrency=4", "--max-tasks-per-child=100", "--time-limit=3600"]
