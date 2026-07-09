# Urban Heat Mitigation Platform — API Reference

## Base Information

| Property | Value |
|---|---|
| **Base URL** | `https://api.heatt.example.com/api/v1` |
| **Protocol** | HTTPS (TLS 1.2+) |
| **Content-Type** | `application/json` |
| **Accept** | `application/json` |
| **Auth** | Bearer JWT (access token) |

## Authentication

All authenticated endpoints require an `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are obtained via `POST /api/v1/auth/login`. Access tokens expire in 15 minutes. Refresh tokens expire in 7 days. Use `POST /api/v1/auth/refresh` to obtain new tokens.

## Error Codes

| Status | Code | Description |
|---|---|---|
| **400** | `BAD_REQUEST` | Malformed request syntax or invalid parameters |
| **401** | `UNAUTHORIZED` | Missing or invalid authentication credentials |
| **403** | `FORBIDDEN` | Authenticated but insufficient permissions |
| **404** | `NOT_FOUND` | Requested resource does not exist |
| **409** | `CONFLICT` | Resource conflict (duplicate, locked) |
| **422** | `VALIDATION_ERROR` | Request body fails schema validation |
| **429** | `RATE_LIMITED` | Too many requests |
| **500** | `INTERNAL_ERROR` | Unexpected server error |
| **502** | `BAD_GATEWAY` | Upstream service unavailable |
| **503** | `SERVICE_UNAVAILABLE` | Platform in maintenance mode |

## Rate Limits

| Endpoint Group | Rate Limit | Burst | Scope |
|---|---|---|---|
| **General API** | 100 req/s | 200 | Per IP + User |
| **Login** | 10 req/m | 15 | Per IP |
| **Refresh Token** | 20 req/m | 30 | Per IP |
| **Export** | 5 req/m | 10 | Per User |
| **Acquisition Schedule** | 10 req/h | 15 | Per Project |
| **ML Training** | 2 req/h | 3 | Per Project |
| **Scenario Simulation** | 10 req/m | 20 | Per User |

## Pagination

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number (1-indexed) |
| `per_page` | integer | 20 | Items per page (max 200) |
| `sort_by` | string | `created_at` | Sort field |
| `sort_order` | string | `desc` | `asc` or `desc` |

Response format: `{"data": [...], "pagination": {"page": 1, "per_page": 20, "total": 147, "total_pages": 8}}`

## Versioning

The API is versioned via URL path prefix `/api/v1/`. Breaking changes are introduced in new versions with a deprecation period of at least 6 months.

---

## Endpoints

---

### Tag: auth

#### POST /auth/login

Authenticate user credentials and receive JWT tokens.

**Request Body:** `{"email": "user@example.com", "password": "securePassword123"}`

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "dGhpcyBpcyBhIHJlZnJl...",
  "token_type": "Bearer",
  "expires_in": 900,
  "refresh_expires_in": 604800,
  "user": {"id": "a1b2c3d4-...", "email": "user@example.com", "name": "Jane Doe", "roles": ["user"]}
}
```
**Errors:** 400 (invalid format), 401 (invalid credentials), 429 (rate limit)

#### POST /auth/refresh

Obtain new tokens using refresh token. Body: `{"refresh_token": "..."}`. Returns access_token, refresh_token, token_type, expires_in.

#### POST /auth/logout

Invalidate refresh token. **Response 204.** **Errors:** 400, 401

#### POST /auth/change-password

Body: `{"current_password": "...", "new_password": "..."}`. **Response 204.** Errors: 400 (weak), 401 (wrong current).

#### POST /auth/forgot-password

Body: `{"email": "..."}`. **Response 204** (always success to prevent enumeration).

#### POST /auth/reset-password

Body: `{"token": "...", "new_password": "..."}`. **Response 204.** Errors: 400 (invalid/expired token).

---

### Tag: users

#### GET /users

List users (admin). Query: `page`, `per_page`, `sort_by`, `sort_order`, `search`, `role`.

**Response 200:**
```json
{
  "data": [{"id": "...", "email": "user@example.com", "name": "Jane Doe", "roles": ["user"], "is_active": true, "created_at": "2026-01-15T08:30:00Z", "last_login_at": "2026-07-01T14:22:00Z"}],
  "pagination": {"page": 1, "per_page": 20, "total": 45, "total_pages": 3}
}
```
**Errors:** 401, 403

#### POST /users

Create user (admin). Body: `{"email": "...", "password": "...", "name": "...", "roles": ["user"]}`. **Response 201.** Errors: 400, 401, 403, 409.

#### GET /users/{user_id}, PATCH /users/{user_id}, DELETE /users/{user_id}

CRUD. DELETE soft-deletes. **Response 204.** Errors: 400, 401, 403, 404.

---

### Tag: roles

#### GET /roles, POST /roles, GET /roles/{role_id}, PATCH /roles/{role_id}, DELETE /roles/{role_id}

Full CRUD. Admin only for mutations. System roles cannot be modified/deleted. Errors: 400, 401, 403, 404, 409.

---

### Tag: projects

#### GET /projects

List accessible projects. Query: `page`, `per_page`, `sort_by`, `sort_order`, `status`, `search`.

**Response 200:**
```json
{
  "data": [{"id": "p1a2b3c4-...", "name": "Mumbai UHI Assessment", "description": "Heat mitigation study", "bbox": {"min_lon":72.8,"min_lat":18.9,"max_lon":72.98,"max_lat":19.2}, "crs": "EPSG:4326", "status": "active", "scene_count": 12, "model_count": 3, "created_at": "2026-03-10T09:00:00Z", "owner_id": "a1b2c3d4-..."}],
  "pagination": {"page": 1, "per_page": 20, "total": 8, "total_pages": 1}
}
```

#### POST /projects

Create project. Body includes `name`, `description`, `bbox`, `crs`, `tags`. **Response 201.**

#### GET/PATCH/DELETE /projects/{project_id}

CRUD. DELETE cascades to all associated data. **Response 204.**

#### GET /projects/{project_id}/summary

Key metrics: LST stats, UHI intensity, hotspot count, severity distribution, best model, recommendation count.

---

### Tag: satellite

#### GET /satellite/scenes

List scenes. Query: `page`, `per_page`, `project_id`, `provider` (landsat8, landsat9, sentinel2, bhuvan), `date_from`, `date_to`, `cloud_cover_max`, `status`.

#### GET /satellite/scenes/{scene_id}

Scene details: bands, resolution, wavelengths, processing metadata (cloud mask, atmospheric correction, resampling).

#### DELETE /satellite/scenes/{scene_id}

Delete scene and all derived data. **Response 204.**

---

### Tag: satellite-acquisition

#### POST /acquisition/schedule

Schedule acquisition. Body: `{"project_id": "...", "provider": "landsat8", "aoi": {"type": "Polygon", "coordinates": [...]}, "date_from": "2025-01-01", "date_to": "2026-07-01", "max_cloud_cover": 20, "bands": ["red","green","blue","nir","swir1","swir2","tirs1","tirs2"]}`.

**Response 202:** `{"task_id": "acq-...", "status": "scheduled", "estimated_scenes": 18, "estimated_duration_seconds": 540}`

#### GET /acquisition/tasks

List tasks with progress (total/completed/failed scenes). Query: `page`, `per_page`, `status`, `project_id`.

#### GET /acquisition/tasks/{task_id}

Task status and results (scene_ids, total_size_mb).

#### POST /acquisition/tasks/{task_id}/cancel

Cancel running task. Errors: 400 (cannot cancel completed).

---

### Tag: gis

#### POST /gis/indices

Compute spectral indices. Body: `project_id`, `scene_ids`, `indices` (ndvi, ndwi, ndbi, nbri, ui, bsi), `overwrite`. **Response 202** with task_id.

#### GET /gis/indices/{project_id}

List computed indices. Query: `scene_id`, `index_type`. Returns min, max, mean, std, raster_url.

#### GET /gis/indices/{project_id}/timeseries

Time-series at point. Query: `lon`, `lat`, `index_type`, `date_from`, `date_to`.

---

### Tag: heat

#### POST /heat/detect

Detect UHI. Body: `project_id`, `scene_ids`, `lst_algorithm` (mono_window, split_window), `emissivity_method`, `uhi_threshold_std`, hotspot clustering (dbscan, eps, min_samples), `urban_rural_gradient`. **Response 202.**

#### GET /heat/results/{project_id}

UHI results: LST stats (mean, median, min, max, std), severity distribution with counts and areas, hotspot clusters with centers, urban-rural gradient.

#### GET /heat/severity-map/{project_id}

GeoJSON FeatureCollection of severity polygons. Query: `scene_id`, `simplify_tolerance`.

---

### Tag: ml-training

#### GET /ml/models

List models. Query: `page`, `per_page`, `project_id`, `model_type`, `status`.

#### POST /ml/train

Start training. Body: `project_id`, `name`, `config` including `model_types`, `ensemble_method`, `cross_validation`, `hyperparameter_search` (optuna trials), `feature_groups`, `target`, `explainability`. **Response 202.**

#### GET /ml/models/{model_id}

Model details: best_params, metrics (R2, RMSE, MAE, CV scores, MAPE), feature_importance, training_samples, duration.

#### DELETE /ml/models/{model_id}

Archive model. **Response 204.**

#### POST /ml/models/{model_id}/deploy

Deploy model to production inference. Errors: 400 if not completed.

#### GET /ml/training-jobs, GET /ml/training-jobs/{task_id}

List/get training job status.

---

### Tag: ml-inference

#### POST /ml/predict

Run inference. Body: `project_id`, `model_id`, `scene_ids`, `explain`, `output_format`. Returns predictions with severity distribution and SHAP explanations (global top features + local per-cell values).

#### POST /ml/predict/batch

Batch inference (async). **Response 202** with task_id.

#### GET /ml/drift

Drift detection. Query: `project_id`, `model_id`, `metric`. Returns data drift (PSI), concept drift (accuracy_delta), model drift (prediction distribution shift) with status/threshold.

---

### Tag: recommendations

#### POST /recommendations/generate

Generate recommendations. Body: `project_id`, `model_id`, `budget`, `intervention_types`, `constraints` (min_area, max_cost, exclude_landuse, prioritize_equity), `optimization` (method: knapsack, objective: maximize_cost_effectiveness). **Response 202.**

#### GET /recommendations/{project_id}

Ranked recommendations with cost, projected LST reduction, cost-effectiveness, co-benefits, equity metrics.

#### PATCH /recommendations/{project_id}/items/{recommendation_id}

Update item status (accepted/rejected).

#### POST /recommendations/{project_id}/export

Export as PDF/GeoJSON/CSV. Query: `format`. **Response 200** with download URL and expiry.

---

### Tag: scenarios

#### POST /scenarios/create

Create scenario. Body: `project_id`, `name`, `description`, `model_id`, `interventions` (type, parameters, area_constraint), `monte_carlo` (n_simulations, confidence_level, uncertainty_params). **Response 202** with task_id and scenario_id.

#### GET /scenarios/{project_id}, GET /scenarios/detail/{scenario_id}

List/get scenario results: baseline vs simulated LST, confidence intervals, severity shifts, population benefitted.

#### POST /scenarios/compare

Compare scenarios. Body: `scenario_ids`, `metrics`. Returns ranked comparison with recommended scenario and rationale.

#### DELETE /scenarios/{scenario_id}

Delete scenario. **Response 204.**

---

### Tag: reports

#### POST /reports/generate

Generate report. Body: `project_id`, `type` (executive_summary, technical, full), `format`, `include_sections`, `language`. **Response 202.**

#### GET /reports/{project_id}, GET /reports/detail/{report_id}, DELETE /reports/{report_id}

List, get metadata, delete. **Response 204** for delete.

---

### Tag: notifications

#### GET /notifications

List notifications. Query: `page`, `per_page`, `unread_only`, `type` (acquisition, training, inference, recommendation, scenario, system).

#### PATCH /notifications/{notification_id}/read

Mark read. **Response 204.**

#### POST /notifications/read-all

Mark all read. **Response 204.**

#### DELETE /notifications/{notification_id}

Delete. **Response 204.**

#### GET /notifications/subscribe

WebSocket: `wss://api.heatt.example.com/api/v1/notifications/subscribe?token=<access_token>`.
Server sends notification JSON with type/data. Heartbeat: `{"type": "ping"}` every 30s.

---

### Tag: admin

#### GET /admin/stats

System stats (admin): users, projects, scenes, models, recommendations, system metrics (requests_24h, avg_response_time, p99_response_time, error_rate).

#### GET /admin/logs

Query logs. Query: `level`, `service`, `from`, `to`, `search`, `page`, `per_page`.

#### GET /admin/health/services

All service health statuses: API, database (connections, replication lag), Redis (memory, hit rate), Celery (active/queued tasks, failures), object store.

#### POST /admin/cache/clear

Clear Redis cache. Returns cleared_keys, freed_memory_mb.

#### GET /admin/audit-log

Query audit log. Query: `user_id`, `action`, `resource_type`, `from`, `to`, `page`, `per_page`.

---

### Tag: health

#### GET /health

Comprehensive health: status, version, commit, build_time, uptime, per-service checks with response times. **503** if critical dependency unhealthy.

#### GET /health/ready

Readiness probe: `{"status": "ready", "checks": {"database": {"status": "ready"}, "redis": {"status": "ready"}}}`. **503** if not ready.

#### GET /health/live

Liveness probe: `{"status": "alive"}`. Always succeeds.

---

## Common Response Structures

### ApiError
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Scene with ID s1a2b3c4-... was not found",
    "details": {"resource_type": "scene", "resource_id": "s1a2b3c4-..."},
    "trace_id": "4a1f3c8e-b701-4f2a-9d5e-c2f3b8a1d6e7",
    "timestamp": "2026-07-02T12:00:00Z"
  }
}
```

### PaginatedResponse
```json
{
  "data": [],
  "pagination": {"page": 1, "per_page": 20, "total": 147, "total_pages": 8}
}
```
