# Urban Heat Mitigation Platform — Configuration Reference

**Version 1.0.0** | July 2026

---

## Table of Contents

1. [Environment Variables](#1-environment-variables)
2. [Database Configuration](#2-database-configuration)
3. [Redis Configuration](#3-redis-configuration)
4. [MinIO / S3 Configuration](#4-minio--s3-configuration)
5. [Celery Configuration](#5-celery-configuration)
6. [ML Model Configuration](#6-ml-model-configuration)
7. [Recommendation Configuration](#7-recommendation-configuration)
8. [Scenario Configuration](#8-scenario-configuration)
9. [Nginx Configuration](#9-nginx-configuration)
10. [Monitoring Configuration](#10-monitoring-configuration)
11. [Logging Configuration](#11-logging-configuration)
12. [Email Configuration](#12-email-configuration)
13. [Security Configuration](#13-security-configuration)

---

## 1. Environment Variables

All configuration is managed via environment variables. Set them in a `.env` file at the project root, or pass them directly to containers.

### 1.1 General

| Variable | Description | Default | Example |
|---|---|---|---|
| `ENVIRONMENT` | Runtime environment | `development` | `production` |
| `SECRET_KEY` | Django-style secret key for cryptographic signing | *(required)* | `openssl rand -hex 64` |
| `PROJECT_NAME` | Application display name | `Urban Heat Mitigation Platform` | `City Heat Watch` |
| `VERSION` | API version string | `1.0.0` | `1.2.3` |
| `DEBUG` | Enable debug mode (verbose errors, hot reload) | `false` | `true` |
| `TIMEZONE` | Default timezone for the application | `UTC` | `America/New_York` |
| `DEFAULT_LOCALE` | Default language/locale | `en` | `en` |

### 1.2 Database

| Variable | Description | Default | Example |
|---|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string (async) | *(required)* | `postgresql+asyncpg://uhmp:pass@db:5432/uhmp` |
| `DATABASE_SYNC_URL` | Synchronous connection string (for Alembic) | *(inferred from DATABASE_URL)* | `postgresql://uhmp:pass@db:5432/uhmp` |
| `DATABASE_POOL_SIZE` | Connection pool size | `10` | `20` |
| `DATABASE_MAX_OVERFLOW` | Overflow connections beyond pool_size | `20` | `40` |
| `DATABASE_POOL_TIMEOUT` | Seconds to wait for a connection | `30` | `60` |
| `DATABASE_POOL_RECYCLE` | Seconds before recycling a connection | `1800` | `3600` |
| `DATABASE_ECHO` | Log all SQL queries | `false` | `true` |
| `DATABASE_SSL_MODE` | SSL mode for connection | `prefer` | `require` |
| `DATABASE_STATEMENT_TIMEOUT` | Max execution time per statement (ms) | `30000` | `60000` |

### 1.3 Redis

| Variable | Description | Default | Example |
|---|---|---|---|
| `REDIS_URL` | Redis connection string | *(required)* | `redis://:password@redis:6379/0` |
| `REDIS_SOCKET_TIMEOUT` | Socket timeout in seconds | `5` | `10` |
| `REDIS_RETRY_ON_TIMEOUT` | Retry on timeout | `true` | `false` |
| `REDIS_HEALTH_CHECK_INTERVAL` | Health check interval in seconds | `30` | `60` |
| `REDIS_MAX_CONNECTIONS` | Maximum connections in pool | `50` | `100` |
| `REDIS_DB_CACHE` | Redis database number for cache | `0` | `1` |
| `REDIS_DB_SESSION` | Redis database number for sessions | `1` | `2` |
| `REDIS_DB_BROKER` | Redis database number for Celery broker | `2` | `3` |
| `REDIS_DB_RESULT` | Redis database number for Celery results | `3` | `4` |

### 1.4 MinIO / S3

| Variable | Description | Default | Example |
|---|---|---|---|
| `MINIO_ENDPOINT` | MinIO server endpoint | `localhost:9000` | `minio:9000` |
| `MINIO_ACCESS_KEY` | Access key (username) | *(required)* | `minioadmin` |
| `MINIO_SECRET_KEY` | Secret key (password) | *(required)* | *(64-char random string)* |
| `MINIO_SECURE` | Use HTTPS for MinIO | `false` | `true` |
| `MINIO_REGION` | S3 region | `us-east-1` | `eu-west-1` |
| `MINIO_BUCKET_RASTERS` | Bucket for raster data | `uhmp-rasters` | `city-heat-rasters` |
| `MINIO_BUCKET_MODELS` | Bucket for ML models | `uhmp-models` | `city-heat-models` |
| `MINIO_BUCKET_EXPORTS` | Bucket for user exports | `uhmp-exports` | `city-heat-exports` |
| `MINIO_BUCKET_TEMP` | Bucket for temporary/scratch data | `uhmp-temp` | `city-heat-temp` |

> **AWS S3 Note:** Set `MINIO_ENDPOINT` to `s3.amazonaws.com` and configure `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` instead of `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` to use native S3.

### 1.5 Celery

| Variable | Description | Default | Example |
|---|---|---|---|
| `CELERY_BROKER_URL` | Broker URL (defaults to `REDIS_URL` DB 2) | *(inferred)* | `redis://:pass@redis:6379/2` |
| `CELERY_RESULT_BACKEND` | Result backend URL (defaults to `REDIS_URL` DB 3) | *(inferred)* | `redis://:pass@redis:6379/3` |
| `CELERY_WORKER_CONCURRENCY` | Number of worker processes | `4` | `8` |
| `CELERY_WORKER_POOL` | Pool implementation | `prefork` | `threads` or `gevent` |
| `CELERY_TASK_SOFT_TIME_LIMIT` | Soft time limit per task (seconds) | `600` | `1800` |
| `CELERY_TASK_HARD_TIME_LIMIT` | Hard time limit per task (seconds) | `900` | `2700` |
| `CELERY_TASK_MAX_RETRIES` | Max retries for failed tasks | `3` | `5` |
| `CELERY_TASK_ACKS_LATE` | Acknowledge tasks after execution | `true` | `false` |
| `CELERY_TASK_REJECT_ON_WORKER_LOST` | Requeue task if worker lost | `true` | `false` |
| `CELERY_RESULT_EXPIRES` | Seconds before result expires | `86400` | `604800` |
| `CELERY_MAX_TASKS_PER_CHILD` | Tasks before worker restart (memory leak guard) | `1000` | `200` |

### 1.6 ML Models

| Variable | Description | Default | Example |
|---|---|---|---|
| `MODEL_DIR` | Directory for model storage | `/data/models` | `/opt/models` |
| `ACTIVE_MODEL_VERSION` | Currently active model version tag | `v1.0.0` | `v2.1.0-rc1` |
| `MODEL_TRAINING_TIMEOUT` | Max training time per model (seconds) | `7200` | `14400` |
| `MODEL_PREDICTION_BATCH_SIZE` | Batch size for inference | `1024` | `4096` |
| `MODEL_CACHE_TTL` | Cache prediction results (seconds) | `3600` | `7200` |
| `DRIFT_THRESHOLD` | Data drift threshold before model retrain alert | `0.15` | `0.10` |
| `DRIFT_CHECK_INTERVAL` | How often to check for drift (hours) | `24` | `12` |
| `FEATURE_STORE_URL` | Feature store connection (if using Feast) | *(optional)* | `feast://localhost:6565` |

### 1.7 Recommendations

| Variable | Description | Default | Example |
|---|---|---|---|
| `RECOMMENDATION_BUDGET_MIN` | Minimum budget for optimization (USD) | `10000` | `50000` |
| `RECOMMENDATION_BUDGET_MAX` | Maximum budget for optimization (USD) | `100000000` | `50000000` |
| `RECOMMENDATION_DEFAULT_BUDGET` | Default budget preset (USD) | `1000000` | `5000000` |
| `RECOMMENDATION_NUM_OPTIONS` | Number of alternative plans to generate | `5` | `10` |
| `RECOMMENDATION_CO2_PRICE` | Social cost of carbon (USD/tonne) | `51` | `190` |
| `RECOMMENDATION_DISCOUNT_RATE` | Discount rate for cost-benefit analysis | `0.03` | `0.05` |
| `RECOMMENDATION_MAINTENANCE_YEARS` | Years of maintenance included | `20` | `30` |
| `RECOMMENDATION_ENERGY_SAVINGS` | Average energy savings per °C reduction (USD/household/yr) | `150` | `200` |
| `RECOMMENDATION_HEALTH_SAVINGS` | Average health benefit per °C reduction (USD/person/yr) | `85` | `120` |

### 1.8 Scenario Simulation

| Variable | Description | Default | Example |
|---|---|---|---|
| `SCENARIO_MAX_RUN_TIME` | Max simulation run time (seconds) | `300` | `600` |
| `SCENARIO_DEFAULT_CONFIDENCE` | Default confidence level | `moderate` | `conservative` |
| `SCENARIO_COMPARISON_CACHE_TTL` | Cache comparison results (seconds) | `1800` | `3600` |
| `SCENARIO_MAX_INTERVENTIONS` | Max concurrent interventions per simulation | `10` | `20` |
| `SCENARIO_GRID_RESOLUTION` | Simulation grid resolution (meters) | `30` | `10` |

### 1.9 API & Frontend

| Variable | Description | Default | Example |
|---|---|---|---|
| `API_HOST` | API server host | `0.0.0.0` | `127.0.0.1` |
| `API_PORT` | API server port | `8000` | `443` |
| `API_WORKERS` | Number of uvicorn workers | `4` | `8` |
| `API_MAX_UPLOAD_SIZE` | Max upload file size (bytes) | `2147483648` (2 GB) | `1073741824` (1 GB) |
| `API_UPLOAD_TIMEOUT` | Upload timeout (seconds) | `3600` | `7200` |
| `VITE_API_URL` | Frontend API base URL | `http://localhost:8000` | `https://api.uhmp.example.com` |
| `VITE_MAPBOX_TOKEN` | MapLibre tile provider token | *(optional)* | `pk.eyJ1Ijoi...` |
| `VITE_DEFAULT_MAP_CENTER` | Default map center [lng, lat] | `[0, 0]` | `[-73.935, 40.730]` |
| `VITE_DEFAULT_MAP_ZOOM` | Default map zoom level | `10` | `12` |

### 1.10 Authentication & Security

| Variable | Description | Default | Example |
|---|---|---|---|
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` | `RS256` |
| `JWT_SECRET_KEY` | JWT signing key (HMAC) | *(required if HS256)* | `openssl rand -hex 64` |
| `JWT_PRIVATE_KEY_PATH` | Path to RSA private key (RS256) | *(required if RS256)* | `/etc/ssl/private/jwt_private.pem` |
| `JWT_PUBLIC_KEY_PATH` | Path to RSA public key (RS256) | *(required if RS256)* | `/etc/ssl/certs/jwt_public.pem` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (minutes) | `1440` (24h) | `60` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime (days) | `30` | `7` |
| `JWT_ISSUER` | JWT issuer claim | `uhmp` | `https://auth.uhmp.example.com` |
| `JWT_AUDIENCE` | JWT audience claim | `uhmp-api` | `https://api.uhmp.example.com` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `http://localhost:5173` | `https://uhmp.example.com,https://admin.uhmp.example.com` |
| `CORS_ALLOW_CREDENTIALS` | Allow credentials in CORS | `true` | `false` |
| `RATE_LIMIT_PER_MINUTE` | Max requests per minute per IP | `60` | `120` |
| `RATE_LIMIT_PER_HOUR` | Max requests per hour per IP | `1000` | `2000` |
| `RATE_LIMIT_UPLOAD_PER_HOUR` | Max uploads per hour per user | `10` | `20` |
| `SESSION_TIMEOUT_MINUTES` | Inactive session timeout | `480` | `120` |
| `PASSWORD_MIN_LENGTH` | Minimum password length | `12` | `16` |
| `MFA_ENABLED` | Require multi-factor authentication | `false` | `true` |
| `MAX_LOGIN_ATTEMPTS` | Max failed login attempts before lockout | `5` | `3` |
| `LOGIN_LOCKOUT_MINUTES` | Lockout duration after failed attempts | `15` | `30` |

### 1.11 Email

| Variable | Description | Default | Example |
|---|---|---|---|
| `SMTP_HOST` | SMTP server host | *(required for email)* | `smtp.sendgrid.net` |
| `SMTP_PORT` | SMTP server port | `587` | `465` |
| `SMTP_USER` | SMTP username | *(required)* | `apikey` |
| `SMTP_PASSWORD` | SMTP password | *(required)* | `SG.xxxxx` |
| `SMTP_USE_TLS` | Use TLS for SMTP | `true` | `true` |
| `EMAIL_FROM` | Sender email address | `noreply@uhmp.example.com` | `notifications@cityheat.gov` |
| `EMAIL_FROM_NAME` | Sender display name | `UHMP Platform` | `City Heat Watch` |
| `EMAIL_TEMPLATE_DIR` | Path to email templates | `app/templates/email` | `/etc/uhmp/email-templates` |

### 1.12 Monitoring & Logging

| Variable | Description | Default | Example |
|---|---|---|---|
| `SENTRY_DSN` | Sentry DSN for error tracking | *(optional)* | `https://key@o123.ingest.sentry.io/456` |
| `SENTRY_ENVIRONMENT` | Sentry environment tag | *(inferred from ENVIRONMENT)* | `production` |
| `SENTRY_SAMPLE_RATE` | Error sample rate (0.0–1.0) | `1.0` | `0.5` |
| `PROMETHEUS_MULTIPROC_DIR` | Prometheus multiprocess directory | `/tmp/prometheus` | `/var/run/prometheus` |
| `PROMETHEUS_ENABLED` | Enable Prometheus metrics endpoint | `true` | `false` |
| `OPENMETRICS_ENABLED` | Enable OpenMetrics format | `true` | `false` |
| `LOG_LEVEL` | Log level | `INFO` | `DEBUG` |
| `LOG_FORMAT` | Log format | `json` | `text` |
| `LOG_OUTPUT` | Log output destination | `stdout` | `file` |
| `LOG_FILE_PATH` | Path to log file (if LOG_OUTPUT=file) | `logs/uhmp.log` | `/var/log/uhmp/uhmp.log` |
| `LOG_MAX_BYTES` | Max log file size before rotation | `10485760` (10 MB) | `104857600` (100 MB) |
| `LOG_BACKUP_COUNT` | Number of rotated log files to keep | `5` | `30` |

### 1.13 Processing

| Variable | Description | Default | Example |
|---|---|---|---|
| `PROCESSING_MAX_CONCURRENT` | Max concurrent processing tasks | `4` | `8` |
| `PROCESSING_CLOUD_THRESHOLD` | Default cloud confidence threshold | `20` | `15` |
| `PROCESSING_ATM_CORRECTION` | Default atmospheric correction method | `6sv` | `dos` |
| `PROCESSING_AEROSOL_MODEL` | Default aerosol model | `urban` | `rural` |
| `PROCESSING_TILE_SIZE` | Processing tile size (pixels) | `256` | `512` |
| `PROCESSING_CACHE_DIR` | Processing cache directory | `/tmp/uhmp-cache` | `/data/cache` |
| `PROCESSING_CACHE_TTL` | Processing cache TTL (seconds) | `86400` | `604800` |

---

## 2. Database Configuration

### 2.1 Connection Pooling

The platform uses SQLAlchemy's async connection pooling via `asyncpg`.

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,       # default: 10
    max_overflow=settings.DATABASE_MAX_OVERFLOW,  # default: 20
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,  # default: 30
    pool_recycle=settings.DATABASE_POOL_RECYCLE,  # default: 1800
    echo=settings.DATABASE_ECHO,                  # default: False
    connect_args={
        "statement_cache_size": 0,                # Disable for asyncpg
        "ssl": settings.DATABASE_SSL_MODE,
    },
)
```

### 2.2 Migrations (Alembic)

```bash
# Create a migration
alembic revision --autogenerate -m "add_scene_metadata"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View history
alembic history
```

### 2.3 Backup

```bash
# Full backup
pg_dump -U uhmp -h localhost -Fc uhmp > /backups/uhmp_$(date +%Y%m%d).dump

# Restore
pg_restore -U uhmp -h localhost -d uhmp --clean /backups/uhmp_20260701.dump
```

### 2.4 PostGIS-Specific Configuration

```sql
-- Enable PostGIS (run once per database)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Spatial index creation (applied in migrations)
CREATE INDEX idx_scenes_geometry ON scenes USING GIST (geometry);
CREATE INDEX idx_hotspots_geometry ON hotspots USING GIST (geometry);
CREATE INDEX idx_scenes_acquisition_date ON scenes (acquisition_date);
CREATE INDEX idx_scenes_sensor ON scenes (sensor);
```

---

## 3. Redis Configuration

### 3.1 Caching

```python
# app/core/cache.py
from redis.asyncio import Redis

cache = Redis.from_url(
    settings.REDIS_URL,
    db=settings.REDIS_DB_CACHE,  # 0
    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
    health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
)
```

**Cache key conventions:**
- `scene:{id}:metadata` — Scene metadata (TTL: 1 hour)
- `scene:{id}:raster:{band}` — Band raster data (TTL: 30 min)
- `index:{scene_id}:{index_name}` — Spectral index (TTL: 1 hour)
- `lst:{scene_id}` — LST results (TTL: 1 hour)
- `prediction:{model_id}:{area_id}` — ML predictions (TTL: 2 hours)
- `user:{id}:session` — User session (TTL: 24 hours)
- `rate_limit:{ip}:{endpoint}` — Rate limit counters (TTL: 1 min)

### 3.2 Session Storage

```python
# app/core/session.py
from redis.asyncio import Redis

session_store = Redis.from_url(
    settings.REDIS_URL,
    db=settings.REDIS_DB_SESSION,  # 1
    decode_responses=True,
)
```

### 3.3 Task Queue (Celery Broker)

Configured in `app/tasks/celery_app.py` (see Section 5).

---

## 4. MinIO / S3 Configuration

### 4.1 Client Setup

```python
# app/core/storage.py
from minio import Minio

client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
    region=settings.MINIO_REGION,
)
```

### 4.2 Bucket Structure

```
uhmp-rasters/
  raw/              — Original uploaded scenes
    {scene_id}.tif
  processed/        — Preprocessed scenes
    {scene_id}/
      cloud_mask.tif
      surface_reflectance.tif
      lst.tif
  indices/          — Spectral indices
    {scene_id}/
      ndvi.tif
      ndbi.tif
      ndwi.tif
      ...

uhmp-models/
  xgboost/          — XGBoost model artifacts
    v1.0.0/
      model.json
      preprocessor.pkl
      metrics.json
  lightgbm/
    v1.0.0/
      model.txt
      ...
  catboost/
    v1.0.0/
      model.cbm
      ...
  ensemble/
    v1.0.0/
      ...

uhmp-exports/
  reports/          — Generated PDF reports
    {user_id}/
      report_20260701.pdf
  csv/              — CSV exports
    {user_id}/
      hotspots_20260701.csv
  geojson/          — GeoJSON exports
    {user_id}/
      hotspots_20260701.geojson

uhmp-temp/          — Temporary/scratch (TTL: 24h, auto-cleaned)
  uploads/
    {upload_id}/
  processing/
    {task_id}/
```

### 4.3 Retention Policy

| Bucket | Retention | Cleanup Strategy |
|---|---|---|
| `uhmp-rasters/raw` | Permanent (until user deletes) | User-initiated |
| `uhmp-rasters/processed` | Permanent | User-initiated |
| `uhmp-rasters/indices` | Transient (recomputable) | LRU eviction (30 days) |
| `uhmp-models` | Permanent (versioned) | Manual |
| `uhmp-exports` | 7 days | Automated cron job |
| `uhmp-temp` | 24 hours | Automated cron job |

---

## 5. Celery Configuration

### 5.1 App Initialization

```python
# app/tasks/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "uhmp",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.preprocessing",
        "app.tasks.indices",
        "app.tasks.lst",
        "app.tasks.uhi_detection",
        "app.tasks.prediction",
        "app.tasks.recommendation",
        "app.tasks.scenario",
        "app.tasks.reporting",
        "app.tasks.maintenance",
    ],
)

celery_app.conf.update(
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_pool=settings.CELERY_WORKER_POOL,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_HARD_TIME_LIMIT,
    task_max_retries=settings.CELERY_TASK_MAX_RETRIES,
    task_acks_late=settings.CELERY_TASK_ACKS_LATE,
    task_reject_on_worker_lost=settings.CELERY_TASK_REJECT_ON_WORKER_LOST,
    result_expires=settings.CELERY_RESULT_EXPIRES,
    worker_max_tasks_per_child=settings.CELERY_MAX_TASKS_PER_CHILD,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
)
```

### 5.2 Task Queues

| Queue | Purpose | Priority | Concurrency |
|---|---|---|---|
| `default` | General tasks | Normal | 2 |
| `high_priority` | Interactive (user-facing) tasks | High | 4 |
| `low_priority` | Batch/background tasks | Low | 1 |
| `ml_training` | Model training (GPU if available) | Low | 1 |
| `export` | Report/export generation | Normal | 2 |

**Routing configuration:**
```python
celery_app.conf.task_routes = {
    "app.tasks.preprocessing.*": {"queue": "high_priority"},
    "app.tasks.prediction.predict": {"queue": "high_priority"},
    "app.tasks.prediction.*": {"queue": "ml_training"},
    "app.tasks.reporting.*": {"queue": "export"},
    "app.tasks.maintenance.*": {"queue": "low_priority"},
}
```

### 5.3 Running Workers

```bash
# Default worker
celery -A app.tasks worker --loglevel=info --concurrency=4

# Specific queue worker
celery -A app.tasks worker --loglevel=info --queues=high_priority --concurrency=4

# Beat scheduler (periodic tasks)
celery -A app.tasks beat --loglevel=info

# Flower monitor
celery -A app.tasks flower --port=5555
```

### 5.4 Periodic Tasks (Celery Beat)

```python
# app/tasks/scheduler.py
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "check-model-drift": {
        "task": "app.tasks.maintenance.check_model_drift",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "cleanup-temp-files": {
        "task": "app.tasks.maintenance.cleanup_temp",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    "cleanup-exports": {
        "task": "app.tasks.maintenance.cleanup_exports",
        "schedule": crontab(hour=4, minute=0),  # Daily at 4 AM
    },
    "refresh-materialized-views": {
        "task": "app.tasks.maintenance.refresh_views",
        "schedule": crontab(hour=5, minute=0),  # Daily at 5 AM
    },
    "send-daily-summary": {
        "task": "app.tasks.notifications.daily_summary",
        "schedule": crontab(hour=8, minute=0),  # Daily at 8 AM
    },
}
```

---

## 6. ML Model Configuration

### 6.1 Model Registry

Models are registered in `app/ml/registry.py`. Each model implements the `BaseModel` interface:

```python
class BaseModel(ABC):
    @abstractmethod
    def train(self, X, y, **params): ...
    @abstractmethod
    def predict(self, X): ...
    @abstractmethod
    def predict_proba(self, X): ...
    @abstractmethod
    def explain(self, X): ...
    @abstractmethod
    def save(self, path): ...
    @classmethod
    @abstractmethod
    def load(cls, path): ...
    @abstractmethod
    def get_feature_importance(self): ...
    @abstractmethod
    def metrics(self): ...
```

### 6.2 Hyperparameters

Default hyperparameters for each model type:

**XGBoost:**
```json
{
  "n_estimators": 300,
  "max_depth": 8,
  "learning_rate": 0.05,
  "subsample": 0.8,
  "colsample_bytree": 0.8,
  "min_child_weight": 3,
  "gamma": 0.1,
  "reg_alpha": 0.01,
  "reg_lambda": 0.1,
  "random_state": 42,
  "n_jobs": -1,
  "tree_method": "hist"
}
```

**LightGBM:**
```json
{
  "n_estimators": 500,
  "max_depth": 10,
  "num_leaves": 63,
  "learning_rate": 0.03,
  "subsample": 0.8,
  "colsample_bytree": 0.8,
  "min_child_samples": 20,
  "reg_alpha": 0.01,
  "reg_lambda": 0.1,
  "random_state": 42,
  "n_jobs": -1,
  "boosting_type": "gbdt"
}
```

**CatBoost:**
```json
{
  "iterations": 500,
  "depth": 8,
  "learning_rate": 0.05,
  "l2_leaf_reg": 3,
  "border_count": 128,
  "random_seed": 42,
  "thread_count": -1,
  "loss_function": "RMSE",
  "verbose": 100
}
```

**Ensemble (Stacking):**
```json
{
  "base_models": ["xgboost", "lightgbm", "catboost"],
  "meta_model": "linear_regression",
  "cv_folds": 5,
  "use_probabilities": true
}
```

### 6.3 Drift Detection

The platform monitors feature drift using the **Population Stability Index (PSI)** and **Kolmogorov-Smirnov (KS) test**.

| Metric | Threshold | Action |
|---|---|---|
| PSI < 0.10 | No drift | Continue |
| 0.10 ≤ PSI < 0.25 | Moderate drift | Alert, schedule retrain |
| PSI ≥ 0.25 | Severe drift | Alert, disable model, trigger retrain |
| KS p-value < 0.05 | Significant distribution change | Flag for review |

### 6.4 Model Versioning

Models follow the same SemVer as the platform:
- **MAJOR**: Breaking changes to model API or feature set
- **MINOR**: New model types, feature additions
- **PATCH**: Hyperparameter tuning, retraining with new data

---

## 7. Recommendation Configuration

### 7.1 Strategy Definitions

Strategies are defined in `app/recommendation/strategies/`:

```python
# app/recommendation/strategies/green_roofs.py
StrategyConfig(
    id="green_roofs",
    name="Green Roofs",
    cost_per_m2=(15, 40),       # (min, max) USD/m²
    temp_reduction=(2, 5),      # (min, max) °C
    co_benefits={
        "stormwater": 0.8,
        "air_quality": 0.6,
        "biodiversity": 0.7,
        "energy": 0.9,
        "social": 0.4,
    },
    maintenance_multiplier=0.05,  # 5% of install cost per year
    lifetime_years=30,
    min_area_m2=100,
    max_slope_degrees=30,
    applicable_land_covers=["building"],
)
```

### 7.2 Optimization Parameters

The optimization uses a Pareto-front multi-objective approach:

| Parameter | Default | Description |
|---|---|---|
| `population_size` | 100 | Genetic algorithm population |
| `generations` | 200 | Number of optimization generations |
| `crossover_rate` | 0.8 | Crossover probability |
| `mutation_rate` | 0.1 | Mutation probability |
| `objective_weights` | {temp: 0.4, cost: 0.3, co_benefit: 0.2, speed: 0.1} | Objective function weights |
| `pareto_front_size` | 10 | Number of solutions on the Pareto front |

### 7.3 CO₂ Pricing

The social cost of carbon (SC-CO₂) is configurable via `RECOMMENDATION_CO2_PRICE`. Current EPA estimates (2026):

| Year | Low (3% avg) | High (2.5% avg) |
|---|---|---|
| 2025 | $57 | $212 |
| 2030 | $62 | $236 |
| 2050 | $85 | $360 |

---

## 8. Scenario Configuration

### 8.1 Simulation Engine

The scenario simulation uses a physics-informed empirical model based on:

```python
ΔT = Σ(α_i × A_i × I_i × C_i)
```
Where:
- `ΔT` = Temperature change (°C)
- `α_i` = Effectiveness coefficient for strategy `i`
- `A_i` = Area covered by strategy `i` (m²)
- `I_i` = Implementation intensity (0–1)
- `C_i` = Confidence multiplier (depending on confidence level)

### 8.2 Confidence Levels

| Level | Multiplier | Description |
|---|---|---|
| `conservative` | 0.7 | Pessimistic estimate — lower bound of effectiveness |
| `moderate` | 1.0 | Most likely estimate — mean effectiveness |
| `aggressive` | 1.3 | Optimistic estimate — upper bound, ideal conditions |

### 8.3 Template Definitions

Templates are registered in `app/scenario/templates.py`. See the Developer Guide for how to add new templates.

---

## 9. Nginx Configuration

### 9.1 Production Nginx Config

```nginx
# /etc/nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    multi_accept on;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format json escape=json '{'
        '"timestamp":"$time_iso8601",'
        '"remote_addr":"$remote_addr",'
        '"request":"$request",'
        '"status":$status,'
        '"body_bytes":$body_bytes_sent,'
        '"request_time":$request_time,'
        '"upstream_time":"$upstream_response_time",'
        '"xff":"$http_x_forwarded_for"'
    '}';
    access_log /var/log/nginx/access.log json;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 1000;
    client_max_body_size 2G;
    client_body_timeout 3600s;

    # Gzip
    gzip on;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;
    gzip_vary on;
    gzip_proxied any;

    # SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
    limit_req_zone $binary_remote_addr zone=upload:10m rate=10r/h;
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    # Upstreams
    upstream api_backend {
        least_conn;
        server api:8000 max_fails=3 fail_timeout=30s;
    }

    upstream frontend_static {
        server frontend:5173 max_fails=3 fail_timeout=30s;
    }

    # HTTP → HTTPS redirect
    server {
        listen 80;
        server_name uhmp.example.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name uhmp.example.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # HSTS
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

        # Content Security Policy
        add_header Content-Security-Policy "
            default-src 'self';
            script-src 'self' 'unsafe-inline' https://*.mapbox.com https://*.tile.openstreetmap.org;
            style-src 'self' 'unsafe-inline' https://*.mapbox.com;
            img-src 'self' data: blob: https://*.tile.openstreetmap.org https://*.mapbox.com;
            font-src 'self' data:;
            connect-src 'self' https://*.tile.openstreetmap.org https://*.mapbox.com;
            frame-src 'none';
            object-src 'none';
        " always;

        # API proxy
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://api_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_send_timeout 300s;

            # CORS preflight
            if ($request_method = 'OPTIONS') {
                add_header 'Access-Control-Allow-Origin' 'https://uhmp.example.com';
                add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS';
                add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept';
                add_header 'Access-Control-Max-Age' 86400;
                return 204;
            }
        }

        # API docs
        location /docs {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
        }

        location /openapi.json {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
        }

        # Upload endpoint (higher timeout, rate limit)
        location /api/v1/scenes/upload {
            limit_req zone=upload burst=2 nodelay;
            client_max_body_size 2G;
            client_body_timeout 3600s;
            proxy_pass http://api_backend;
            proxy_read_timeout 3600s;
            proxy_send_timeout 3600s;
        }

        # Static frontend
        location / {
            proxy_pass http://frontend_static;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Cache static assets
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
                expires 30d;
                add_header Cache-Control "public, immutable";
                proxy_pass http://frontend_static;
            }
        }

        # Monitoring
        location /metrics {
            limit_req zone=api burst=5;
            proxy_pass http://api_backend;
        }

        location /health {
            limit_req zone=api burst=5;
            proxy_pass http://api_backend;
        }
    }
}
```

---

## 10. Monitoring Configuration

### 10.1 Prometheus

**prometheus.yml:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: production

scrape_configs:
  - job_name: 'uhmp-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics
    scheme: http
    scrape_interval: 10s

  - job_name: 'celery'
    static_configs:
      - targets: ['celery_exporter:9808']
    scrape_interval: 30s

  - job_name: 'postgresql'
    static_configs:
      - targets: ['postgres_exporter:9187']
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis_exporter:9121']
    scrape_interval: 30s

  - job_name: 'minio'
    static_configs:
      - targets: ['minio:9000']
    metrics_path: /minio/v2/metrics/cluster
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx_exporter:9113']
    scrape_interval: 30s

  - job_name: 'node'
    static_configs:
      - targets: ['node_exporter:9100']
    scrape_interval: 30s
```

### 10.2 Grafana

**Pre-configured datasources:**
```yaml
# monitoring/grafana/datasources/datasources.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false
```

### 10.3 Loki (Log Aggregation)

```yaml
# monitoring/loki/loki-config.yml
auth_enabled: false
server:
  http_listen_port: 3100
ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
  chunk_idle_period: 15m
  max_chunk_age: 1h
schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h
storage_config:
  boltdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks
limits_config:
  retention_period: 720h  # 30 days
  reject_old_samples: true
  reject_old_samples_max_age: 168h
```

### 10.4 Key Metrics

| Metric | Type | Description | Alert Threshold |
|---|---|---|---|
| `uhmp_api_request_duration_seconds` | Histogram | API request latency | p99 > 5s |
| `uhmp_api_requests_total` | Counter | Total API requests | — |
| `uhmp_api_errors_total` | Counter | API error count | Rate > 5% |
| `uhmp_celery_tasks_total` | Counter | Total Celery tasks | — |
| `uhmp_celery_task_duration_seconds` | Histogram | Task execution time | p99 > 300s |
| `uhmp_celery_queue_depth` | Gauge | Current queue size | > 100 |
| `uhmp_db_connection_count` | Gauge | Active DB connections | > 80% of pool |
| `uhmp_db_query_duration_seconds` | Histogram | DB query latency | p99 > 1s |
| `uhmp_redis_memory_bytes` | Gauge | Redis memory usage | > 80% of maxmemory |
| `uhmp_storage_used_bytes` | Gauge | MinIO storage usage | > 85% of quota |
| `uhmp_model_drift_score` | Gauge | Current drift score | > 0.15 |

---

## 11. Logging Configuration

### 11.1 Structured Logging (JSON)

```python
# app/core/logging.py
import logging
import json
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger("uhmp")
    handler = logging.StreamHandler()

    if settings.LOG_FORMAT == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(module)s %(funcName)s %(lineno)d %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s:%(lineno)d — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.WARNING)

    return logger
```

### 11.2 Log Levels

| Level | Usage |
|---|---|
| `DEBUG` | Detailed debugging — SQL queries, variable dumps |
| `INFO` | Normal operation — task started/completed, user actions |
| `WARNING` | Unexpected but non-critical — retry attempts, slow queries |
| `ERROR` | Failure requiring attention — task failure, API 5xx |
| `CRITICAL` | System-wide failure — database down, out of disk space |

### 11.3 JSON Log Example

```json
{
  "timestamp": "2026-07-02T12:00:00Z",
  "level": "INFO",
  "name": "uhmp",
  "module": "tasks.preprocessing",
  "funcName": "run_preprocessing",
  "lineno": 42,
  "message": "Preprocessing completed",
  "scene_id": 123,
  "duration_seconds": 145.3,
  "pixels_processed": 1048576,
  "cloud_pct": 5.2
}
```

---

## 12. Email Configuration

### 12.1 SMTP Settings

Configure via environment variables (see Section 1.11).

### 12.2 Email Templates

Templates use Jinja2 and are stored in `app/templates/email/`:

```
email/
  base.html                  — Base layout template
  welcome.html               — Welcome email (new user)
  password_reset.html        — Password reset link
  invitation.html            — Account invitation
  report_ready.html          — Report generation complete
  alert_model_drift.html     — Model drift notification
  daily_summary.html         — Daily activity summary
  processing_complete.html   — Processing task complete
  export_ready.html          — Export download ready
```

### 12.3 Email Events

| Event | Template | Trigger |
|---|---|---|
| User registration | `welcome.html` | Account created |
| Password reset request | `password_reset.html` | Forgot password form |
| User invitation | `invitation.html` | Admin invites user |
| Report ready | `report_ready.html` | PDF generation complete |
| Model drift detected | `alert_model_drift.html` | Drift score > threshold |
| Daily summary | `daily_summary.html` | Celery beat |
| Processing complete | `processing_complete.html` | Async task done |
| Export ready | `export_ready.html` | Export generation complete |

---

## 13. Security Configuration

### 13.1 JWT Authentication

The platform supports both HMAC (HS256) and RSA (RS256) signing:

**HS256 (symmetric):**
```python
JWT_ALGORITHM = "HS256"
JWT_SECRET_KEY = "<random-64-byte-hex>"
```

**RS256 (asymmetric — recommended for production):**
```bash
# Generate key pair
openssl genrsa -out jwt_private.pem 2048
openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem
```

```python
JWT_ALGORITHM = "RS256"
JWT_PRIVATE_KEY_PATH = "/etc/ssl/private/jwt_private.pem"
JWT_PUBLIC_KEY_PATH = "/etc/ssl/certs/jwt_public.pem"
```

### 13.2 CORS

CORS is configured via the `CORS_ORIGINS` environment variable. In `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["Content-Disposition"],
    max_age=86400,
)
```

### 13.3 Rate Limiting

Applied at the Nginx level (see Section 9) and at the application level via `slowapi`:

```python
# app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    storage_uri=settings.REDIS_URL,
)

app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Per-endpoint overrides
@router.post("/upload")
@limiter.limit("10/hour")
async def upload_scene(...): ...
```

### 13.4 Password Policy

```python
# app/core/security.py
PASSWORD_POLICY = {
    "min_length": settings.PASSWORD_MIN_LENGTH,  # 12
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digit": True,
    "require_special_char": True,
    "max_consecutive_repeated": 3,
    "password_history": 5,  # Cannot reuse last 5 passwords
    "password_expiry_days": 90,  # Force reset every 90 days
}
```

---

*© 2026 Urban Heat Mitigation Platform. All rights reserved.*
*For configuration support, contact devops@uhmp.example.com*
