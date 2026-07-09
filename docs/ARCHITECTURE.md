# Urban Heat Mitigation Platform — Architecture

## High-Level Architecture Overview

The Urban Heat Mitigation Platform is a modular, event-driven system that ingests multispectral satellite imagery, computes land surface temperature (LST) and urban heat island (UHI) indicators, trains ensemble machine learning models to predict thermal risk, and generates cost-optimized mitigation recommendations. The system is built on a microservices architecture orchestrated via Docker Compose, with FastAPI serving as the API gateway and Celery workers handling long-running compute tasks (acquisition, training, simulation). PostgreSQL with PostGIS extension provides geospatial storage and analytics, while Redis serves as both a Celery broker and a caching layer for frequently accessed raster tiles and model predictions. All services emit structured metrics and traces via OpenTelemetry, aggregated by Prometheus and Loki for observability through Grafana dashboards.

The platform is organized around six core domains: Satellite Acquisition (scheduling, downloading, preprocessing imagery), Geospatial Analysis (index computation, LST retrieval, UHI clustering), Machine Learning (feature engineering, model training, inference, drift detection), Recommendations (rule-based candidate generation, knapsack optimization, cost-effectiveness scoring), Scenario Simulation (template-based feature perturbation, Monte Carlo uncertainty propagation, comparison ranking), and Presentation (REST API, real-time WebSocket notifications, MapLibre GL frontend). Each domain is implemented as a self-contained Python package with well-defined service interfaces registered via a central module registry.

Data flows through the system in a directed acyclic pipeline: raw satellite scenes are acquired and preprocessed into analysis-ready rasters, from which spectral indices and LST are computed. These raster layers are vectorized into feature vectors aligned with administrative or grid-cell boundaries, forming the training and inference datasets. ML models ingest these feature vectors to produce UHI severity classifications and LST anomaly predictions. Downstream, the recommendation engine combines model predictions with cost databases and land-use constraints to generate ranked mitigation portfolios, while the scenario engine allows planners to simulate the impact of interventions (e.g., green roofs, reflective pavements) before committing resources.

The system is designed for horizontal scalability. Stateless API and worker containers can be scaled independently behind Nginx reverse proxy. Raster processing is parallelized across workers using Celery task routing with geo-partitioned queues. Model inference supports batching and GPU acceleration via CUDA when available. Caching strategies are layered: Redis caches tile requests and feature vectors; a CDN caches static MapLibre tiles; and application-level memoization avoids redundant computation of spectral indices for overlapping scenes. All persistent state — user accounts, project metadata, ML models, recommendations, and scenarios — is stored in PostgreSQL with PostGIS, with read replicas planned for production deployments.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          URBAN HEAT MITIGATION PLATFORM                              │
│                                                                                      │
│  ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌─────────────┐   ┌───────────────┐  │
│  │  React   │   │  Nginx    │   │  FastAPI  │   │  Celery     │   │  PostgreSQL   │  │
│  │  Frontend│──▶│  Reverse  │──▶│  Gateway  │──▶│  Workers    │──▶│  + PostGIS    │  │
│  │  (TS)    │   │  Proxy    │   │  (Python) │   │  (Python)   │   │  (Spatial DB) │  │
│  └──────────┘   └───────────┘   └─────┬─────┘   └──────┬──────┘   └───────────────┘  │
│        │                               │               │                             │
│        │                               │               │                             │
│  ┌─────┴──────┐               ┌────────┴────────┐     │                     ┌────────┴────────┐
│  │ MapLibre   │               │   Service Layer  │     │                     │     Redis       │
│  │ GL +       │               │  ┌──────────────┐│     │                     │  ┌────────────┐ │
│  │ ECharts    │               │  │ AuthService   ││     │                     │  │ Cache +    │ │
│  └────────────┘               │  │ UserService   ││     │                     │  │ Celery     │ │
│                               │  │ ProjectService ││     │                     │  │ Broker     │ │
│                               │  │ SatelliteSvc  ││     │                     │  └────────────┘ │
│  ┌────────────┐               │  │ GisService    ││     │                     └────────────────┘
│  │ WebSocket  │               │  │ HeatService   ││     │
│  │ (Notific.) │               │  │ MlService     ││     │                      ┌────────────────┐
│  └────────────┘               │  │ RecommendSvc  ││     │                      │  Object Store  │
│                               │  │ ScenarioSvc   ││     │                      │  (MinIO/S3)    │
│                               │  │ ReportService ││     │─── raster tiles ────▶│  ┌────────────┐ │
│                               │  │ Notification  ││     │                      │  │ GeoTIFF    │ │
│                               │  │ AdminService  ││     │                      │  │ ML Models  │ │
│                               │  └──────────────┘│     │                      │  │ Reports    │ │
│                               └──────────────────┘     │                      └────────────┘ │
│                                                         │                                   │
│  ┌──────────────────────────────────────────────────────┴──────────────┐                    │
│  │                     Celery Task Queues                              │                    │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │                    │
│  │  │ acq_worker    │ │ train_worker │ │ infer_worker │ │ sim_worker │ │                    │
│  │  │ (Acquisition) │ │ (ML Training)│ │ (Inference)  │ │(Scenario)  │ │                    │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │                    │
│  └─────────────────────────────────────────────────────────────────────┘                    │
│                                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                         Observability Stack                                            │  │
│  │  ┌───────────┐  ┌──────────┐  ┌───────┐  ┌───────────┐  ┌────────────┐               │  │
│  │  │Prometheus │  │ Grafana  │  │ Loki  │  │OTel Col.  │  │ Health    │               │  │
│  │  │(Metrics)  │  │(Dash.)   │  │(Logs) │  │(Traces)   │  │ Endpoints │               │  │
│  │  └───────────┘  └──────────┘  └───────┘  └───────────┘  └────────────┘               │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Module Dependency Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              MODULE DEPENDENCY TREE                                  │
│                                                                                      │
│  heatt/  (root package)                                                              │
│  ├── api/                      depends on: services, schemas, auth                    │
│  │   ├── v1/                                                                         │
│  │   │   ├── auth.py           depends: services.auth, schemas.auth                   │
│  │   │   ├── users.py          depends: services.user, schemas.user                   │
│  │   │   ├── roles.py          depends: services.role, schemas.role                   │
│  │   │   ├── projects.py       depends: services.project, schemas.project             │
│  │   │   ├── satellite.py      depends: services.satellite, schemas.satellite         │
│  │   │   ├── acquisition.py    depends: services.satellite.acquisition                │
│  │   │   ├── gis.py            depends: services.gis, schemas.gis                     │
│  │   │   ├── heat.py           depends: services.heat, schemas.heat                   │
│  │   │   ├── ml_training.py    depends: services.ml, schemas.ml                       │
│  │   │   ├── ml_inference.py   depends: services.ml.inference                         │
│  │   │   ├── recommendations.py depends: services.recommendation                      │
│  │   │   ├── scenarios.py      depends: services.scenario                             │
│  │   │   ├── reports.py        depends: services.report                               │
│  │   │   ├── notifications.py  depends: services.notification                         │
│  │   │   ├── admin.py          depends: services.admin                                │
│  │   │   └── health.py         depends: — (direct db/redis check)                     │
│  │   ├── deps.py               depends: db, redis, auth                               │
│  │   └── errors.py             depends: — (standalone exception handlers)             │
│  ├── core/                                                                             │
│  │   ├── config.py             depends: pydantic, env                                  │
│  │   ├── security.py           depends: core.config, jose, passlib                     │
│  │   ├── registry.py           depends: — (standalone registry pattern)                │
│  │   ├── database.py           depends: sqlalchemy, core.config                        │
│  │   ├── redis_client.py       depends: redis, core.config                            │
│  │   ├── celery_app.py         depends: core.config, redis_client                     │
│  │   ├── logging.py            depends: structlog, core.config                        │
│  │   ├── telemetry.py          depends: opentelemetry, core.config                    │
│  │   ├── rate_limit.py         depends: redis_client                                  │
│  │   └── exceptions.py         depends: — (standalone exception classes)              │
│  ├── domain/                                                                           │
│  │   ├── models/              depends: sqlalchemy, geoalchemy2                        │
│  │   │   ├── user.py                                                                  │
│  │   │   ├── role.py                                                                  │
│  │   │   ├── project.py                                                               │
│  │   │   ├── satellite_scene.py                                                        │
│  │   │   ├── raster_layer.py                                                          │
│  │   │   ├── feature_vector.py                                                        │
│  │   │   ├── ml_model.py                                                              │
│  │   │   ├── prediction.py                                                            │
│  │   │   ├── recommendation.py                                                        │
│  │   │   ├── scenario.py                                                              │
│  │   │   ├── notification.py                                                          │
│  │   │   └── audit_log.py                                                             │
│  │   ├── schemas/            depends: pydantic                                        │
│  │   │   ├── auth.py                                                                  │
│  │   │   ├── user.py                                                                  │
│  │   │   ├── satellite.py                                                             │
│  │   │   ├── heat.py                                                                  │
│  │   │   ├── ml.py                                                                    │
│  │   │   ├── recommendation.py                                                        │
│  │   │   ├── scenario.py                                                              │
│  │   │   └── common.py (pagination, error)                                            │
│  │   └── enums.py              depends: — (standalone enumerations)                   │
│  ├── services/               depends: domain.models, domain.schemas, core             │
│  │   ├── auth_service.py                                                              │
│  │   ├── user_service.py                                                              │
│  │   ├── role_service.py                                                              │
│  │   ├── project_service.py                                                           │
│  │   ├── satellite_service.py                                                         │
│  │   ├── acquisition_service.py                                                       │
│  │   ├── gis_service.py                                                               │
│  │   ├── heat_service.py                                                              │
│  │   ├── ml_service.py                                                                │
│  │   ├── recommendation_service.py                                                    │
│  │   ├── scenario_service.py                                                          │
│  │   ├── report_service.py                                                            │
│  │   ├── notification_service.py                                                      │
│  │   └── admin_service.py                                                             │
│  ├── acquisition/           depends: rasterio, shapely, numpy                         │
│  │   ├── landsat.py         depends: core.config, domain.models                       │
│  │   ├── sentinel.py                                                                  │
│  │   ├── bhuvan.py                                                                    │
│  │   ├── cloud_masking.py                                                             │
│  │   ├── atmospheric_correction.py                                                    │
│  │   ├── resampler.py                                                                 │
│  │   └── mosaicker.py                                                                 │
│  ├── gis/                   depends: rasterio, shapely, geopandas, numpy              │
│  │   ├── indices.py                                                                   │
│  │   ├── lst_mono_window.py                                                           │
│  │   ├── lst_split_window.py                                                          │
│  │   ├── emissivity.py                                                                │
│  │   ├── atmospheric_correction_rte.py                                                │
│  │   ├── uhi_detection.py                                                             │
│  │   └── feature_extraction.py                                                        │
│  ├── ml/                    depends: sklearn, xgboost, lightgbm, catboost, shap      │
│  │   ├── models/                                                                      │
│  │   │   ├── random_forest.py                                                         │
│  │   │   ├── xgboost_model.py                                                         │
│  │   │   ├── lightgbm_model.py                                                        │
│  │   │   ├── catboost_model.py                                                        │
│  │   │   ├── svm_model.py                                                             │
│  │   │   ├── knn_model.py                                                             │
│  │   │   ├── mlp_model.py                                                             │
│  │   │   └── ensemble.py                                                              │
│  │   ├── feature_engineering.py                                                       │
│  │   ├── cross_validation.py                                                          │
│  │   ├── hyperparameter_search.py                                                     │
│  │   ├── drift_detection.py                                                           │
│  │   ├── explainability.py                                                            │
│  │   ├── trainer.py                                                                   │
│  │   └── inference.py                                                                 │
│  ├── recommendation/       depends: ml, gis                                           │
│  │   ├── candidate_generator.py                                                       │
│  │   ├── cost_effectiveness.py                                                        │
│  │   └── knapsack_optimizer.py                                                        │
│  ├── scenario/             depends: ml, gis                                           │
│  │   ├── template_engine.py                                                           │
│  │   ├── monte_carlo.py                                                               │
│  │   └── comparator.py                                                                │
│  ├── workers/              depends: celery_app, services                              │
│  │   ├── acq_worker.py                                                                │
│  │   ├── train_worker.py                                                              │
│  │   ├── infer_worker.py                                                              │
│  │   └── sim_worker.py                                                                │
│  └── main.py               depends: fastapi, all routers                              │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Sequence Diagrams

### Satellite Acquisition Pipeline

```
User            API            AcquisitionService    LandsatAPI         Celery             S3/ObjectStore    PostgreSQL
 │              │                    │                   │                │                     │               │
 │ POST /acquisition/schedule        │                   │                │                     │               │
 │──────────────▶                    │                   │                │                     │               │
 │              │  validate AOI + dates                 │                │                     │               │
 │              │─────────────────────▶                  │                │                     │               │
 │              │                    │                   │                │                     │               │
 │              │  schedule_acquisition(scene_id)        │                │                     │               │
 │              │─────────────────────▶                  │                │                     │               │
 │              │                    │  search_scenes(aoi, dates)         │                     │               │
 │              │                    │──────────────────▶                 │                     │               │
 │              │                    │                   │  SceneList     │                     │               │
 │              │                    │◀───────────────────                 │                     │               │
 │              │                    │                   │                │                     │               │
 │              │                    │  dispatch(acq_worker, scene)       │                     │               │
 │              │                    │────────────────────────────────────▶                     │               │
 │ 202 Accepted │                    │                   │                │                     │               │
 │◀─────────────│                    │                   │                │                     │               │
 │              │                    │                   │                │                     │               │
 │              │                    │                   │                │  download_bundle()   │               │
 │              │                    │                   │                │────────────────────▶│               │
 │              │                    │                   │                │◀────────────────────│               │
 │              │                    │                   │                │                     │               │
 │              │                    │                   │                │  cloud_mask(Fmask)   │               │
 │              │                    │                   │                │  atmos_corr(DOS1)    │               │
 │              │                    │                   │                │  resample(30m)       │               │
 │              │                    │                   │                │  save_raster()       │               │
 │              │                    │                   │                │────────────────────▶│               │
 │              │                    │                   │                │                     │               │
 │              │                    │                   │                │  update_status(      │               │
 │              │                    │                   │                │   completed, meta)   │               │
 │              │                    │                   │                │                     │──────────────▶│
 │              │                    │                   │                │                     │               │
 │              │                    │   notify_complete(scene_id)        │                     │               │
 │              │                    │◀───────────────────────────────────│                     │               │
 │              │   WebSocket: acquisition.complete                       │                     │               │
 │              │◀────────────────────────────────────────────────────────│                     │               │
```

### UHI Detection Pipeline

```
API              HeatService          GisService        PostGIS             Redis
 │                   │                    │                │                 │
 │ POST /heat/detect                     │                │                 │
 │──────────────────▶                    │                │                 │
 │                   │  get_raster(project_id, scene_id)  │                 │
 │                   │───────────────────▶                │                 │
 │                   │                    │  raster_query  │                 │
 │                   │                    │───────────────▶│                 │
 │                   │                    │◀───────────────│                 │
 │                   │◀───────────────────│                │                 │
 │                   │                    │                │                 │
 │                   │  compute_ndvi()    │                │                 │
 │                   │  compute_ndwi()    │                │                 │
 │                   │  compute_ndbi()    │                │                 │
 │                   │  compute_ui()      │                │                 │
 │                   │  compute_bsi()     │                │                 │
 │                   │  compute_lst(mono_window)           │                 │
 │                   │  compute_lst(split_window)          │                 │
 │                   │───────────────────▶                │                 │
 │                   │                    │                │                 │
 │                   │                    │  detect_hotspots(dbscan, eps=0.01, min_samples=5)  │
 │                   │                    │─────(in-memory)─────────────────│                 │
 │                   │                    │  severity_classify()            │                 │
 │                   │                    │     threshold = mean + n*std    │                 │
 │                   │                    │  urban_rural_gradient()         │                 │
 │                   │                    │─────(in-memory)─────────────────│                 │
 │                   │                    │                │                 │
 │                   │  cache rasters + features          │                 │
 │                   │─────────────────────────────────────────────────────▶│
 │                   │                    │                │                 │
 │                   │  persist vectors + stats           │                 │
 │                   │──────────────────────────────────────────────────────▶
 │                   │                    │                │                 │
 │ 200 {uhi_result}  │                    │                │                 │
 │◀──────────────────│                    │                │                 │
```

### ML Training + Prediction Pipeline

```
API              MlService            Trainer            Celery              MLflow/S3         PostGIS
 │                   │                    │                │                    │                │
 │ POST /ml/train    │                    │                │                    │                │
 │──────────────────▶│                    │                │                    │                │
 │                   │  validate_config() │                │                    │                │
 │                   │───────────────────▶│                │                    │                │
 │                   │                    │                │                    │                │
 │                   │  dispatch(train_worker)             │                    │                │
 │                   │────────────────────────────────────▶│                    │                │
 │ 202 Accepted      │                    │                │                    │                │
 │◀──────────────────│                    │                │                    │                │
 │                   │                    │                │                    │                │
 │                   │                    │                │  load_features(    │                │
 │                   │                    │                │   project_id)      │                │
 │                   │                    │                │────────────────────────────────────▶
 │                   │                    │                │◀────────────────────────────────────
 │                   │                    │                │                    │                │
 │                   │                    │                │  split_data(       │                │
 │                   │                    │                │   temporal_split)  │                │
 │                   │                    │                │  engineer_features │                │
 │                   │                    │                │  (17 features)     │                │
 │                   │                    │                │                    │                │
 │                   │                    │                │  cross_validate(   │                │
 │                   │                    │                │   spatial_kfold=5) │                │
 │                   │                    │                │  hyperopt(optuna,  │                │
 │                   │                    │                │   n_trials=100)    │                │
 │                   │                    │                │  train_best_model()│                │
 │                   │                    │                │  compute_shap()    │                │
 │                   │                    │                │                    │                │
 │                   │                    │                │  save_model()      │                │
 │                   │                    │                │──────────────────▶│                │
 │                   │                    │                │                    │                │
 │                   │                    │                │  save_metadata(    │                │
 │                   │                    │                │   metrics, params) │                │
 │                   │                    │                │────────────────────────────────────▶
 │                   │                    │                │                    │                │
 │                   │  notify_train_complete(model_id)   │                    │                │
 │                   │◀───────────────────────────────────│                    │                │
 │  WebSocket: ml.training.complete      │                │                    │                │
 │◀──────────────────│                    │                │                    │                │
 │                   │                    │                │                    │                │
 │ POST /ml/predict  │                    │                │                    │                │
 │──────────────────▶│                    │                │                    │                │
 │                   │  load_model(model_id)              │                    │                │
 │                   │───────────────────────────────────────────────────────────────────────▶│
 │                   │◀───────────────────────────────────────────────────────────────────────│
 │                   │                    │                │                    │                │
 │                   │  load_features(project_id)         │                    │                │
 │                   │───────────────────────────────────────────────────────────────────────▶│
 │                   │◀───────────────────────────────────────────────────────────────────────│
 │                   │                    │                │                    │                │
 │                   │  predict(X)        │                │                    │                │
 │                   │  explain(shap.TreeExplainer)        │                    │                │
 │                   │                    │                │                    │                │
 │ 200 {predictions, shap_values}         │                │                    │                │
 │◀──────────────────│                    │                │                    │                │
```

### Recommendation Generation

```
API               RecommendationService      CandidateGenerator     CostEffectiveness     KnapsackOptimizer    PostGIS
 │                        │                        │                      │                      │                │
 │ POST /recommendations  │                        │                      │                      │                │
 │────────────────────────▶                        │                      │                      │                │
 │                        │                        │                      │                      │                │
 │                        │  get_predictions(       │                      │                      │                │
 │                        │   project_id)           │                      │                      │                │
 │                        │───────────────────────────────────────────────────────────────────────▶│
 │                        │◀───────────────────────────────────────────────────────────────────────│
 │                        │                        │                      │                      │                │
 │                        │  generate_candidates(   │                      │                      │                │
 │                        │   lst, severity, lulc)  │                      │                      │                │
 │                        │────────────────────────▶│                      │                      │                │
 │                        │                        │  rule_based_filter(   │                      │                │
 │                        │                        │   lulc_class →        │                      │                │
 │                        │                        │   intervention_type)  │                      │                │
 │                        │                        │  spatial_intersection( │                      │                │
 │                        │                        │   parcel_boundary)    │                      │                │
 │                        │                        │                      │                      │                │
 │                        │◀────────────────────────│                      │                      │                │
 │                        │                        │                      │                      │                │
 │                        │  score_candidates(       │                      │                      │                │
 │                        │   candidates)            │                      │                      │                │
 │                        │────────────────────────────────────────────────▶│                      │                │
 │                        │                        │                      │                      │                │
 │                        │                        │  cost = material +    │                      │                │
 │                        │                        │   installation +      │                      │                │
 │                        │                        │   maintenance         │                      │                │
 │                        │                        │  benefit = lst_reduc  │                      │                │
 │                        │                        │   * area * pop_density│                      │                │
 │                        │                        │  cost_effectiveness = │                      │                │
 │                        │                        │   benefit / cost      │                      │                │
 │                        │                        │                      │                      │                │
 │                        │◀────────────────────────────────────────────────│                      │                │
 │                        │                        │                      │                      │                │
 │                        │  optimize(budget,        │                      │                      │                │
 │                        │   candidates)            │                      │                      │                │
 │                        │────────────────────────────────────────────────────────────────────▶│
 │                        │                        │                      │                      │                │
 │                        │                        │                      │  01_knapsack(         │                │
 │                        │                        │                      │   dp, weights=        │                │
 │                        │                        │                      │   cost, values=       │                │
 │                        │                        │                      │   cost_effectiveness) │                │
 │                        │                        │                      │                      │                │
 │                        │◀────────────────────────────────────────────────────────────────────│
 │                        │                        │                      │                      │                │
 │                        │  persist(recommendations)│                      │                      │                │
 │                        │───────────────────────────────────────────────────────────────────────▶
 │                        │                        │                      │                      │                │
 │ 200 {recommendations,   │                        │                      │                      │                │
 │       total_cost,       │                        │                      │                      │                │
 │       projected_reduction}                        │                      │                      │                │
 │◀────────────────────────│                        │                      │                      │                │
```

### Scenario Simulation

```
API               ScenarioService        TemplateEngine      MonteCarloSim        Comparator       PostGIS
 │                        │                    │                   │                   │               │
 │ POST /scenarios        │                    │                   │                   │               │
 │────────────────────────▶                    │                   │                   │               │
 │                        │                    │                   │                   │               │
 │                        │  load_features(    │                   │                   │               │
 │                        │   project_id)      │                   │                   │               │
 │                        │────────────────────────────────────────────────────────────────────────▶│
 │                        │◀────────────────────────────────────────────────────────────────────────│
 │                        │                    │                   │                   │               │
 │                        │  apply_template(   │                   │                   │               │
 │                        │   scenario_def)    │                   │                   │               │
 │                        │───────────────────▶│                   │                   │               │
 │                        │                    │  modify_feature(   │                   │               │
 │                        │                    │   "green_roof",    │                   │               │
 │                        │                    │   albedo→0.7,      │                   │               │
 │                        │                    │   ndvi→0.6)        │                   │               │
 │                        │                    │  modify_feature(   │                   │               │
 │                        │                    │   "tree_canopy",   │                   │               │
 │                        │                    │   shade→0.4)       │                   │               │
 │                        │◀───────────────────│                   │                   │               │
 │                        │                    │                   │                   │               │
 │                        │  run_monte_carlo(   │                   │                   │               │
 │                        │   modified_features, n=1000)           │                   │               │
 │                        │───────────────────────────────────────▶│                   │               │
 │                        │                    │                   │  for i in 1..1000: │               │
 │                        │                    │                   │    sample_noise(   │               │
 │                        │                    │                   │     ~N(0, σ))      │               │
 │                        │                    │                   │    predict(model,  │               │
 │                        │                    │                   │     X_modified)    │               │
 │                        │                    │                   │  compute_ci(95%)   │               │
 │                        │◀───────────────────────────────────────│                   │               │
 │                        │                    │                   │                   │               │
 │                        │  rank_scenarios(    │                   │                   │               │
 │                        │   scenarios)        │                   │                   │               │
 │                        │───────────────────────────────────────────────────────────▶│               │
 │                        │                    │                   │                   │  sort(         │
 │                        │                    │                   │                   │   lst_reduction │
 │                        │                    │                   │                   │   DESC)        │
 │                        │                    │                   │                   │  compute_rank_  │
 │                        │                    │                   │                   │   score()      │
 │                        │◀───────────────────────────────────────────────────────────│               │
 │                        │                    │                   │                   │               │
 │                        │  persist(scenarios)│                   │                   │               │
 │                        │────────────────────────────────────────────────────────────────────────▶│
 │                        │                    │                   │                   │               │
 │ 200 {scenarios,        │                    │                   │                   │               │
 │       comparison,      │                    │                   │                   │               │
 │       uncertainties}   │                    │                   │                   │               │
 │◀────────────────────────│                    │                   │                   │               │
```

## Data Flow Diagram

```
                                                        ┌──────────────────────────────────────────────────┐
                                                        │              DATA FLOW DIAGRAM                     │
                                                        │                                                  │
 ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────────────┐    │
 │  Satellite   │    │  Raw Scenes  │    │ Preprocessed  │    │  Spectral    │    │  Feature Vectors   │    │
 │  Data Sources│───▶│  (GeoTIFF)   │───▶│  Rasters      │───▶│  Indices +   │───▶│  (tabular, per     │    │
 │              │    │              │    │  (cloud-free, │    │  LST Layers  │    │   grid cell/       │    │
 │ Landsat 8/9  │    │  B1-B11      │    │   atmos-corr, │    │              │    │   admin boundary)  │    │
 │ Sentinel-2   │    │  MTL/Metadata│    │   resampled)  │    │ NDVI, NDWI,  │    │                    │    │
 │ ISRO Bhuvan  │    │              │    │              │    │ NDBI, NBRI,  │    │  17 features +    │    │
 │              │    │              │    │              │    │ UI, BSI, LST │    │  target (UHI/LST) │    │
 └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └────────┬───────────┘    │
        │                   │                   │                   │                      │               │
        │  AWS/ESRI         │  S3/MinIO         │  S3/MinIO         │  Redis              │               │
        │  STAC API         │  (object store)   │  (object store)   │  (cache)            │               │
        │                   │                   │                   │                      │               │
        ▼                   ▼                   ▼                   ▼                      ▼               │
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
 │                                    MACHINE LEARNING PIPELINE                                         │  │
 │                                                                                                      │  │
 │  ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌───────────────┐  │  │
 │  │ Feature  │───▶│ Cross-    │───▶│ Hyper-   │───▶│ Train     │───▶│ Evaluate │───▶│ Deploy Model  │  │  │
 │  │ Engineer │    │ validate  │    │ parameter│    │ Best      │    │ (Test    │    │ (S3 + MLflow  │  │  │
 │  │ 17 feats │    │ (spatial  │    │ Search    │    │ Model     │    │ Set,     │    │ + Registry)   │  │  │
 │  │ Standard │    │  k-fold)  │    │ (Optuna)  │    │           │    │ SHAP,    │    │               │  │  │
 │  │ Scaler   │    │           │    │           │    │           │    │ Metrics) │    │               │  │  │
 │  └──────────┘    └───────────┘    └──────────┘    └───────────┘    └──────────┘    └───────┬───────┘  │  │
 │                                                                                            │          │  │
 │                                                                                            ▼          │  │
 │                                                                                     ┌──────────────┐ │  │
 │                                                                                     │   Inference  │ │  │
 │                                                                                     │  (Batch +    │ │  │
 │                                                                                     │   Real-time) │ │  │
 │                                                                                     └──────┬───────┘ │  │
 │                                                                                            │          │  │
 └────────────────────────────────────────────────────────────────────────────────────────────┼──────────┘  │
                                                                                              │             │
                                                                                              ▼             │
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
 │                                          DOWNSTREAM APPLICATIONS                                     │  │
 │                                                                                                      │  │
 │  ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────────────────────┐    │  │
 │  │  UHI Severity Map    │    │  Recommendations     │    │  Scenario Simulations                │    │  │
 │  │                      │    │                      │    │                                      │    │  │
 │  │  • LST thresholds    │    │  • Rule-based        │    │  • Template engine (green roofs,      │    │  │
 │  │  • Hotspot clusters  │    │    candidates        │    │    tree canopy, reflective pavements) │    │  │
 │  │  • Urban-rural       │    │  • Cost-effectiveness│    │  • Monte Carlo uncertainty            │    │  │
 │  │    gradient          │    │    scoring           │    │  • Multi-scenario comparison           │    │  │
 │  │  • Severity classes  │    │  • Knapsack          │    │  • Confidence intervals               │    │  │
 │  │                      │    │    optimization      │    │                                      │    │  │
 │  └──────────────────────┘    └──────────────────────┘    └──────────────────────────────────────┘    │  │
 │                                                                                                      │  │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
                                                                                                          │
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
 │                                       MONITORING & DRIFT DETECTION                                   │  │
 │                                                                                                      │  │
 │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐ │  │
 │  │  Data Drift      │    │  Concept Drift   │    │  Model Drift     │    │  Model Retraining      │ │  │
 │  │                  │    │                  │    │                  │    │  (automated trigger)   │ │  │
 │  │  • PSI (pop.     │    │  • Accuracy      │    │  • Feature       │    │                        │ │  │
 │  │    stability idx)│    │    degradation   │    │    importance    │    │  • Scheduled nightly  │ │  │
 │  │  • KS test       │    │  • Confusion     │    │    shift         │    │  • On drift detected  │ │  │
 │  │  • Distribution  │    │    matrix delta  │    │  • SHAP distance │    │  • Manual trigger     │ │  │
 │  │    comparison    │    │                  │    │  • Prediction    │    │                        │ │  │
 │  │                  │    │                  │    │    distribution  │    │                        │ │  │
 │  └──────────────────┘    └──────────────────┘    └──────────────────┘    └─────────────────────────┘ │  │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
                                                                                                          │
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
 │                                         USER INTERFACE                                               │  │
 │                                                                                                      │  │
 │  ┌────────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐│  │
 │  │  MapLibre GL       │  │  ECharts         │  │  Scenario        │  │  Reports                     ││  │
 │  │  (raster tiles,    │  │  (time series,   │  │  Builder UI      │  │  (PDF export, tables,        ││  │
 │  │   vector layers)   │  │   distributions, │  │  (drag-drop      │  │   charts, executive summary) ││  │
 │  │                    │  │   SHAP beeswarm) │  │   interventions) │  │                              ││  │
 │  └────────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────────────────┘│  │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
                                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## ML Pipeline Diagram

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           ML PIPELINE — END TO END                                                 │
│                                                                                                                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│  │  DATA    │   │ FEATURE  │   │ TRAINING │   │EVALUATION│   │DEPLOYMENT│   │INFERENCE │   │MONITORING│          │
│  │ INGEST  │   │ ENGINEER │   │          │   │          │   │          │   │          │   │          │          │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘          │
│       │              │              │              │              │              │              │                  │
│  ┌────┴────┐   ┌─────┴─────┐  ┌────┴────┐   ┌────┴────┐   ┌────┴────┐   ┌────┴────┐   ┌────┴────┐             │
│  │PostGIS  │   │ 17 Feat. │  │ Split   │   │ Test Set│   │Register │   │ Batch   │   │Data Drift│             │
│  │ + Raster│   │ Calc     │  │ Train/  │   │ Metrics │   │ Model   │   │ Predict │   │(PSI, KS) │             │
│  │ Tiles   │   │ NDVI, LST│  │ Val/Test│   │ R², MAE │   │ in S3 + │   │ (Celery)│   │          │             │
│  └─────────┘   │ Standard │  └────┬────┘   │ SHAP    │   │ MLflow  │   └────┬────┘   │Concept   │             │
│                │ Scaler   │       │         └─────────┘   └─────────┘       │       │Drift     │             │
│                │ Encoding │  ┌────┴────┐                                                    │(Accuracy │             │
│                └──────────┘  │ Cross   │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │Degradation)│             │
│                              │ Valid.  │  │ Hyperparam   │  │ Model Training│  │Explain   │ └────┬────┘             │
│                              │ Spatial │──│ Search       │──│ (best params) │──│ SHAP     │      │                  │
│                              │ k-fold  │  │ Optuna 100   │  │ Ensemble Vote │  │ Kernel   │      │                  │
│                              │ (n=5)   │  │ trials       │  │ (soft/hard)   │  │ Plots    │      │                  │
│                              └─────────┘  └──────────────┘  └──────────────┘  └──────────┘      │                  │
│                                                                                   │              │                  │
│                                                                                   ▼              ▼                  │
│                                                                          ┌─────────────────────────────┐            │
│                                                                          │      RETRAIN TRIGGER          │            │
│                                                                          │  (drift detected OR schedule) │            │
│                                                                          └─────────────────────────────┘            │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Deployment Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                            DEPLOYMENT ARCHITECTURE (Docker)                                          │
│                                                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐            │
│  │                                      DOCKER HOST / ORCHESTRATOR                                      │            │
│  │                                                                                                      │            │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐             │            │
│  │  │  nginx      │──▶│  api:8000   │──▶│  services   │──▶│  db:5432   │──▶│  redis:6379 │             │            │
│  │  │  :80 → :443 │   │  (FastAPI)  │   │  (in-process)│  │  (PostGIS) │   │  (Cache +   │             │            │
│  │  │  reverse    │   │  gunicorn   │   │  (6 replicas)│  │  (1 master+ │   │   Broker)   │             │            │
│  │  │  proxy +    │   │  uvicorn    │   │              │  │  1 replica) │   │  (1 master+ │             │            │
│  │  │  TLS term   │   │  workers=8  │   │              │  │             │   │  2 replicas)│             │            │
│  │  └─────────────┘   └─────────────┘   └─────────────┘  └─────────────┘   └─────────────┘             │            │
│  │        │                │                  │                 │                  │                    │            │
│  │        │                ▼                  ▼                 │                  │                    │            │
│  │        │        ┌────────────────────────────────────┐      │                  │                    │            │
│  │        │        │         Celery Workers             │      │                  │                    │            │
│  │        │        │  ┌─────────┐ ┌─────────┐          │      │                  │                    │            │
│  │        │        │  │ acq_wk  │ │ train_wk│          │      │                  │                    │            │
│  │        │        │  │(2 reps) │ │ (1 rep) │          │      │                  │                    │            │
│  │        │        │  ├─────────┤ ├─────────┤          │      │                  │                    │            │
│  │        │        │  │infer_wk │ │ sim_wk  │          │      │                  │                    │            │
│  │        │        │  │(3 reps) │ │ (2 reps)│          │      │                  │                    │            │
│  │        │        │  └─────────┘ └─────────┘          │      │                  │                    │            │
│  │        │        └────────────────────────────────────┘      │                  │                    │            │
│  │        │                                                    │                  │                    │            │
│  │        ▼                                                    ▼                  ▼                    │            │
│  │  ┌─────────────┐   ┌───────────────────────────────────────────────────────────────────────────────┐│            │
│  │  │  frontend   │   │                                Object Storage                                  ││            │
│  │  │  :5173      │   │  ┌─────────────────────────────────────────────────────────────────────────┐  ││            │
│  │  │  (Vite +    │   │  │  /rasters/{project_id}/{scene_id}/{band}.tif                             │  ││            │
│  │  │   React)    │   │  │  /indices/{project_id}/{scene_id}/{ndvi,ndwi,ndbi,ui,bsi,lst}.tif       │  ││            │
│  │  │  served via │   │  │  /models/{model_id}/model.pkl                                           │  ││            │
│  │  │  nginx      │   │  │  /models/{model_id}/preprocessor.pkl                                    │  ││            │
│  │  └─────────────┘   │  │  /models/{model_id}/metadata.json                                       │  ││            │
│  │                     │  │  /reports/{report_id}.pdf                                               │  ││            │
│  │                     │  │  /exports/{export_id}/{data}.geojson                                    │  ││            │
│  │                     │  └─────────────────────────────────────────────────────────────────────────┘  ││            │
│  │                     └───────────────────────────────────────────────────────────────────────────────┘│            │
│  │                                                                                                      │            │
│  │  ┌────────────────────────────────────────────────────────────────────────────────────┐               │            │
│  │  │                          Observability Stack                                       │               │            │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐    │               │            │
│  │  │  │Prometheus  │  │  Grafana   │  │   Loki     │  │OTel Col.   │  │  Alert-    │    │               │            │
│  │  │  │ :9090      │  │  :3000     │  │  :3100     │  │ :4318      │  │  manager   │    │               │            │
│  │  │  │(pull: api, │  │(dashboards,│  │(log agg.  │  │(traces     │  │  :9093     │    │               │            │
│  │  │  │ workers,   │  │ alerts)    │  │ from api + │  │ to Jaeger) │  │(slack,     │    │               │            │
│  │  │  │ postgres,  │  │            │  │ workers)   │  │            │  │  pagerduty)│    │               │            │
│  │  │  │ nginx)     │  │            │  │            │  │            │  │            │    │               │            │
│  │  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘  └────────────┘    │               │            │
│  │  └────────────────────────────────────────────────────────────────────────────────────┘               │            │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────────┘            │
│                                                                                                                     │
│  LEGEND:                                                                                                            │
│    ───▶  HTTP / gRPC traffic                                                                                        │
│    ───▶  Redis protocol / Celery messaging                                                                          │
│    ───▶  PostgreSQL wire protocol                                                                                   │
│    ~ ~ ▶  MinIO / S3 HTTP API                                                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Authentication Flow (JWT)

```
┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
│  Client  │          │  Nginx   │          │  FastAPI │          │  AuthSvc │          │  DB      │
└────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘          └────┬─────┘
     │                     │                     │                     │                     │
     │  POST /api/v1/auth/login                  │                     │                     │
     │  {email, password}  │                     │                     │                     │
     │────────────────────▶│────────────────────▶│────────────────────▶│                     │
     │                     │                     │                     │                     │
     │                     │                     │                     │  verify_password()   │
     │                     │                     │                     │  SELECT * FROM users │
     │                     │                     │                     │────────────────────▶│
     │                     │                     │                     │◀────────────────────│
     │                     │                     │                     │                     │
     │                     │                     │                     │  generate_access_token(sub, roles, exp=15m)
     │                     │                     │                     │  generate_refresh_token(sub, exp=7d)
     │                     │                     │                     │                     │
     │                     │                     │                     │  store refresh_hash  │
     │                     │                     │                     │────────────────────▶│
     │                     │                     │                     │◀────────────────────│
     │                     │                     │◀────────────────────│                     │
     │                     │◀────────────────────│                     │                     │
     │◀────────────────────│                     │                     │                     │
     │                     │                     │                     │                     │
     │  200 {access_token, refresh_token, expires_in}                 │                     │
     │                     │                     │                     │                     │
     │                     │                     │                     │                     │
     │  GET /api/v1/projects                    │                     │                     │
     │  Authorization: Bearer <access_token>    │                     │                     │
     │────────────────────▶│────────────────────▶│                     │                     │
     │                     │                     │                     │                     │
     │                     │                     │  decode_token()      │                     │
     │                     │                     │  verify_signature()  │                     │
     │                     │                     │  check_exp()         │                     │
     │                     │                     │  extract_sub+roles   │                     │
     │                     │                     │                     │                     │
     │                     │                     │  authorize(required_roles)                 │
     │                     │                     │────────────────────▶│                     │
     │                     │                     │◀────────────────────│                     │
     │                     │                     │                     │                     │
     │                     │                     │  forward to ProjectService                │
     │                     │                     │────────────────────▶│                     │
     │                     │                     │◀────────────────────│                     │
     │                     │◀────────────────────│                     │                     │
     │◀────────────────────│                     │                     │                     │
     │  200 {projects}     │                     │                     │                     │
     │                     │                     │                     │                     │
     │                     │                     │                     │                     │
     │  POST /api/v1/auth/refresh                                    │                     │
     │  {refresh_token}    │                     │                     │                     │
     │────────────────────▶│────────────────────▶│────────────────────▶│                     │
     │                     │                     │                     │  verify_refresh_hash│
     │                     │                     │                     │────────────────────▶│
     │                     │                     │                     │◀────────────────────│
     │                     │                     │◀────────────────────│                     │
     │                     │◀────────────────────│                     │                     │
     │◀────────────────────│                     │                     │                     │
     │  200 {new_access_token, new_refresh_token}                     │                     │
     │                     │                     │                     │                     │
```

## API Flow: Request → Nginx → Backend → Service → Repository → Database

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Client  │    │  Nginx   │    │  FastAPI │    │  Service │    │Repository│    │    DB    │
└────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │               │               │               │               │
     │  Request      │               │               │               │               │
     │──────────────▶│               │               │               │               │
     │               │               │               │               │               │
     │               │  TLS terminate│               │               │               │
     │               │  Rate limit   │               │               │               │
     │               │  Check JWT    │               │               │               │
     │               │  Rewrite path │               │               │               │
     │               │  Add headers  │               │               │               │
     │               │──────────────▶│               │               │               │
     │               │               │               │               │               │
     │               │               │  Validate req │               │               │
     │               │               │  Parse body   │               │               │
     │               │               │  Check perms  │               │               │
     │               │               │  Log + trace  │               │               │
     │               │               │──────────────▶│               │               │
     │               │               │               │               │               │
     │               │               │               │  Business     │               │
     │               │               │               │  logic +      │               │
     │               │               │               │  validation   │               │
     │               │               │               │──────────────▶│               │
     │               │               │               │               │               │
     │               │               │               │               │  Build query   │
     │               │               │               │               │  Execute SQL   │
     │               │               │               │               │──────────────▶│
     │               │               │               │               │               │
     │               │               │               │               │  Return rows   │
     │               │               │               │               │◀──────────────│
     │               │               │               │               │               │
     │               │               │               │  Map to domain │               │
     │               │               │               │  Apply cache   │               │
     │               │               │               │◀──────────────│               │
     │               │               │               │               │               │
     │               │               │  Map to schema │               │               │
     │               │               │  Apply hooks   │               │               │
     │               │               │◀──────────────│               │               │
     │               │               │               │               │               │
     │               │  Compress     │               │               │               │
     │               │  Add headers  │               │               │               │
     │               │◀──────────────│               │               │               │
     │               │               │               │               │               │
     │  Response     │               │               │               │               │
     │◀──────────────│               │               │               │               │
     │               │               │               │               │               │
```

## Design Decisions with Rationale

### 1. FastAPI over Django REST Framework
**Decision**: Use FastAPI for the API gateway.
**Rationale**: FastAPI provides native async support, automatic OpenAPI/Swagger generation, Pydantic-based request validation, and superior performance for I/O-bound geospatial workloads. Django's ORM, while mature, adds unnecessary overhead for a geospatial platform where most complex queries are executed via PostGIS raw SQL or GeoAlchemy2. FastAPI's dependency injection system aligns with the platform's clean architecture principles.

### 2. Celery for Async Task Processing
**Decision**: Delegate all long-running operations (acquisition, training, simulation) to Celery workers.
**Rationale**: Satellite download and preprocessing, ML training, and Monte Carlo simulations are CPU/IO-bound operations that would block the API server. Celery provides reliable task queuing with Redis as broker, priority queues, task routing to specialized workers, and built-in retry/dead-letter mechanisms. This keeps the API server responsive and allows independent scaling of compute resources.

### 3. PostgreSQL/PostGIS as Primary Datastore
**Decision**: Use PostgreSQL with PostGIS for all persistent storage.
**Rationale**: PostGIS provides mature geospatial indexing (GiST), spatial query functions (ST_Within, ST_Intersects, ST_Distance), and raster support. This eliminates the need for a separate spatial database or tile server for vector data. Raster tiles are stored in object storage (S3/MinIO) with metadata and footprints in PostGIS, combining the scalability of object storage with the queryability of a relational database.

### 4. Ensemble ML Architecture
**Decision**: Train multiple model types (RF, XGBoost, LightGBM, CatBoost, SVM, KNN, MLP) and combine via soft/hard voting.
**Rationale**: No single model consistently outperforms others across diverse urban morphologies. Ensemble methods reduce overfitting risk and improve generalization. The voting ensemble provides robust uncertainty estimates through prediction variance across constituent models. Each model captures different patterns: tree-based models handle non-linear interactions well, SVM works for high-dimensional spaces, and MLP captures complex feature hierarchies.

### 5. Object Storage for Raster Data
**Decision**: Store GeoTIFF files in S3-compatible object storage (MinIO for self-hosted, S3 for cloud).
**Rationale**: Raster files are large (100-500 MB per scene), append-only, and rarely modified. Object storage provides cost-effective, scalable storage with built-in replication and CDN integration. Cloud-optimized GeoTIFFs (COGs) enable server-side range requests for efficient tile serving without a dedicated tile server.

### 6. Module Registry Pattern
**Decision**: Register all services, ML models, and data sources via a central registry.
**Rationale**: The registry pattern enables plugin-like extensibility — new acquisition sources (e.g., MODIS, VIIRS) or ML models can be added by implementing a common interface and registering with the registry. The registry also supports dependency resolution, lifecycle management (init/shutdown), and centralized health checks.

### 7. SHAP for Explainability
**Decision**: Use SHAP (TreeExplainer, KernelExplainer) for all model explanations.
**Rationale**: SHAP provides theoretically grounded Shapley value explanations consistent with cooperative game theory. TreeExplainer is computationally efficient for tree-based models (RF, XGBoost, LightGBM, CatBoost) with O(TL²⁰) complexity. KernelExplainer provides model-agnostic explanations for SVM, KNN, and MLP. SHAP visualizations (beeswarm, waterfall, dependence) are directly consumable by urban planners and policymakers.

### 8. Redis Multi-Role
**Decision**: Use Redis as cache, Celery broker, and rate-limiter store.
**Rationale**: Consolidating infrastructure reduces operational complexity. Redis's in-memory performance supports sub-millisecond cache lookups for raster tile metadata and feature vectors. As a Celery broker, it provides reliable task delivery with optional persistence. The rate limiter uses Redis sorted sets for sliding window rate counting. A single Redis cluster with appropriate persistence configuration handles all three roles.

### 9. OpenTelemetry for Observability
**Decision**: Use OpenTelemetry for distributed tracing, with Prometheus metrics and Loki logs.
**Rationale**: OpenTelemetry provides a unified, vendor-neutral instrumentation API. Traces propagate across the API server, Celery workers, and database calls, enabling end-to-end latency analysis. Prometheus scrapes metrics from instrumented endpoints for CPU, memory, request duration, and ML prediction latency. Loki aggregates structured logs from all containers with minimal overhead.

### 10. Nginx as API Gateway
**Decision**: Use Nginx for TLS termination, rate limiting, static file serving, and reverse proxy.
**Rationale**: Nginx handles connection management more efficiently than Python-based servers. It provides TLS termination with Let's Encrypt auto-renewal, configurable rate limiting before requests reach the application layer, and direct serving of static MapLibre tile assets. The reverse proxy configuration enables blue-green deployments with zero downtime.

## Registry Pattern Explanation

The registry pattern centralizes service discovery and lifecycle management. Implemented via Python's `__init_subclass__` metaclass mechanism, it automatically registers all concrete implementations of abstract base classes.

```
class ServiceRegistry:
    """Central registry for all platform services."""

    _services: dict[str, type["BaseService"]] = {}
    _instances: dict[str, "BaseService"] = {}

    @classmethod
    def register(cls, name: str, service_cls: type["BaseService"]) -> None:
        cls._services[name] = service_cls

    @classmethod
    def get_service(cls, name: str) -> "BaseService":
        if name not in cls._instances:
            cls._instances[name] = cls._services[name]()
        return cls._instances[name]

    @classmethod
    def get_all_services(cls) -> list["BaseService"]:
        return [cls.get_service(name) for name in cls._services]

    @classmethod
    async def initialize_all(cls) -> None:
        for svc in cls.get_all_services():
            await svc.initialize()

    @classmethod
    async def shutdown_all(cls) -> None:
        for svc in reversed(cls.get_all_services()):
            await svc.shutdown()
```

## Module Registry Pattern

Each domain module registers its service, models, and schemas at import time using the `@register` decorator:

```
@register("heat", "service")
class HeatService(BaseService):
    @classmethod
    def get_registry_key(cls) -> str:
        return "heat"

    async def initialize(self) -> None:
        self.repository = HeatRepository()

    async def detect_uhi(self, project_id: UUID) -> UHIResult:
        """Detect urban heat island effect using LST analysis."""
        ...


@register("models", "random_forest")
@register("models", "rf")
class RandomForestModel(BaseMLModel):
    model_type = "random_forest"

    def create_estimator(self) -> Any:
        return RandomForestRegressor(
            n_estimators=500,
            max_depth=20,
            min_samples_leaf=5,
            n_jobs=-1,
            random_state=42,
        )


@register("sources", "landsat8")
@register("sources", "landsat9")
class LandsatAcquisitionSource(BaseAcquisitionSource):
    provider = "USGS"
    bands = {
        "coastal": 1, "blue": 2, "green": 3, "red": 4,
        "nir": 5, "swir1": 6, "swir2": 7,
        "pan": 8, "cirrus": 9, "tirs1": 10, "tirs2": 11,
    }
```

This allows the system to discover all modules at runtime without hardcoded import paths:

```
# In app startup
ServiceRegistry.initialize_all()
SourceRegistry.discover("heatt.acquisition")
ModelRegistry.discover("heatt.ml.models")
```

## Error Handling Strategy

### Layered Error Model

```
┌──────────────────────────────────────────────┐
│               PRESENTATION LAYER              │
│  (FastAPI exception handlers)                 │
│  ┌────────────────────────────────────────┐   │
│  │  http_exception_handler()              │   │
│  │  validation_exception_handler()        │   │
│  │  python_exception_handler()            │   │
│  │  custom_domain_exception_handler()     │   │
│  └────────────────────────────────────────┘   │
└──────────────────────┬───────────────────────┘
                       │ catches & maps
┌──────────────────────┴───────────────────────┐
│               SERVICE LAYER                    │
│  Raises domain-specific exceptions:           │
│  ┌────────────────────────────────────────┐   │
│  │  SceneNotFoundError                    │   │
│  │  ModelNotTrainedError                  │   │
│  │  InvalidGeometryError                  │   │
│  │  AcquisitionFailedError                │   │
│  │  InsufficientDataError                 │   │
│  │  PredictionQualityError                │   │
│  │  RecommendationInfeasibleError         │   │
│  │  SimulationConvergenceError            │   │
│  └────────────────────────────────────────┘   │
└──────────────────────┬───────────────────────┘
                       │ raises
┌──────────────────────┴───────────────────────┐
│               REPOSITORY LAYER                 │
│  Wraps DB/driver errors:                      │
│  ┌────────────────────────────────────────┐   │
│  │  DatabaseConnectionError               │   │
│  │  QueryExecutionError                   │   │
│  │  ConstraintViolationError             │   │
│  └────────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

### Error Response Format

All errors return a standardized JSON body:

```json
{
  "error": {
    "code": "SCENE_NOT_FOUND",
    "message": "Satellite scene with ID abc-123 not found",
    "details": {
      "scene_id": "abc-123",
      "provider": "landsat8"
    },
    "trace_id": "4a1f3c8e-b701-4f2a-9d5e-c2f3b8a1d6e7",
    "timestamp": "2026-07-02T14:30:00Z"
  }
}
```

### Exception Hierarchy

```
PlatformException (base)
├── AuthenticationException
│   ├── InvalidCredentialsError
│   ├── TokenExpiredError
│   └── InsufficientPermissionsError
├── ResourceNotFoundException
│   ├── UserNotFoundError
│   ├── ProjectNotFoundError
│   ├── SceneNotFoundError
│   └── ModelNotFoundError
├── ValidationException
│   ├── InvalidGeometryError
│   ├── InvalidDateRangeError
│   └── SchemaValidationError
├── ProcessingException
│   ├── AcquisitionFailedError
│   ├── InsufficientDataError
│   ├── ModelTrainingError
│   ├── PredictionError
│   └── SimulationError
├── ConflictException
│   ├── DuplicateResourceError
│   └── ResourceLockedError
└── ExternalServiceException
    ├── USGSApiError
    ├── ESAApiError
    └── WeatherApiError
```

### Retry and Backoff Strategy

- **Network/Transient errors**: Retry with exponential backoff (3 attempts, base delay 1s, max 30s)
- **Rate limit errors (429)**: Retry after `Retry-After` header with jitter
- **Validation errors**: No retry — return 422 immediately
- **Internal errors (500)**: Log full trace, return generic error, alert on-call via PrometheusAlertManager
- **Celery task failures**: Automatic retry for transient failures (max_retries=3, countdown=60), dead-letter queue for persistent failures

### Idempotency

- All POST endpoints accept `Idempotency-Key` header
- Idempotency keys stored in Redis with 24-hour TTL
- On duplicate key, return original response with 200 status
- On failure with duplicate key, return 409 Conflict

## Key Architectural Principles

### Separation of Concerns

The codebase is organized into four distinct layers, each with a single, well-defined responsibility:

| Layer | Responsibility | Dependencies |
|---|---|---|
| **API** (`api/`) | HTTP request handling, validation, routing, response formatting | FastAPI, Pydantic schemas |
| **Service** (`services/`) | Business logic, orchestration, workflow coordination | Domain models, repositories |
| **Domain** (`domain/`) | Core business entities, rules, enumerations | SQLAlchemy, GeoAlchemy2 |
| **Infrastructure** (`core/`) | Cross-cutting concerns: config, auth, logging, telemetry | External libraries |

Each layer communicates only with the layer directly below it. The API layer never accesses the database directly — it delegates to services, which use repositories against domain models. This ensures that changes to infrastructure (e.g., switching from PostgreSQL to a different database) do not ripple through the application.

### Single Responsibility

Every class and module has exactly one reason to change:

- **`LandsatAcquisitionSource`**: Only handles Landsat-specific API interaction and band mapping
- **`AtmosphericCorrectionRTE`**: Only implements the radiative transfer equation correction
- **`KnapsackOptimizer`**: Only solves the 0/1 knapsack problem for budget optimization
- **`DriftDetector`**: Only computes drift metrics (PSI, KS statistic) between reference and production distributions
- **`SHAPExplainer`**: Only generates and formats Shapley value explanations

This makes the codebase navigable, testable, and maintainable. A developer working on cloud masking does not need to understand knapsack optimization.

### Dependency Injection

Dependencies are explicitly declared and injected rather than imported or instantiated internally:

```python
class HeatService:
    def __init__(
        self,
        db_session: AsyncSession,
        raster_repo: RasterRepository,
        cache: RedisCache,
        telemetry: Tracer,
    ):
        self._db = db_session
        self._raster_repo = raster_repo
        self._cache = cache
        self._tracer = telemetry
```

FastAPI's dependency injection system resolves these at runtime:

```python
async def get_heat_service(
    db: AsyncSession = Depends(get_db),
    cache: RedisCache = Depends(get_redis),
    tracer: Tracer = Depends(get_tracer),
) -> HeatService:
    return HeatService(
        db_session=db,
        raster_repo=RasterRepository(db),
        cache=cache,
        telemetry=tracer,
    )
```

This enables:
- **Testability**: Dependencies can be mocked/stubbed in unit tests
- **Flexibility**: Implementations can be swapped without changing consumers
- **Clarity**: The dependency graph is explicit and auditable
- **Lifecycle management**: Services can be initialized and shut down in dependency order

### Additional Principles

- **Fail Fast**: Validate inputs at the API boundary before any processing begins. Invalid requests are rejected with 422 status and detailed error messages before reaching service or database layers.
- **CQRS Adjacent**: Read operations (GET endpoints) use optimized query paths with Redis caching. Write operations (POST, PUT, DELETE) go through the full service layer with transactional integrity. Complex read models (e.g., UHI dashboards) are materialized as PostgreSQL views.
- **Eventual Consistency for Async**: Satellite acquisition, ML training, and scenario simulation are eventually consistent. The API returns 202 Accepted with a task ID immediately, and progress is communicated via WebSocket notifications.
- **Defense in Depth**: Input validation at API schema level, business rule validation at service level, constraint validation at database level. No layer trusts the layer above it.
- **Observability by Default**: Every service method emits a span with duration, success/failure status, and key parameters. Metrics are automatically recorded via OpenTelemetry instrumentations. Logs are structured (JSON) with trace context correlation.
