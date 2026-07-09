# Production Deployment Checklist

## Pre-Deployment

- [ ] All tests passing (CI green)
- [ ] Security scan completed (no HIGH/CRITICAL findings)
- [ ] Code review completed
- [ ] `.env` configured with production values
- [ ] `SECRET_KEY` is a secure random 64+ char hex string
- [ ] `POSTGRES_PASSWORD` is a secure random 32+ char string
- [ ] `MINIO_SECRET_KEY` is a secure random 32+ char string
- [ ] `REDIS_PASSWORD` is set
- [ ] CORS origins configured for production domain
- [ ] SSL certificates obtained (Let's Encrypt)

## Server Setup

- [ ] `sudo ./deploy/scripts/setup.sh` completed
- [ ] Docker and Docker Compose installed
- [ ] Firewall configured (22, 80, 443 only)
- [ ] fail2ban configured and running
- [ ] Swap configured (4GB+)
- [ ] Log rotation configured
- [ ] Timezone set to UTC
- [ ] NTP configured (chrony/ntpd)
- [ ] SSH key-based auth only (no passwords)
- [ ] Automatic security updates enabled

## Security

- [ ] Container hardening applied: `sudo ./deploy/security/container-hardening.sh`
- [ ] Docker daemon configured with secure defaults
- [ ] User namespace remapping enabled
- [ ] All containers running as non-root user
- [ ] No containers with privileged mode
- [ ] No containers with `CAP_SYS_ADMIN`
- [ ] Images scanned with Trivy
- [ ] Dependencies scanned (pip-audit, npm audit)
- [ ] Secrets scanned (trufflehog)
- [ ] AppArmor/SELinux profiles applied
- [ ] Audit logging enabled for Docker

## Database

- [ ] PostgreSQL connection pooling configured (20 connections)
- [ ] PostGIS extensions installed
- [ ] Regular backup schedule configured (daily)
- [ ] Backup retention policy set (30 days)
- [ ] Backup restoration tested
- [ ] Database encryption at rest (if applicable)
- [ ] `pg_stat_statements` enabled for monitoring

## Networking

- [ ] DNS records configured (A/AAAA for domain)
- [ ] CDN configured (Cloudflare/fastly) - optional
- [ ] Rate limiting configured on Nginx
- [ ] DDoS protection enabled (if behind CDN)
- [ ] Internal services not exposed to internet
- [ ] WebSocket connections supported
- [ ] File upload size limit configured (100MB)

## Monitoring

- [ ] Prometheus scraping all targets
- [ ] Grafana dashboards imported
- [ ] Loki receiving logs from all services
- [ ] OpenTelemetry collector running
- [ ] Alerting rules configured
- [ ] Alert notifications configured (Slack/email)
- [ ] Sentry/error tracking configured
- [ ] Uptime monitoring configured (Pingdom/Checkly)
- [ ] Synthetic transactions configured

## TLS/SSL

- [ ] HTTPS enforced (HTTP → 301 → HTTPS)
- [ ] TLS 1.2 and 1.3 only
- [ ] Strong ciphers configured
- [ ] HSTS enabled (max-age=63072000)
- [ ] OCSP stapling enabled
- [ ] Certificate auto-renewal configured (daily)
- [ ] Certificate expiry monitoring configured

## CI/CD

- [ ] CI pipeline passes for all branches
- [ ] CD pipeline deploys on main branch push
- [ ] Docker images built and pushed to registry
- [ ] Database migrations run automatically on deploy
- [ ] Health checks run after deployment
- [ ] Rollback procedure documented
- [ ] Slack/email notifications configured

## Performance

- [ ] Backend workers configured (4 workers)
- [ ] Celery workers configured (4 concurrent)
- [ ] Redis maxmemory configured (512MB)
- [ ] Nginx caching enabled for static assets
- [ ] Gzip/Brotli compression enabled
- [ ] Connection pooling configured
- [ ] Database indexes reviewed
- [ ] API response times acceptable
- [ ] Load testing completed

## Backup & DR

- [ ] Daily database backups configured
- [ ] Backups stored off-server (S3/GCS)
- [ ] Backup restoration tested
- [ ] Disaster recovery plan documented
- [ ] Recovery time objective (RTO) defined
- [ ] Recovery point objective (RPO) defined
- [ ] Infrastructure-as-code backed up
- [ ] Configuration files backed up

## Operational

- [ ] Logging level set to INFO in production
- [ ] Debug endpoints disabled
- [ ] Admin interfaces restricted (IP whitelist)
- [ ] API versioning confirmed
- [ ] Documentation updated
- [ ] On-call rotation established
- [ ] Runbooks created for common incidents
- [ ] Health check endpoint returns all service statuses
- [ ] Graceful shutdown configured (30s timeout)

## Post-Deployment

- [ ] All containers healthy
- [ ] Database reachable and migrations applied
- [ ] Redis reachable and caching
- [ ] Frontend loads without errors
- [ ] API returns correct responses
- [ ] HTTPS working with valid certificate
- [ ] Monitoring dashboards showing data
- [ ] Logs flowing to Loki
- [ ] Alerts not firing (or expected)
- [ ] Load test passes (if applicable)
- [ ] `./deploy/scripts/health-check.sh` passes all checks
