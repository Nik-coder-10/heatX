# Urban Heat Mitigation Platform — Release Management

**Version 1.0.0** | July 2026

---

## Table of Contents

1. [Versioning Scheme](#1-versioning-scheme)
2. [Release Process](#2-release-process)
3. [Current Release: v1.0.0](#3-current-release-v100)
4. [Changelog](#4-changelog)
5. [Upgrade Guides](#5-upgrade-guides)
6. [Migration Notes](#6-migration-notes)
7. [Deprecation Policy](#7-deprecation-policy)
8. [Release Cadence](#8-release-cadence)

---

## 1. Versioning Scheme

The platform follows **Semantic Versioning (SemVer 2.0.0)**: `MAJOR.MINOR.PATCH`

### Format

```
v<MAJOR>.<MINOR>.<PATCH>[-<PRERELEASE>][+<BUILD>]
```

Examples: `v1.0.0`, `v1.2.3-rc.1`, `v2.0.0+build.20260701`

### Rules

| Component | Increment When | Example |
|---|---|---|
| **MAJOR** | Breaking API changes, breaking database schema changes, removal of deprecated features | v1.0.0 → v2.0.0 |
| **MINOR** | New features, new API endpoints, new ML models, new spectral indices (backward compatible) | v1.0.0 → v1.1.0 |
| **PATCH** | Bug fixes, performance improvements, security patches, documentation updates | v1.0.0 → v1.0.1 |

### Pre-release Labels

| Label | Meaning | Stability |
|---|---|---|
| `alpha.N` | Early development, unstable APIs | Experimental |
| `beta.N` | Feature-complete, testing phase | Unstable |
| `rc.N` | Release candidate, final testing | Stable (pending) |

### Backward Compatibility Guarantees

Within a MAJOR version:
- **API:** All public endpoints remain available (deprecation warnings added one MINOR version before removal).
- **Database schema:** Migrations are additive (new columns/tables may be added; existing ones are not removed).
- **Configuration:** Environment variable names and semantics remain stable.
- **ML model API:** Model loading/saving format remains compatible.
- **Frontend API client:** Generated TypeScript client remains compatible.

---

## 2. Release Process

### 2.1 Branching Strategy

```
main          ─────●────────────────────●─────────────► (stable releases)
                    \                  /
release/v1.0.0      └──●──●──●──────┘     (release branch)
                         \    /
develop                  ──●──●──●──●──●──► (integration branch)
                               \    /
feature/xxx                  ──●──●──        (feature branches)
```

| Branch | Purpose | Base Branch | Lifespan |
|---|---|---|---|
| `main` | Production-ready code | — | Permanent |
| `develop` | Integration branch for next release | `main` | Permanent |
| `release/v<version>` | Release stabilization | `develop` | Until release |
| `feature/<name>` | New feature development | `develop` | Feature duration |
| `fix/<issue>` | Bug fixes | `develop` or `main` | Fix duration |
| `hotfix/<issue>` | Urgent production fix | `main` | Fix duration |

### 2.2 Release Workflow

#### Step 1: Feature Freeze

```bash
# Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/v1.1.0

# Update version in all files
# - app/core/config.py: VERSION = "1.1.0"
# - frontend/package.json: "version": "1.1.0"
# - pyproject.toml: version = "1.1.0"
```

#### Step 2: Release Branch Testing

Run full test suite on release branch:

```bash
# Backend tests
pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=85

# Frontend tests
cd frontend && npm run test:coverage && npm run lint && npm run typecheck

# Integration tests
pytest tests/integration/ -v

# Security scan
bandit -r app/ -x tests/
npm audit --production

# Performance regression
locust -f tests/performance/locustfile.py --headless -u 100 -r 10 --run-time 5m
```

#### Step 3: Create Release Candidate

```bash
# Tag release candidate
git tag -a v1.1.0-rc.1 -m "Release candidate v1.1.0-rc.1"
git push origin v1.1.0-rc.1

# Deploy to staging environment
./scripts/deploy-staging.sh v1.1.0-rc.1
```

#### Step 4: Release

```bash
# Merge release branch into main
git checkout main
git merge --no-ff release/v1.1.0

# Tag the release
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin main --tags

# Merge back into develop
git checkout develop
git merge --no-ff release/v1.1.0
git push origin develop

# Delete release branch
git branch -d release/v1.1.0
git push origin --delete release/v1.1.0
```

#### Step 5: Publish

Publish release artifacts:

- **GitHub Release:** Create release with changelog on GitHub.
- **Docker Images:** Push to container registry.
- **Documentation:** Deploy updated docs site.
- **Notification:** Send release announcement to community.

### 2.3 Hotfix Process

For critical production bugs:

```bash
# Create hotfix branch from main
git checkout main
git checkout -b hotfix/critical-fix

# Fix the issue
git add .
git commit -m "fix: critical database connection leak"

# Merge to main and develop
git checkout main
git merge --no-ff hotfix/critical-fix
git push origin main

git checkout develop
git merge --no-ff hotfix/critical-fix
git push origin develop

# Tag hotfix release
git tag -a v1.0.1 -m "Hotfix v1.0.1"
git push origin v1.0.1

# Delete hotfix branch
git branch -d hotfix/critical-fix
```

### 2.4 Changelog Guidelines

The changelog follows the [Keep a Changelog](https://keepachangelog.com) format:

```markdown
# Changelog

## [1.1.0] - 2026-09-15

### Added
- New spectral index: Enhanced Vegetation Index (EVI)
- Scenario comparison view — side-by-side baseline vs. simulated maps
- CSV export for spectral index values at sample points
- Admin panel configuration for ML model drift thresholds

### Changed
- Improved preprocessing speed by 40% using parallel tile processing
- Updated MapLibre GL from v3.6 to v4.1 for better performance
- Increased default upload limit from 1 GB to 2 GB

### Fixed
- Fixed memory leak in Celery worker after 100+ tasks
- Fixed incorrectly computed NDBI index formula
- Fixed 429 rate limiting errors for authenticated users
- Fixed PDF report generation timeout for large study areas

### Deprecated
- `GET /api/v1/scenes/status` — use `GET /api/v1/scenes/{id}` instead
- `ENABLE_LEGACY_ALGORITHM` environment variable

### Security
- Updated JWT library to v9.0.3 (CVE-2026-1234)
- Added rate limiting to file upload endpoint

## [1.0.0] - 2026-07-02
### Added
- Initial release
```

---

## 3. Current Release: v1.0.0

**Release Date:** July 2, 2026

### Highlights

- **Satellite imagery ingestion** — upload Landsat 8/9, Sentinel-2, and custom GeoTIFF imagery.
- **Preprocessing pipeline** — cloud masking (Fmask, Sen2Cor), atmospheric correction (6SV, DOS), resampling, reprojection.
- **Spectral indices** — NDVI, NDBI, NDWI, MNDWI, UI, BSI, SAVI, EVI, BI, NDMI.
- **Land Surface Temperature** — split-window (Landsat) and single-channel (Sentinel-2) algorithms.
- **UHI detection** — statistical thresholding, spatial clustering, severity classification (Low/Moderate/High/Extreme).
- **ML prediction** — XGBoost, LightGBM, CatBoost, and Ensemble models for LST and hotspot probability prediction.
- **Mitigation recommendations** — multi-objective optimization (NSGA-II) with budget constraints, 8 strategy types.
- **Scenario simulation** — 7 template types (green roofs, cool pavements, tree canopy, albedo, combined, climate, custom).
- **Model explainability** — SHAP values, feature importance, counterfactual explanations.
- **Reporting** — PDF reports, CSV exports, GeoJSON exports, GeoTIFF exports.
- **User management** — Role-based access (Admin, Analyst, Viewer), invitation system, audit logging.
- **Monitoring** — Prometheus metrics, Grafana dashboards, structured JSON logging, Sentry integration.
- **Infrastructure** — Docker Compose deployment (dev + prod), Nginx reverse proxy, SSL, rate limiting.

### Known Issues

| Issue | Impact | Workaround | Fix Version |
|---|---|---|---|
| Sentinel-2 L2A scenes > 500 MB may timeout during upload | Upload failures | Split scene into tiles before upload | v1.1.0 |
| SHAP KernelExplainer slow for > 1000 samples | Long wait times for explanations | Use TreeExplainer when possible | v1.1.0 |
| Map tile corruption on Firefox when GPU acceleration disabled | Visual artifacts | Use Chrome/Edge, or enable GPU accel in Firefox | v1.1.0 |
| PDF report images may be low-resolution on large study areas | Blurry maps | Reduce study area extent | v1.1.0 |

### Release Assets

| Asset | Link |
|---|---|
| Source code | https://github.com/yourorg/uhmp/releases/tag/v1.0.0 |
| Docker images | `docker pull ghcr.io/yourorg/uhmp-api:v1.0.0` |
| Documentation | https://docs.uhmp.example.com/v1.0.0 |
| API specification | https://docs.uhmp.example.com/v1.0.0/openapi.json |

---

## 4. Changelog

### v1.0.0 (2026-07-02)

#### Added
- Initial release of the Urban Heat Mitigation Platform
- Satellite imagery ingestion for Landsat 8/9, Sentinel-2, MODIS
- Cloud masking (Fmask, Sen2Cor) and atmospheric correction (6SV, DOS)
- 10 spectral indices: NDVI, NDBI, NDWI, MNDWI, UI, BSI, SAVI, EVI, BI, NDMI
- LST computation with split-window and single-channel algorithms
- UHI hotspot detection with severity classification
- XGBoost, LightGBM, CatBoost, and Ensemble ML models
- Budget-optimized mitigation recommendations (8 strategies)
- 7 scenario simulation templates
- SHAP explainability and counterfactual analysis
- PDF, CSV, GeoJSON, GeoTIFF exports
- User authentication and role-based access control
- Admin panel for user and system management
- Docker Compose development and production deployment
- Prometheus metrics and Grafana dashboards
- Structured JSON logging and Sentry error tracking
- Nginx reverse proxy with SSL, rate limiting, and security headers
- Comprehensive documentation (User Guide, Installation, Configuration, Troubleshooting, FAQ, Developer Guide)

---

## 5. Upgrade Guides

### 5.1 Upgrading from v0.5.0 to v1.0.0

#### Breaking Changes

**1. Database schema migration**

The database schema has changed significantly. Run:

```bash
# Backup existing database
pg_dump -U uhmp -h localhost -Fc uhmp > /backups/uhmp_v0.5.0_backup.dump

# Run migrations
alembic upgrade head

# Seed new required data
python scripts/seed.py --update
```

**2. Environment variable changes**

| v0.5.0 Variable | v1.0.0 Variable | Action |
|---|---|---|
| `DB_URL` | `DATABASE_URL` | Rename |
| `REDIS_HOST` / `REDIS_PORT` | `REDIS_URL` | Combine into single URL |
| `S3_*` | `MINIO_*` | Renamed with new structure |
| `JWT_SECRET` | `JWT_SECRET_KEY` | Rename |
| `MAPBOX_TOKEN` | `VITE_MAPBOX_TOKEN` | Moved to frontend |

**3. API endpoint changes**

| v0.5.0 Endpoint | v1.0.0 Endpoint |
|---|---|
| `POST /api/upload` | `POST /api/v1/scenes/upload` |
| `POST /api/process` | `POST /api/v1/scenes/{id}/preprocess` |
| `GET /api/status/{id}` | `GET /api/v1/scenes/{id}` |
| `POST /api/predict` | `POST /api/v1/predictions` |
| `POST /api/recommend` | `POST /api/v1/recommendations` |

**4. Docker Compose restructuring**

The docker-compose files have been restructured:
- `docker-compose.dev.yml` — Development with hot reload
- `docker-compose.prod.yml` — Production with monitoring stack

#### Upgrade Steps

```bash
# 1. Backup
pg_dump -U uhmp -h localhost -Fc uhmp > /backups/pre_upgrade.dump

# 2. Pull new code
git fetch origin
git checkout v1.0.0

# 3. Update .env file
# Compare with .env.example and update all changed variables
cp .env.example .env
# Edit .env with your values

# 4. Run database migrations
source venv/bin/activate
alembic upgrade head
python scripts/seed.py --update

# 5. Update frontend
cd frontend
rm -rf node_modules
npm install

# 6. Restart services
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# 7. Verify
curl http://localhost:8000/health
```

### 5.2 Upgrading from v0.3.0 to v1.0.0

#### Direct Upgrade Path

Since the jump from v0.3.0 to v1.0.0 spans multiple versions, a clean installation is recommended:

```bash
# 1. Export your data from v0.3.0
python scripts/export_v0.3_data.py --output /tmp/uhmp_v0.3_export

# 2. Full fresh installation of v1.0.0
# Follow INSTALLATION.md for your platform

# 3. Import v0.3.0 data
python scripts/import_legacy_data.py --input /tmp/uhmp_v0.3_export

# 4. Re-run preprocessing on imported scenes
python scripts/reprocess_imported_scenes.py
```

#### v0.3.0 → v0.4.0 Migration (if doing incremental)

```bash
# v0.3.0 → v0.4.0
git checkout v0.4.0
alembic upgrade head  # Added user roles, study areas
python scripts/seed.py --update
```

#### v0.4.0 → v0.5.0 Migration

```bash
git checkout v0.5.0
alembic upgrade head  # Added ML model registry, recommendations
```

#### v0.5.0 → v1.0.0 Migration

See Section 5.1 above.

---

## 6. Migration Notes

### 6.1 General Migration Principles

1. **Always backup before migrating.** Database backups are mandatory before any schema migration.
2. **Test migrations on a staging environment first.** Never run migrations directly on production without testing.
3. **Migrations are additive within a MAJOR version.** Tables, columns, and indexes are only added, never removed.
4. **Cross-MAJOR migrations may include data transformations.** These are documented in the upgrade guide.
5. **Rollback procedures are defined for each migration.** If a migration fails, follow the rollback steps.

### 6.2 v0.5.0 → v1.0.0 Migration Details

**Schema changes:**

| Change | Type | Details |
|---|---|---|
| `scenes` table: new columns | Additive | `cloud_cover`, `sensor`, `acquisition_date`, `metadata JSONB` |
| `study_areas` table | New | Replaces hardcoded area configuration |
| `predictions` table: model_version column | Additive | Tracks which model version produced the prediction |
| `recommendations` table: co2_savings column | Additive | New metric for carbon impact |
| `audit_log` table | New | User action audit trail |
| `user_sessions` table | New | Session management |
| `scenes.user_id` FK | Additive | Scene-to-user ownership |

**Data migration:**

```bash
python scripts/migrations/v0.5_to_v1.0_data_migration.py
```

This script:
1. Extracts sensor metadata from existing scene files.
2. Populates new columns (cloud_cover, sensor, acquisition_date).
3. Creates default study areas from scene extents.
4. Links unowned scenes to admin user.
5. Validates data integrity post-migration.

### 6.3 Rollback Procedure

```bash
# If migration v1.0.0 fails:

# 1. Restore database backup
pg_restore -U uhmp -h localhost -d uhmp --clean /backups/pre_upgrade.dump

# 2. Revert code
git checkout v0.5.0

# 3. Restore .env
cp /backups/env_v0.5.0 .env

# 4. Restart services
docker compose -f docker-compose.v0.5.yml up -d

# 5. Verify
curl http://localhost:8000/health
```

---

## 7. Deprecation Policy

### 7.1 API Deprecation

1. **Announcement:** Deprecated endpoints are marked with a `Deprecation` header and logged as warnings.
2. **Timeline:** Endpoints are deprecated for **one MINOR version** before removal.
3. **Headers:**
   - `Deprecation: true` — The endpoint is deprecated.
   - `Sunset: Sat, 01 Nov 2026 00:00:00 GMT` — Date when the endpoint will be removed.

### 7.2 Configuration Deprecation

- Deprecated environment variables still work but generate startup warnings.
- They are removed after **two MINOR versions** from deprecation announcement.

### 7.3 Feature Deprecation

- Deprecated features remain functional but are not actively maintained.
- They are removed in the next MAJOR version.
- At least **6 months** notice is given for feature removal.

### 7.4 Currently Deprecated (v1.0.0)

| Item | Deprecated In | Removal In | Replacement |
|---|---|---|---|
| `GET /api/v1/scenes/status` | v1.0.0 | v1.2.0 | `GET /api/v1/scenes/{id}` |
| `ENABLE_LEGACY_ALGORITHM` env var | v1.0.0 | v1.2.0 | Use `PROCESSING_ATM_CORRECTION=legacy` |
| Python 3.10 support | v1.0.0 | v2.0.0 | Use Python 3.11+ |

---

## 8. Release Cadence

### 8.1 Schedule

| Release Type | Frequency | Timeline |
|---|---|---|
| **PATCH** (bug fixes) | As needed | 1–4 weeks after previous release |
| **MINOR** (features) | Quarterly | March, June, September, December |
| **MAJOR** (breaking) | Annually | July (mid-year) |

### 8.2 Upcoming Releases

| Version | Expected Date | Planned Features |
|---|---|---|
| v1.0.1 | July 2026 | Bug fixes from initial release |
| v1.1.0 | September 2026 | Sentinel-2 L2A optimization, EVI index, scenario comparison enhancements |
| v1.2.0 | December 2026 | Scheduled analysis, API rate limit dashboard, mobile-responsive UI |
| v2.0.0 | July 2027 | Real-time sensor integration, multi-city comparison, new ML architecture |

### 8.3 Long-Term Support (LTS)

- **v1.x** is designated as an LTS release series.
- LTS releases receive security patches for **2 years** after the next MAJOR release.
- v1.0.0 security support: until July 2028.

### 8.4 Release Communication

All releases are announced via:

1. **GitHub Releases:** https://github.com/yourorg/uhmp/releases
2. **Mailing list:** Subscribe at https://uhmp.example.com/newsletter
3. **Twitter/X:** @UHMP_Platform
4. **Community forum:** https://community.uhmp.example.com

---

*© 2026 Urban Heat Mitigation Platform. All rights reserved.*
*For release-related questions, contact releases@uhmp.example.com*
