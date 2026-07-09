# Disaster Recovery Plan

## Recovery Objectives

| Metric | Target |
|--------|--------|
| Recovery Time Objective (RTO) | 1 hour |
| Recovery Point Objective (RPO) | 24 hours |
| Data Loss Tolerance | Up to 24 hours of data |

## Backup Strategy

### Database Backups

- **Frequency:** Daily at 2 AM UTC
- **Type:** Full PostgreSQL dump (custom format)
- **Retention:** 30 days
- **Storage:** Local + S3 (off-server)
- **Verification:** Automatic integrity check after each backup

```bash
# Create backup
./deploy/database/backup.sh

# Verify backup
gzip -t /backups/postgres/urbanheat_*.dump.gz
```

### Configuration Backups

- Docker Compose files (version-controlled in git)
- Environment variables (.env file backed up separately)
- Nginx configuration (version-controlled)
- Grafana dashboards (provisioned automatically)

## Recovery Procedures

### 1. Full System Recovery

```bash
# On a new server:
git clone <repository> /opt/urbanheat
cd /opt/urbanheat
cp .env.production .env
# Edit .env with credentials
sudo ./deploy/scripts/setup.sh
./deploy/scripts/deploy.sh prod --monitoring --pull
```

### 2. Database Recovery

```bash
# List available backups
ls -lh /backups/postgres/

# Restore from backup
./deploy/database/restore.sh /backups/postgres/urbanheat_20240101_020000.dump.gz

# Verify restoration
docker exec urbanheat-postgres psql -U urbanheat -d urbanheat -c "SELECT count(*) FROM users;"
```

### 3. Point-in-Time Recovery (if WAL archiving enabled)

```bash
# Restore to specific point in time
docker exec urbanheat-postgres pg_ctl promote -D /var/lib/postgresql/data
```

### 4. Container Recovery

```bash
# Rebuild and restart specific service
docker compose -f deploy/docker-compose.prod.yml up -d --build backend

# Full container rebuild
docker compose -f deploy/docker-compose.prod.yml down
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

## Failure Scenarios

### Database Failure

**Symptoms:** Backend returns 500 errors, health check fails for postgres.

**Response:**
1. Check PostgreSQL logs: `docker logs urbanheat-postgres --tail 100`
2. Attempt restart: `docker restart urbanheat-postgres`
3. If persistent, restore from latest backup
4. Verify data integrity after restore

### Backend Failure

**Symptoms:** API returns errors, health check fails.

**Response:**
1. Check backend logs: `docker logs urbanheat-backend --tail 100`
2. Restart backend: `docker compose restart backend`
3. If persistent, rebuild: `docker compose up -d --build backend`

### Redis Failure

**Symptoms:** Caching stops, Celery tasks fail.

**Response:**
1. Check Redis: `docker exec urbanheat-redis redis-cli ping`
2. Restart Redis: `docker restart urbanheat-redis`
3. Redis will recover from snapshot on restart

### Disk Full

**Symptoms:** Database stops, containers crash.

**Response:**
1. Check disk: `df -h`
2. Clean Docker: `docker system prune -f`
3. Remove old backups: `find /backups -mtime +30 -delete`
4. If urgent, add storage: resize volume/disk

## Communication Plan

| Severity | Response Time | Notify |
|----------|--------------|--------|
| Critical (platform down) | 15 min | All team + Slack |
| High (feature broken) | 1 hour | Engineering team |
| Medium (degraded) | 4 hours | Engineering lead |
| Low (cosmetic) | 24 hours | Team lead |

## Testing

- Monthly restore test from backup to verify integrity
- Quarterly full DR exercise
- Regular chaos engineering (kill random containers)

## Post-Incident

1. Document timeline of events
2. Identify root cause
3. Implement preventive measures
4. Update runbooks
5. Schedule follow-up review
