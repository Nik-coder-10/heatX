#!/bin/bash
# =============================================================================
# Urban Heat Mitigation Platform - Environment File Generator
# Generates secure random values for production .env file
# Usage: ./deploy/scripts/generate-env.sh > .env
# =============================================================================

set -euo pipefail

echo "# ============================================================================="
echo "# Urban Heat Mitigation Platform - Generated Environment Variables"
echo "# Generated: $(date -u)"
echo "# WARNING: Keep this file secure! Never commit to version control!"
echo "# ============================================================================="
echo ""

# Database
POSTGRES_USER="urbanheat"
POSTGRES_PASSWORD=$(openssl rand -hex 32)
POSTGRES_DB="urbanheat"
POSTGRES_PORT=5432

echo "# ===== Database ====="
echo "POSTGRES_USER=$POSTGRES_USER"
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo "POSTGRES_DB=$POSTGRES_DB"
echo "POSTGRES_PORT=$POSTGRES_PORT"
echo ""

# JWT
SECRET_KEY=$(openssl rand -hex 64)

echo "# ===== JWT / Auth ====="
echo "SECRET_KEY=$SECRET_KEY"
echo "ALGORITHM=HS256"
echo "ACCESS_TOKEN_EXPIRE_MINUTES=30"
echo ""

# Redis
REDIS_PASSWORD=$(openssl rand -hex 32)

echo "# ===== Redis ====="
echo "REDIS_HOST=redis"
echo "REDIS_PORT=6379"
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
echo ""

# MinIO
MINIO_ACCESS_KEY=$(openssl rand -hex 16)
MINIO_SECRET_KEY=$(openssl rand -hex 32)

echo "# ===== MinIO (Object Storage) ====="
echo "MINIO_ENDPOINT=minio:9000"
echo "MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY"
echo "MINIO_SECRET_KEY=$MINIO_SECRET_KEY"
echo "MINIO_BUCKET=urbanheat-data"
echo ""

# URLs
echo "# ===== URLs ====="
echo "BACKEND_CORS_ORIGINS=[\"https://\$DOMAIN\"]"
echo "FRONTEND_URL=https://\$DOMAIN"
echo "BACKEND_URL=https://api.\$DOMAIN"
echo "API_V1_STR=/api/v1"
echo "DOMAIN=urbanheat.io"
echo ""

# Grafana
GRAFANA_PASSWORD=$(openssl rand -hex 16)

echo "# ===== Monitoring ====="
echo "GRAFANA_USER=admin"
echo "GRAFANA_PASSWORD=$GRAFANA_PASSWORD"
echo "SENTRY_DSN="
echo ""

# SMTP
echo "# ===== Email / SMTP ====="
echo "SMTP_TLS=True"
echo "SMTP_PORT=587"
echo "SMTP_HOST=smtp.sendgrid.net"
echo "SMTP_USER=apikey"
echo "SMTP_PASSWORD="
echo "EMAILS_FROM_EMAIL=noreply@\$DOMAIN"
echo "EMAILS_FROM_NAME=Urban Heat Mitigation Platform"
echo ""

# Celery
echo "# ===== Celery ====="
echo "CELERY_BROKER_URL=redis://:\$REDIS_PASSWORD@redis:6379/0"
echo "CELERY_RESULT_BACKEND=redis://:\$REDIS_PASSWORD@redis:6379/0"
echo "CELERY_WORKER_CONCURRENCY=4"
echo ""

# External APIs
echo "# ===== External APIs ====="
echo "BHUVAN_API_KEY="
echo "OPENWEATHER_API_KEY="
echo ""

echo "# ===== Version ====="
echo "APP_VERSION=1.0.0"
echo "ENVIRONMENT=production"
echo ""

echo "# ============================================================================="
echo "# IMPORTANT: Review and update the following before deploying:"
echo "# 1. Set DOMAIN to your actual domain"
echo "# 2. Add SMTP_PASSWORD for email notifications"
echo "# 3. Add BHUVAN_API_KEY if using ISRO data"
echo "# 4. Add OPENWEATHER_API_KEY for weather data"
echo "# 5. Add SENTRY_DSN for error tracking"
echo "# ============================================================================="
