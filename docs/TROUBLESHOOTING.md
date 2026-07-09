# Urban Heat Mitigation Platform — Troubleshooting Guide

**Version 1.0.0** | July 2026

---

## Table of Contents

1. [Common Issues and Solutions](#1-common-issues-and-solutions)
   - Installation Issues
   - Database Issues
   - Backend Issues
   - Frontend Issues
   - ML / AI Issues
   - Performance Issues
   - Deployment Issues
2. [Health Check Troubleshooting](#2-health-check-troubleshooting)
3. [Log Analysis Guide](#3-log-analysis-guide)
4. [Debug Mode Instructions](#4-debug-mode-instructions)
5. [Support Channels](#5-support-channels)
6. [FAQ](#6-faq)

---

## 1. Common Issues and Solutions

### 1.1 Installation Issues

#### Issue 1: pip install -r requirements.txt fails with GDAL error

**Problem:** Installation fails with output like `ERROR: Could not build wheels for GDAL` or `gdal-config not found`.

**Cause:** GDAL C library is not installed on the system, or its version is incompatible with the Python GDAL binding.

**Solution:**

*Ubuntu/Debian:*
```
sudo apt install -y gdal-bin libgdal-dev
pip install --no-cache-dir GDAL==
pip install -r requirements.txt
```

*macOS:*
```
brew install gdal
export CPLUS_INCLUDE_PATH=/opt/homebrew/include
export C_INCLUDE_PATH=/opt/homebrew/include
pip install -r requirements.txt
```

*Windows:*
```
conda install -c conda-forge gdal=3.7
```

#### Issue 2: Docker Compose fails with port conflict

**Problem:** `docker compose up` fails with `port is already allocated` or `address already in use`.

**Cause:** Local PostgreSQL (5432), Redis (6379), or other services are already running on the required ports.

**Solution:**
```
sudo systemctl stop postgresql redis-server   # Linux
brew services stop postgresql@15 redis        # macOS
Stop-Service postgresql*, redis*              # Windows
```

#### Issue 3: Celery worker won't start

**Problem:** Celery exits immediately with `connection refused` or `unknown error`.

**Cause:** Redis is not running or the broker URL is incorrect.

**Solution:**
```
redis-cli ping
echo $CELERY_BROKER_URL
sudo systemctl start redis-server        # Linux
brew services start redis                # macOS
docker start uhmp-redis                  # Docker
```

#### Issue 4: Frontend shows blank page after npm run dev

**Problem:** Vite dev server starts but browser shows a blank white page with console errors.

**Cause:** Missing environment variables or incorrect API URL.

**Solution:**
```
cd frontend
cat .env
echo "VITE_API_URL=http://localhost:8000" > .env
rm -rf node_modules/.vite
npm run dev
```

### 1.2 Database Issues

#### Issue 5: Connection refused when connecting to PostgreSQL

**Problem:** Backend cannot connect to database.

**Cause:** PostgreSQL is not running, or it is running on a different port.

**Solution:**
```
pg_isready
sudo systemctl start postgresql          # Linux
brew services start postgresql@15        # macOS
net start postgresql-15                  # Windows
ss -tlnp | grep 5432
```

#### Issue 6: Alembic migration fails with "relation already exists"

**Problem:** Running `alembic upgrade head` fails with duplicate table errors.

**Cause:** Database has tables from a previous migration but Alembic state is out of sync.

**Solution:**
```
alembic stamp head
psql -U uhmp -d uhmp -c "DROP TABLE IF EXISTS alembic_version CASCADE;"
alembic upgrade head
```

#### Issue 7: PostGIS unknown geometry type error

**Problem:** Queries fail with geometry type errors.

**Cause:** Geometry column contains mixed or invalid geometry types.

**Solution:**
```sql
UPDATE scenes SET geometry = ST_MakeValid(geometry) WHERE NOT ST_IsValid(geometry);
ALTER TABLE scenes ADD CONSTRAINT chk_geometry_type
  CHECK (ST_GeometryType(geometry) IN ('ST_Polygon', 'ST_MultiPolygon'));
CREATE INDEX IF NOT EXISTS idx_scenes_geometry ON scenes USING GIST (geometry);
```

#### Issue 8: Database query timeout

**Problem:** API endpoints return 504 Gateway Timeout after 30+ seconds.

**Cause:** Missing indexes, large table scans, or inefficient queries.

**Solution:**
```sql
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

CREATE INDEX CONCURRENTLY idx_scenes_acquisition_date ON scenes (acquisition_date);
CREATE INDEX CONCURRENTLY idx_scenes_sensor ON scenes (sensor);
CREATE INDEX CONCURRENTLY idx_hotspots_severity ON hotspots (severity);

ANALYZE scenes, hotspots, predictions;
```

### 1.3 Backend Issues

#### Issue 9: API returns 500 Internal Server Error

**Problem:** API endpoints return HTTP 500 with no useful error message.

**Cause:** Unhandled exception in the backend.

**Solution:**
```
docker logs uhmp-api --tail 100
tail -100 logs/uhmp.log
export DEBUG=true
uvicorn app.main:app --reload
```

#### Issue 10: 429 Too Many Requests errors

**Problem:** API returns 429 status code for legitimate requests.

**Cause:** Rate limiting threshold exceeded (default 60 req/min/IP).

**Solution:**
```
# Increase rate limit in .env:
RATE_LIMIT_PER_MINUTE=120
```

#### Issue 11: File upload fails with 413 Request Entity Too Large

**Problem:** Uploading large satellite images fails with HTTP 413.

**Cause:** Nginx or API upload size limit is too low.

**Solution:**
```
# In .env:
API_MAX_UPLOAD_SIZE=4294967296  # 4 GB

# In nginx.conf:
client_max_body_size 4G;
client_body_timeout 3600s;
```

#### Issue 12: Scenes stuck in "Processing" status

**Problem:** Uploaded scenes remain in "Processing" status for hours.

**Cause:** Celery worker crashed or task queue is backed up.

**Solution:**
```
celery -A app.tasks inspect active
celery -A app.tasks inspect reserved
sudo systemctl restart uhmp-celery
celery -A app.tasks purge -f
curl -X POST http://localhost:8000/api/v1/scenes/1/preprocess
```

#### Issue 13: Object not JSON serializable error

**Problem:** API returns 500 with `TypeError: Object of type ndarray is not JSON serializable`.

**Cause:** Numpy array or other non-serializable type in API response.

**Solution:** Convert numpy values using `.item()` for scalars and `.tolist()` for arrays.

### 1.4 Frontend Issues

#### Issue 14: Map tiles not loading

**Problem:** MapLibre GL map shows only grey background.

**Cause:** Missing or invalid tile provider token.

**Solution:**
```
# Check if VITE_MAPBOX_TOKEN is set in frontend/.env
# Try incognito mode to rule out extension interference
```

#### Issue 15: Charts not rendering

**Problem:** ECharts components show blank areas.

**Cause:** Missing data, wrong chart configuration, or ECharts import issue.

**Solution:** Check browser console for errors, verify API returns data, clear browser cache.

#### Issue 16: React component not updating after state change

**Problem:** UI does not reflect updated data after API call.

**Cause:** Stale React state or missing dependency in useEffect.

**Solution:** Check effect dependencies, use React Query for automatic refetching, force re-render with key prop.

#### Issue 17: Build fails with TypeScript errors

**Problem:** `npm run build` fails with TypeScript compilation errors.

**Cause:** Type mismatches, missing type definitions.

**Solution:**
```
npx tsc --noEmit
npm install -D @types/geojson @types/leaflet
```

### 1.5 ML / AI Issues

#### Issue 18: Model predictions are consistently inaccurate

**Problem:** Predicted LST values differ significantly from observed values.

**Cause:** Model drift, insufficient training data, or feature distribution mismatch.

**Solution:**
```
curl http://localhost:8000/api/v1/models/drift
curl -X POST http://localhost:8000/api/v1/models/retrain
```

#### Issue 19: SHAP explainability fails

**Problem:** SHAP value computation fails with kernel width error.

**Cause:** Background dataset is too small or contains identical samples.

**Solution:** Use 100+ background samples. For tree models, use `shap.TreeExplainer` instead of `KernelExplainer`.

#### Issue 20: UHI detection returns no hotspots

**Problem:** Zero hotspot polygons in obviously warm areas.

**Cause:** Threshold multiplier too strict (default 1.5 SD).

**Solution:** Lower threshold to 1.0 SD or use percentile method at 90%.

#### Issue 21: Training fails with out-of-memory error

**Problem:** Model training crashes with CUDA OOM or system OOM.

**Cause:** Dataset too large or batch size too high.

**Solution:** Reduce batch size, use `tree_method="hist"` for XGBoost, reduce `max_bin` and `num_leaves` for LightGBM.

### 1.6 Performance Issues

#### Issue 22: API response time very slow

**Problem:** API endpoints take 5-10+ seconds to respond.

**Cause:** Missing database indexes, N+1 queries, unoptimized geospatial operations.

**Solution:** Enable `DATABASE_ECHO=true` to log queries, add indexes, use `selectinload` for relationships, cache frequently accessed data.

#### Issue 23: Map interaction is laggy

**Problem:** Panning and zooming the map is slow.

**Cause:** Too many vector features, high-resolution raster overlays.

**Solution:** Simplify polygons with `ST_SimplifyPreserveTopology`, use pyramid layers, enable MapLibre tile caching.

#### Issue 24: High memory usage by Celery workers

**Problem:** Celery worker memory grows over time until OOM.

**Cause:** Memory leaks in task processing.

**Solution:** Set `CELERY_MAX_TASKS_PER_CHILD=50`, ensure GDAL datasets are properly closed with `dataset = None`, free large arrays with `del`.

### 1.7 Deployment Issues

#### Issue 25: Docker container exits immediately

**Problem:** Container starts and immediately exits with code 1.

**Cause:** Missing environment variables or health check failure.

**Solution:**
```
docker logs uhmp-api
docker run --rm uhmp-api env | grep SECRET
```

#### Issue 26: Nginx 502 Bad Gateway

**Problem:** Nginx returns 502 for all requests.

**Cause:** Backend API is not running or unreachable.

**Solution:**
```
curl http://localhost:8000/health
tail -50 /var/log/nginx/error.log
```

#### Issue 27: SSL certificate expired

**Problem:** Browser shows "Your connection is not private" warning.

**Cause:** SSL certificate expired or self-signed.

**Solution:**
```
sudo certbot renew
echo | openssl s_client -servername uhmp.example.com -connect uhmp.example.com:443
```

#### Issue 28: Prometheus targets down

**Problem:** Prometheus shows DOWN for all targets.

**Cause:** Services not exposing metrics or network issues.

**Solution:** Check `curl http://localhost:8000/metrics`, verify prometheus.yml scrape configs.

#### Issue 29: Grafana shows No data

**Problem:** Grafana dashboards show "No data" for all panels.

**Cause:** Grafana not connected to Prometheus.

**Solution:** Check Grafana datasource configuration, verify Prometheus has data.

#### Issue 30: Disk space running low

**Problem:** "no space left on device" errors.

**Cause:** Docker volumes accumulating data, logs not rotated.

**Solution:**
```
docker system prune -af --volumes
find /var/log -name "*.log" -size +100M -exec truncate -s 0 {} \;
```

---

## 2. Health Check Troubleshooting

The health check endpoint at `/health` returns component status.

### 2.1 Health Check Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-07-02T12:00:00Z",
  "components": {
    "database": { "status": "connected", "latency_ms": 3 },
    "redis": { "status": "connected", "latency_ms": 1 },
    "minio": { "status": "connected", "latency_ms": 5 },
    "celery": { "status": "connected", "workers": 4 }
  },
  "uptime_seconds": 86400
}
```

### 2.2 Component Failures

| Component | Error | Possible Causes |
|---|---|---|
| database | disconnected | PostgreSQL not running, wrong DATABASE_URL |
| redis | disconnected | Redis not running, wrong REDIS_URL |
| minio | disconnected | MinIO not running, wrong credentials |
| celery | no_workers | No Celery workers running |

### 2.3 Diagnosing

```
curl -v http://localhost:8000/health
psql -U uhmp -h localhost -d uhmp -c "SELECT 1;"
redis-cli -h localhost ping
celery -A app.tasks status
```

---

## 3. Log Analysis Guide

### 3.1 Log Locations

| Component | Location |
|---|---|
| API (native) | logs/uhmp.log or stdout |
| API (Docker) | docker logs uhmp-api |
| Nginx | /var/log/nginx/access.log |
| PostgreSQL | /var/log/postgresql/postgresql-15-main.log |
| Celery | docker logs uhmp-celery-worker |
| MinIO | docker logs uhmp-minio |

### 3.2 Searching Logs

```
grep "ERROR" logs/uhmp.log
grep "scene_id":123 logs/uhmp.log
docker logs uhmp-api --since 2h | grep ERROR
```

### 3.3 Log Levels

| Level | Meaning | Action |
|---|---|---|
| DEBUG | Diagnostic info | No action |
| INFO | Normal operation | No action |
| WARNING | Minor issue | Review |
| ERROR | Failed operation | Investigate |
| CRITICAL | System failure | Immediate |

### 3.4 Common Patterns

```
WARNING:uhmp:Memory usage at 85%
WARNING:uhmp:Model drift detected: PSI=0.23
WARNING:uhmp:Slow query (12.3s)
ERROR:uhmp:Task preprocessing.run failed: FileNotFoundError
WARNING:uhmp:Database pool exhausted - 20/20 connections in use
```

---

## 4. Debug Mode Instructions

### 4.1 Enabling Debug Mode

```
export DEBUG=true
# Restart API server

# In frontend/.env:
VITE_DEBUG=true
```

### 4.2 Debug Endpoints

| Endpoint | Description |
|---|---|
| /debug/env | Show environment variables |
| /debug/routes | List registered routes |
| /debug/cache/{key} | Inspect Redis cache |
| /debug/tasks | List Celery tasks |
| /debug/models | Show loaded ML models |

### 4.3 Disable in Production

Debug mode exposes sensitive information. Always set `DEBUG=false` in production.

```
export DEBUG=false
curl http://localhost:8000/debug/env
# Expected: 404 Not Found
```

---

## 5. Support Channels

### 5.1 Documentation
- User Guide: USER_GUIDE.md
- Installation Guide: INSTALLATION.md
- Configuration Reference: CONFIGURATION.md
- API Docs: http://uhmp.example.com/docs

### 5.2 Contact

| Channel | Response Time |
|---|---|
| GitHub Issues | < 48 hours |
| Community Forum | < 24 hours |
| support@uhmp.example.com | 8 hours (business) |
| premium-support@uhmp.example.com | 1 hour (24/7) |
| enterprise@uhmp.example.com | 15 minutes (24/7) |

---

## 6. FAQ

**Q: How do I check the platform version?**
A: Visit the dashboard footer or call `GET /health` and check the `version` field.

**Q: How do I reset my password?**
A: On the login page, click "Forgot Password" and enter your email.

**Q: The upload progress bar is stuck at 99%?**
A: Large files may take minutes to validate. If it persists beyond 30 minutes, cancel and re-upload.

**Q: Can I run the platform without Docker?**
A: Yes. See INSTALLATION.md for native installation.

**Q: How do I contribute?**
A: See DEVELOPER_GUIDE.md for coding standards and contribution workflow.

---

*© 2026 Urban Heat Mitigation Platform. All rights reserved.*
*For support, contact support@uhmp.example.com*
