# Urban Heat Mitigation Platform - Deployment Guide

## Prerequisites

- Docker 24+ and Docker Compose 2.20+
- 8GB+ RAM, 4+ vCPUs, 50GB+ disk space
- Ubuntu 22.04+ (recommended) or Debian 12+
- Domain name (for HTTPS, optional for development)

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository> /opt/urbanheat
cd /opt/urbanheat
cp .env.production .env
# Edit .env with your configuration
vi .env
```

### 2. Deploy

**Development:**
```bash
./deploy/scripts/deploy.sh dev
```

**Production:**
```bash
./deploy/scripts/deploy.sh prod --monitoring
```

**Production with HTTPS:**
```bash
sudo ./deploy/scripts/init-letsencrypt.sh urbanheat.io admin@urbanheat.io
./deploy/scripts/deploy.sh prod --https --monitoring
```

### 3. Verify

```bash
./deploy/scripts/health-check.sh
```

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │     │   Backend    │     │    Worker    │
│  (React SPA) │────▶│  (FastAPI)   │────▶│  (Celery)    │
│    :80/443   │     │    :8000     │     │   (async)    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │           ┌────────┴────────┐           │
       │           │   PostgreSQL    │           │
       │           │  + PostGIS      │           │
       │           └────────┬────────┘           │
       │                    │                    │
       │           ┌────────┴────────┐           │
       └───────────┤     Nginx      ├───────────┘
                   │  Reverse Proxy │
                   └────────────────┘

         Monitoring Stack:
         Prometheus ── Grafana
         Loki ── Promtail
         OpenTelemetry Collector
```

## Docker Compose Files

| File | Purpose |
|------|---------|
| `deploy/docker-compose.dev.yml` | Development (hot-reload, debug tools) |
| `deploy/docker-compose.prod.yml` | Production (optimized, monitoring) |
| `deploy/docker-compose.https.yml` | Production with HTTPS overlay |

## Services

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| PostgreSQL | `urbanheat-postgres` | 5432 | Geospatial database |
| Redis | `urbanheat-redis` | 6379 | Cache & task broker |
| MinIO | `urbanheat-minio` | 9000 | Object storage |
| Backend | `urbanheat-backend` | 8000 | FastAPI application |
| Worker | `urbanheat-worker` | - | Celery async tasks |
| Beat | `urbanheat-beat` | - | Celery scheduler |
| Frontend | `urbanheat-frontend` | 80 | React SPA |
| Nginx | `urbanheat-nginx` | 80/443 | Reverse proxy |
| Prometheus | `urbanheat-prometheus` | 9090 | Metrics collection |
| Grafana | `urbanheat-grafana` | 3000 | Monitoring dashboards |
| Loki | `urbanheat-loki` | 3100 | Log aggregation |
| OTel | `urbanheat-otel` | 4317 | OpenTelemetry collector |

## Environment Variables

See `.env.production` for all variables with documentation.

### Required Variables

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | Database password (32+ chars) |
| `SECRET_KEY` | JWT signing key (64+ chars hex) |
| `MINIO_ACCESS_KEY` | MinIO access key |
| `MINIO_SECRET_KEY` | MinIO secret key (32+ chars) |
| `DOMAIN` | Domain for HTTPS certificates |

## Database

### Migrations

```bash
# Run migrations
./deploy/database/migrate.sh

# Create new migration
docker exec urbanheat-backend alembic revision --autogenerate -m "description"
```

### Backup

```bash
# Manual backup
./deploy/database/backup.sh

# Automated (daily at 2 AM via GitHub Actions)
```

### Restore

```bash
# List available backups
ls -lh /backups/postgres/

# Restore
./deploy/database/restore.sh /backups/postgres/urbanheat_20240101_020000.dump.gz

# Dry run (validate only)
./deploy/database/restore.sh --dry-run /backups/postgres/urbanheat_20240101_020000.dump.gz
```

## Monitoring

### Access

- **Grafana:** `https://your-domain/grafana/`
- **Prometheus:** Internal only (port 9090)

### Built-in Dashboards

1. **System Monitoring** - CPU, memory, disk, containers
2. **Application Monitoring** - API, ML, recommendations
3. **ML Model Monitoring** - Accuracy, drift, latency

### Alerting Rules

- Backend/DB/Redis down (critical)
- High error rate > 5%
- High latency P95 > 2s
- Memory/disk usage > 90%
- Model drift detected
- Failed login rate > 10/5m

## Security

### HTTPS

```bash
# Initial setup
sudo ./deploy/scripts/init-letsencrypt.sh yourdomain.com email@example.com

# Certificates auto-renew daily at 3 AM
```

### Container Hardening

```bash
# Apply security hardening
sudo ./deploy/security/container-hardening.sh

# Run security audit
sudo ./deploy/security/container-hardening.sh --check
```

### Firewall

```bash
# UFW rules are configured by setup.sh
# SSH: 22, HTTP: 80, HTTPS: 443
```

## Upgrade

```bash
# Pull latest code
git pull

# Rebuild and deploy
./deploy/scripts/deploy.sh prod --no-cache --pull --monitoring
```

## Troubleshooting

```bash
# Check health
./deploy/scripts/health-check.sh

# View logs
docker logs urbanheat-backend --tail 100
docker logs urbanheat-worker --tail 100
docker logs urbanheat-nginx --tail 100

# Follow logs
docker logs -f urbanheat-backend

# Check specific service
docker compose -f deploy/docker-compose.prod.yml logs backend

# Restart service
docker compose -f deploy/docker-compose.prod.yml restart backend

# Full restart
./deploy/scripts/deploy.sh prod
```
