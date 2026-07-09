# UrbanHeatAI — Project State

## Epic 1: Core Infrastructure

### Feature 1.1 — Project Scaffolding
**Status:** ✅ Completed

- FastAPI project structure with `app/` package layout
- Configuration management via `pydantic-settings` (`app/core/config.py`)
- Database session management (`app/database/session.py`)
- Alembic initialized with initial (empty) migration
- SQLAlchemy 2.x declarative base with naming conventions (`app/database/base.py`)
- API versioning structure (`app/api/v1/`)

### Feature 1.2 — Enum System
**Status:** ✅ Completed

- All domain enums defined in `app/database/enums.py`
- Enums tested in `tests/test_enums.py` — **9 tests**

### Feature 1.3 — Database Mixins
**Status:** ✅ Completed

- `UUIDPrimaryKeyMixin` — UUID primary key
- `TimestampMixin` — created_at/updated_at with `to_dict()` helper
- `SoftDeleteMixin` — soft_delete/restore/is_deleted/is_active_record with aliases
- `AuditMixin` — created_by/updated_by columns (relationships deferred)
- `BaseModel` — composite mixin (UUID PK + Timestamps + Soft Delete)
- All mixins tested in `tests/test_mixins.py` — **8 tests**

### Feature 1.4 — Role System
**Status:** ✅ Completed

- `Role` model (`app/models/role.py`) — uses `BaseModel` mixin
- Role seeded via `UserRole` enum (`ADMIN, RESEARCHER, PLANNER, VIEWER`)
- Idempotent seeding function (`app/seed/roles.py`)
- Role model tested in `tests/test_role.py` — **7 tests**

### Feature 1.5 — User System
**Status:** ✅ Completed

- `User` model (`app/models/user.py`) — production-grade with all required fields
- Fields: id, email, username, hashed_password, first_name, last_name, full_name,
  phone, profile_image_url, is_active, is_verified, last_login, role_id (FK),
  deleted_at, created_at, updated_at
- Unique constraints on email and username
- Indexed email and username
- Role relationship via FK to `roles.id`
- Relationships to Project and Report (forward references)
- Added docstrings and type hints
- User model tested in `tests/test_user.py` — **12 tests**

### Feature 1.6 — City System
**Status:** ✅ Completed

- City model (`app/models/city.py`) — production-grade with all required fields
- Fields: id, name, state, country, latitude, longitude, bounding_box (PostGIS),
  timezone, population, area_sq_km, climate_zone, deleted_at, created_at, updated_at
- Unique constraint on (name, country)
- Index on (latitude, longitude) for geospatial lookups
- SQLAlchemy 2.x Mapped/mapped_column syntax
- GeoAlchemy2 Geometry for PostGIS polygon boundary
- Added docstrings and type hints
- City model tested in `tests/test_city.py` — **12 tests**

### Feature 1.7 — Project System
**Status:** ✅ Completed

- Project model (`app/models/project.py`) — production-grade with all required fields
- Fields: id, name, description, owner_id (FK), city_id (FK), status (ProjectStatus
  enum), visibility (Visibility enum), start_date, end_date, deleted_at, created_at,
  updated_at
- Foreign keys to `users.id` (owner) and `cities.id` (geographic context)
- Indexes on owner_id, city_id, and (status, created_at) for common query patterns
- Default status: `ACTIVE`, default visibility: `PRIVATE`
- Soft delete support via `deleted_at`
- Model docstring and type hints
- Project model tested in `tests/test_project.py` — **13 tests**

## Epic 2: Domain Models

### Feature 2.1 — Satellite Image System
**Status:** ✅ Completed

- SatelliteImage model (`app/models/satellite_image.py`) — production-grade
- Fields: id, project_id (FK), provider (SatelliteProvider enum), sensor,
  capture_date, resolution, cloud_coverage, scene_id, bands_available, crs,
  footprint (PostGIS Polygon), storage_path, metadata (JSON), status
  (ProcessingStatus enum), deleted_at, created_at, updated_at
- Foreign key to `projects.id`
- Indexes on project_id, and (provider, capture_date) for temporal queries
- Geometry column (footprint) via GeoAlchemy2 for PostGIS polygon
- Model docstring and type hints
- SatelliteImage model tested in `tests/test_satellite_image.py` — **12 tests**

### Feature 2.2 — SatelliteImage Schemas
**Status:** ✅ Completed

- Schemas defined in `app/schemas/satellite_image.py`
- `SatelliteImageBase` — shared base fields with Pydantic v2 validators
- `SatelliteImageCreate` — creation input (inherits Base)
- `SatelliteImageUpdate` — partial update (all fields optional)
- `SatelliteImageResponse` — full response with `ConfigDict(from_attributes=True)`
- `SatelliteImageListResponse` — paginated list wrapper
- `SatelliteImageFilter` — query filters (project_id, provider, status, date range, etc.)
- `SatelliteImageSummary` — lightweight summary for list displays
- Validation rules: cloud_coverage [0, 100], resolution > 0, scene_id non-empty
- Pydantic v2 style (`model_config`, `Field()` descriptions, type hints)
- Schemas tested in `tests/test_satellite_image_schema.py` — **30 tests**

### Feature 2.3 — SatelliteImage Repository
**Status:** ✅ Completed

- `BaseRepository` in `app/repositories/base.py` — generic CRUD with SQLAlchemy 2.x
  `select()` syntax, soft-delete awareness, `get_by_id`, `create`, `update`, `delete`,
  `restore`, `count`, `exists` — designed for reuse by future repositories
- `SatelliteImageRepository` in `app/repositories/satellite_image.py` — extends
  `BaseRepository[SatelliteImage]` with domain-specific queries:
  - `get_by_scene_id()`, `get_by_project()`, `get_by_provider()`, `get_by_status()`
  - `list()` with dynamic filtering (provider, status, date range, cloud cover, etc.)
    and sorting (capture_date, created_at, cloud_coverage, resolution)
  - `paginate()` with filter support, total count, and offset/limit
  - `count_by_project()`, `count_by_status()` aggregates
- Filters applied via dynamic WHERE clause builder (`_build_filters`)
- Sorting via column-attribute map (`_SORT_MAP`)
- All query methods accept `include_deleted` flag for soft-delete overrides
- Repository tested in `tests/test_satellite_image_repository.py` — **47 tests**

### Feature 2.4 — SatelliteImage Service
**Status:** ✅ Completed

- `SatelliteImageService` in `app/services/satellite_image.py` — business logic layer
- CRUD operations: `create_image`, `get_image`, `update_image`, `soft_delete_image`, `restore_image`
- `validate_image` checks for duplicate scene_id before creation
- `change_processing_status` enforces valid status transitions (e.g., PENDING → QUEUED, not PENDING → COMPLETED)
- `attach_metadata` merges new metadata into existing (does not replace)
- `update_cloud_coverage` validates range [0, 100]
- `update_raster_path` validates non-empty string
- `get_statistics` returns total count, per-status breakdown, per-project breakdown
- Domain exceptions: `SatelliteImageError`, `DuplicateSceneIdError`, `ImageNotFoundError`,
  `InvalidStatusTransitionError`, `InvalidProviderError`, `InvalidMetadataError`, `InvalidRasterPathError`
- Service tested in `tests/test_satellite_image_service.py` — **39 tests**

### Feature 2.5 — SatelliteImage API Endpoints
**Status:** ✅ Completed

- 11 REST endpoints in `app/api/v1/endpoints/satellite_image.py`:
  - `POST /` — create satellite image (201)
  - `GET /search` — paginated search with filters
  - `GET /statistics` — aggregate stats (total, by-status, by-project)
  - `GET /project/{project_id}` — list by project
  - `GET /provider/{provider}` — list by provider
  - `GET /status/{status}` — list by processing status
  - `GET /{image_id}` — get by ID
  - `PATCH /{image_id}` — partial update
  - `DELETE /{image_id}` — soft delete (204)
  - `POST /{image_id}/restore` — restore soft-deleted
  - `GET /` — paginated list with filters
- Router registered in `app/api/v1/api.py` at prefix `/satellite`, tag `satellite`
- All endpoints use `SatelliteImageService` (never access repository directly)
- Auth via `get_current_user` dependency on all endpoints
- Proper exception handling: 404 (not found), 409 (duplicate scene_id), 400 (invalid transition/provider)
- Response models: `SatelliteImageResponse`, `SatelliteImageListResponse`
- Self-contained tests in `tests/test_satellite_image_api.py` with local model + repo + service + dependency overrides — **24 tests**

## Repository Layer Implemented

| Repository               | File                                   | Status |
|--------------------------|----------------------------------------|--------|
| BaseRepository           | `app/repositories/base.py`             | ✅     |
| SatelliteImageRepository | `app/repositories/satellite_image.py`  | ✅     |
| UserRepository           | `app/repositories/user.py`             | ⚠️     |

## Pydantic Schemas Implemented

| Schema                      | File                               | Status |
|-----------------------------|------------------------------------|--------|
| User schemas                | `app/schemas/user.py`              | ⚠️     |
| SatelliteImage schemas      | `app/schemas/satellite_image.py`   | ✅     |

## Database Models Implemented

| Model   | Table        | File                        | Mixins      | Status |
|---------|-------------|-----------------------------|-------------|--------|
| Role    | `roles`     | `app/models/role.py`        | BaseModel   | ✅     |
| User    | `users`     | `app/models/user.py`        | —           | ✅     |
| City    | `cities`    | `app/models/city.py`        | —           | ✅     |
| Project | `projects`  | `app/models/project.py`     | —           | ✅     |
| SatelliteImage | `satellite_images` | `app/models/satellite_image.py` | —     | ✅     |
| Report  | `reports`   | `app/models/report.py`      | —           | 📋     |
| AuditLog| `audit_logs`| `app/models/audit_log.py`   | —           | 📋     |

## Test Counts

| Test File          | Tests | Status |
|--------------------|-------|--------|
| `test_enums.py`    | 9     | ✅     |
| `test_mixins.py`   | 8     | ✅     |
| `test_role.py`     | 7     | ✅     |
| `test_user.py`     | 12    | ✅     |
| `test_city.py`     | 12    | ✅     |
| `test_project.py`  | 13    | ✅     |
| `test_satellite_image.py` | 12 | ✅     |
| `test_satellite_image_schema.py` | 30 | ✅     |
| `test_satellite_image_repository.py` | 47 | ✅     |
| `test_satellite_image_service.py`    | 39 | ✅     |
| `test_satellite_image_api.py`        | 24 | ✅     |
| **Total**          | **213**| ✅     |

## Known Technical Debt

1. **Model import cascade** — Models with cross-references (User ↔ Project ↔ City) cause
   import chains that break when any model in the chain has a bug. Several models
   (`city.py`, `project.py`, `report.py`) had missing `func` imports in their
   SQLAlchemy column definitions — these have been fixed.

2. **`full_name` vs `first_name`/`last_name`** — The `User` model has both
   `full_name` (legacy column, nullable) and `first_name`/`last_name` (new
   required columns). A future migration could drop `full_name` or make it a
   computed property.

3. **Alembic migrations** — The initial migration is blank (`pass`). No migrations
   have been auto-generated yet. A migration should be generated before first
   deployment.

4. **Missing model tests** — Report, AuditLog, HeatIsland, Prediction, Recommendation, and Simulation models have no tests.

5. **User schema outdated** — `app/schemas/user.py` uses Pydantic v1 style
   (`orm_mode=True`) and needs updating for new fields (`first_name`, `last_name`,
   `profile_image_url`, `last_login`) and migration to v2 style.

8. **Legacy repository pattern** — `UserRepository` and `TokenRepository` use
   deprecated `self.db.query()` API and integer IDs. They should be migrated to
   the new `BaseRepository` pattern (SQLAlchemy 2.x `select()`, UUID, soft-delete).

6. **GeoAlchemy2 + SQLite** — The City model's `bounding_box` column uses
   `Geometry("POLYGON", srid=4326)` which is PostgreSQL/PostGIS-specific. Tests
   with SQLite use a `Text` fallback type and cannot exercise the spatial
   functionality.

## Next Recommended Task

**Feature 2.6 — ProcessedImage Model & Repository**.

Consider generating an Alembic migration before any deployment.
