# Scaling Guide

## Vertical Scaling (Single Server)

### Resource Allocation

| Service | Min vCPU | Min RAM | Max vCPU | Max RAM |
|---------|----------|---------|----------|---------|
| PostgreSQL | 2 | 2GB | 8 | 16GB |
| Redis | 1 | 512MB | 4 | 4GB |
| Backend | 2 | 2GB | 8 | 8GB |
| Worker | 2 | 2GB | 16 | 16GB |
| Frontend | 1 | 128MB | 2 | 512MB |
| Nginx | 1 | 256MB | 2 | 1GB |
| Prometheus | 1 | 1GB | 2 | 4GB |
| Grafana | 1 | 512MB | 2 | 2GB |

### Requirements by Scale

| Scale | Users | RAM | vCPU | Disk | Monthly API Calls |
|-------|-------|-----|------|------|-------------------|
| Small | < 100 | 8GB | 4 | 50GB | < 10K |
| Medium | 100-1K | 16GB | 8 | 100GB | 10K-100K |
| Large | 1K-10K | 32GB | 16 | 500GB | 100K-1M |
| Enterprise | 10K+ | 64GB+ | 32+ | 1TB+ | 1M+ |

## Horizontal Scaling

### Backend (FastAPI)

```yaml
# docker-compose.override.yml
backend:
  deploy:
    replicas: 3
```

```bash
# Scale backend
docker compose -f deploy/docker-compose.prod.yml up -d --scale backend=3
```

**Note:** Requires a load balancer for multi-replica (Nginx handles this).

### Workers (Celery)

```bash
# Scale workers
docker compose -f deploy/docker-compose.prod.yml up -d --scale worker=5
```

### Database

- Read replicas for heavy query loads
- Connection pooling with PgBouncer
- Partition large tables by date

```yaml
# Add PgBouncer for connection pooling
pgbouncer:
  image: edoburu/pgbouncer:latest
  environment:
    DB_HOST: postgres
    DB_USER: ${POSTGRES_USER}
    DB_PASSWORD: ${POSTGRES_PASSWORD}
    DB_NAME: ${POSTGRES_DB}
    POOL_MODE: transaction
    MAX_CLIENT_CONN: 100
    DEFAULT_POOL_SIZE: 20
```

### Redis

- Redis Cluster for high availability
- Separate instances for cache vs. Celery broker

## Performance Tuning

### Backend

```
# uvicorn workers = 2 * CPU cores
--workers=8
--limit-max-requests=10000
--timeout-graceful-shutdown=30
```

### PostgreSQL

```ini
shared_buffers = 25% of RAM
effective_cache_size = 50% of RAM
work_mem = 64MB
maintenance_work_mem = 256MB
max_connections = 100
```

### Nginx

```
worker_processes auto;
worker_connections 4096;
keepalive_timeout 65;
client_body_buffer_size 128k;
proxy_buffer_size 4k;
```

## Monitoring Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| API P95 latency | > 1s | > 3s |
| API error rate | > 2% | > 5% |
| DB connections | > 50 | > 80 |
| CPU usage | > 70% | > 90% |
| Memory usage | > 80% | > 95% |
| Disk usage | > 80% | > 90% |

## Load Testing

```bash
# Install k6
docker pull grafana/k6

# Run load test
docker run --rm -i grafana/k6 run - < deploy/tests/load-test.js
```
