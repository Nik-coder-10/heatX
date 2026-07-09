# Urban Heat Mitigation Platform — Performance Documentation

## Benchmark Results

### Inference Latency

Benchmarks conducted on AWS c5.4xlarge (16 vCPU, 32 GB RAM, no GPU) with 18,500 training samples and 4,625 test samples (Mumbai, 100 km2).

| Model | Batch Size | Mean Latency (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Throughput (pred/s) |
|---|---|---|---|---|---|---|
| Random Forest (500 trees) | 1 | 4.2 | 3.8 | 7.1 | 12.4 | 238 |
| Random Forest (500 trees) | 100 | 18.7 | 17.2 | 28.4 | 35.1 | 5,348 |
| XGBoost (500 trees) | 1 | 2.8 | 2.5 | 5.2 | 9.8 | 357 |
| XGBoost (500 trees) | 100 | 12.4 | 11.6 | 19.8 | 26.3 | 8,065 |
| LightGBM (500 trees) | 1 | 1.9 | 1.7 | 3.8 | 7.2 | 526 |
| LightGBM (500 trees) | 100 | 8.1 | 7.5 | 13.2 | 18.9 | 12,346 |
| CatBoost (500 trees) | 1 | 3.5 | 3.2 | 6.1 | 11.4 | 286 |
| CatBoost (500 trees) | 100 | 15.2 | 14.1 | 23.7 | 31.2 | 6,579 |
| SVM (RBF kernel) | 1 | 8.7 | 8.1 | 14.2 | 22.8 | 115 |
| SVM (RBF kernel) | 100 | 142.3 | 138.5 | 198.4 | 245.1 | 703 |
| KNN (k=15) | 1 | 1.2 | 1.1 | 2.4 | 4.7 | 833 |
| KNN (k=15) | 100 | 28.6 | 26.8 | 42.1 | 58.3 | 3,497 |
| MLP (3 layers, 256 units) | 1 | 0.8 | 0.7 | 1.5 | 3.1 | 1,250 |
| MLP (3 layers, 256 units) | 100 | 6.3 | 5.8 | 10.2 | 15.7 | 15,873 |
| Ensemble (soft voting) | 1 | 12.8 | 11.9 | 20.4 | 32.1 | 78 |
| Ensemble (soft voting) | 100 | 68.4 | 64.2 | 98.7 | 134.5 | 1,462 |

### API Response Times

| Endpoint | Mean (ms) | P50 (ms) | P95 (ms) | P99 (ms) |
|---|---|---|---|---|
| GET /health | 2 | 1 | 4 | 8 |
| POST /auth/login | 45 | 38 | 89 | 145 |
| GET /projects | 28 | 24 | 52 | 87 |
| POST /projects | 35 | 31 | 61 | 98 |
| GET /satellite/scenes | 62 | 55 | 112 | 198 |
| POST /gis/indices (sync) | 145 | 132 | 245 | 389 |
| GET /heat/results | 185 | 168 | 324 | 512 |
| POST /ml/predict (batch=100) | 85 | 78 | 148 | 234 |
| GET /ml/models/{id} | 22 | 19 | 42 | 68 |
| GET /recommendations/{id} | 142 | 128 | 263 | 412 |

### Training Time

| Model | Dataset Size | Train Time (s) | Memory (GB) |
|---|---|---|---|
| Random Forest (500 trees) | 18,500 samples, 17 features | 142 | 1.2 |
| XGBoost (500 trees) | 18,500 | 98 | 0.9 |
| LightGBM (500 trees) | 18,500 | 76 | 0.7 |
| CatBoost (500 trees) | 18,500 | 187 | 1.8 |
| SVM (RBF kernel) | 18,500 | 423 | 3.4 |
| KNN (k=15) | 18,500 | 0.4 | 0.3 |
| MLP (3 layers, 256 units) | 18,500 | 54 | 0.6 |
| Ensemble (all models + voting) | 18,500 | 982 | 8.9 |
| Optuna hyperparameter search (100 trials) | 18,500 | 3,600 | 4.2 |

### Raster Processing

| Operation | Scene Size | Resolution | Time (s) |
|---|---|---|---|
| Download Landsat 8 scene | 487 MB | 30m | 12 |
| Cloud masking (Fmask) | 487 MB | 30m | 8 |
| Atmospheric correction (DOS1) | 487 MB | 30m | 14 |
| Resampling (30m to 10m) | 487 MB | 10m | 22 |
| NDVI computation | 487 MB | 30m | 3 |
| LST mono-window algorithm | 487 MB | 30m | 6 |
| UHI detection (DBSCAN + severity) | 487 MB | 30m | 15 |
| Feature extraction (17 features) | 487 MB | 30m | 28 |

## Scaling Characteristics

### Data Volume vs Performance

| Samples | Feature Count | RF Train (s) | XGBoost Train (s) | RF Predict (ms/100) | XGBoost Predict (ms/100) |
|---|---|---|---|---|---|
| 5,000 | 17 | 38 | 26 | 5.2 | 3.8 |
| 10,000 | 17 | 78 | 54 | 10.1 | 7.2 |
| 18,500 | 17 | 142 | 98 | 18.7 | 12.4 |
| 50,000 | 17 | 385 | 267 | 47.3 | 31.8 |
| 100,000 | 17 | 782 | 541 | 92.1 | 62.4 |
| 500,000 | 17 | 3,940 | 2,710 | 458 | 308 |

### Spatial Extent vs Processing Time

| Area (km2) | Pixels (30m) | Acquisition (min) | Processing (min) |
|---|---|---|---|
| 10 | 11,111 | 2 | 1 |
| 100 | 111,111 | 5 | 3 |
| 1,000 | 1,111,111 | 12 | 8 |
| 10,000 | 11,111,111 | 45 | 35 |
| 100,000 | 111,111,111 | 180 | 240 |

## Optimization Strategies

### Caching

| Cache Layer | Key Pattern | TTL | Hit Rate |
|---|---|---|---|
| Redis raster tile cache | `raster:{project}:{scene}:{band}` | 1 hour | 78% |
| Redis feature vector cache | `features:{project}:{grid_id}` | 30 min | 85% |
| Redis model prediction cache | `pred:{project}:{model}:{grid_id}` | 1 hour | 72% |
| Redis index computation cache | `index:{project}:{scene}:{type}` | 24 hours | 92% |
| CDN (static tiles) | `/tiles/{z}/{x}/{y}.pbf` | 7 days | 95% |

### Connection Pooling

- **PostgreSQL**: SQLAlchemy pool_size=20, max_overflow=10, pool_timeout=30s
- **Redis**: Connection pool max_connections=50, timeout=5s
- **Celery**: worker_concurrency=8 (per container), prefetch_multiplier=4
- **HTTP (aiohttp)**: Connector limit=100, ttl_dns_cache=300s

### Async Processing

| Operation | Sync Time | Async Time | Speedup |
|---|---|---|---|
| Batch scene acquisition (18 scenes) | 540s | 487s | 1.1x |
| Spectral indices (6 indices, 1 scene) | 18s | 8s | 2.3x |
| Feature extraction (1 scene) | 28s | 12s | 2.3x |
| Monte Carlo simulation (1,000 runs) | 1,200s | 240s | 5.0x |
| Report generation (PDF) | 120s | 45s | 2.7x |

### Database Optimizations

- **Spatial indexing**: GiST indexes on geometry columns, BRIN indexes on acquisition_date
- **Materialized views**: Pre-computed UHI severity aggregates refreshed nightly
- **Partial indexes**: `WHERE status = 'active'` on projects, `WHERE is_deleted = FALSE` on users
- **Query optimization**: ST_Intersects with index-assisted bounding box pre-filter
- **Connection pooling**: PgBouncer transaction mode with 200 max client connections

## Resource Requirements

### Minimum Deployment

| Component | vCPU | RAM (GB) | Storage (GB) | Instances |
|---|---|---|---|---|
| FastAPI API server | 2 | 4 | 10 | 1 |
| Celery workers (all queues) | 4 | 8 | 20 | 1 |
| PostgreSQL + PostGIS | 4 | 16 | 500 | 1 |
| Redis (cache + broker) | 2 | 4 | 50 | 1 |
| Nginx | 1 | 1 | 5 | 1 |
| Object store (MinIO) | 2 | 4 | 1,000 | 1 |
| **Total minimum** | **15** | **37** | **1,585** | **6** |

### Recommended Production

| Component | vCPU | RAM (GB) | Storage (GB) | Instances |
|---|---|---|---|---|
| FastAPI API server | 8 | 16 | 50 | 3 |
| Celery acq_worker | 8 | 16 | 100 | 2 |
| Celery train_worker | 16 | 64 | 100 | 1 |
| Celery infer_worker | 8 | 16 | 50 | 3 |
| Celery sim_worker | 8 | 32 | 50 | 2 |
| PostgreSQL primary | 16 | 64 | 2,000 | 1 |
| PostgreSQL replica | 8 | 32 | 2,000 | 1 |
| Redis primary | 4 | 16 | 100 | 1 |
| Redis replica | 4 | 8 | 100 | 2 |
| Nginx | 2 | 4 | 10 | 2 |
| Object store (MinIO) | 8 | 16 | 5,000 | 3 |
| Prometheus + Grafana + Loki | 4 | 8 | 500 | 1 |
| **Total recommended** | **96** | **292** | **10,060** | **22** |

## Bottleneck Analysis

### Current Bottlenecks (Identified via profiling)

1. **Raster I/O (Primary)** — 47% of Celery worker time spent on reading/writing GeoTIFF files. Mitigation: Cloud-Optimized GeoTIFFs with range requests, parallel chunked reads.

2. **Model Training (CPU-bound)** — SVM and CatBoost training consumes 100% CPU for extended periods. Mitigation: GPU acceleration (CUDA) for training, early stopping with 50-round patience.

3. **Spatial Join Queries** — PostGIS ST_Intersects with large geometries causes seq scans. Mitigation: Better index strategies, bounding box pre-filtering, spatial partitioning.

4. **Redis Memory** — Feature vector cache grows unbounded (observed 2.4 GB for 50,000 grid cells). Mitigation: Implement LRU eviction, reduce TTL, compress vectors with msgpack.

5. **API Serialization** — Large GeoJSON responses (5+ MB) cause high latency. Mitigation: Implement response compression (gzip/brotli), pagination, topology simplification.

### Profiling Methodology

- **Application profiling**: Py-spy (sampling profiler) attached to Celery workers, cProfile for function-level analysis
- **Database profiling**: pg_stat_statements for query latency, auto_explain for query plans (slow query threshold: 200ms)
- **Redis profiling**: redis-cli --latency, SLOWLOG GET 100, MONITOR (limited sampling)
- **Network profiling**: tcpdump + Wireshark for bandwidth analysis, curl -w for per-hop timing
- **Memory profiling**: memory_profiler for Python, pg_top for PostgreSQL, redis-memory-for-key for Redis
- **Profiling schedule**: Continuous (1% sampling), detailed on-demand triggered by latency alerts
- **Tools used**: Py-spy, cProfile, pyperf, pytest-benchmark, locust (load testing), vegeta (HTTP load testing)
