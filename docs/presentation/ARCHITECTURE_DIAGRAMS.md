# Architecture Diagrams — Urban Heat Mitigation Platform

## Bharat Antariksh Hackathon

> All diagrams are text-based (ASCII art) for embedding in documentation,
> presentations, and quick reference. Each diagram includes a legend and
> explanation.

---

## Table of Contents

1. [High-Level Component Diagram](#1-high-level-component-diagram)
2. [Data Flow Diagram](#2-data-flow-diagram)
3. [ML Pipeline Diagram](#3-ml-pipeline-diagram)
4. [Deployment Architecture Diagram](#4-deployment-architecture-diagram)
5. [Module Dependency Tree](#5-module-dependency-tree)

---

## 1. High-Level Component Diagram

```
+-----------------------------------------------------------------------------+
|                        URBAN HEAT MITIGATION PLATFORM                        |
|                         HIGH-LEVEL COMPONENT DIAGRAM                         |
+-----------------------------------------------------------------------------+

                                   + - - - - - - - - - - - - - - - - - - +
                                   |  EXTERNAL DATA SOURCES               |
                                   |                                      |
                                   |  +----------+ +----------+           |
                                   |  |  USGS    | |   ESA    |           |
                                   |  | Landsat  | | Sentinel |           |
                                   |  |  8 / 9   | |  2 / 5P  |           |
                                   |  +----+-----+ +----+-----+           |
                                   |       |            |                 |
                                   |  +----v------------v-----+           |
                                   |  |    ISRO Bhuvan        |           |
                                   |  |  OGC WMS / WCS        |           |
                                   |  +----------+------------+           |
                                   +-------------+-----------------------+
                                                 |
                      +--------------------------+--------------------------+
                      |                          |                          |
                      |           +--------------v--------------+           |
                      |           |    DATA ACQUISITION LAYER    |           |
                      |           |                              |           |
                      |           |  +------------------------+  |           |
                      |           |  |   STAC API Client      |  |           |
                      |           |  |   - Search catalog     |  |           |
                      |           |  |   - Download assets    |  |           |
                      |           |  |   - Parse metadata     |  |           |
                      |           |  +-----------+------------+  |           |
                      |           |              |               |           |
                      |           |  +-----------+------------+  |           |
                      |           |  |   Bhuvan OGC Client    |  |           |
                      |           |  |   - WMS tiles          |  |           |
                      |           |  |   - WCS coverages      |  |           |
                      |           |  |   - WFS features       |  |           |
                      |           |  +-----------+------------+  |           |
                      |           +--------------+--------------+           |
                      |                          |                          |
                      |           +--------------v--------------+           |
                      |           |    PROCESSING ENGINE LAYER   |           |
                      |           |                              |           |
                      |           |  +------------------------+  |           |
                      |           |  |   Preprocessing         |  |           |
                      |           |  |   - Cloud masking      |  |           |
                      |           |  |   - Atmos. correction  |  |           |
                      |           |  |   - Resampling         |  |           |
                      |           |  |   - Reprojection       |  |           |
                      |           |  +-----------+------------+  |           |
                      |           |              |               |           |
                      |           |  +-----------+------------+  |           |
                      |           |  |   Spectral Indices      |  |           |
                      |           |  |   - NDVI, NDBI, NDWI   |  |           |
                      |           |  |   - BUI, UI, SAVI      |  |           |
                      |           |  |   - 25+ total indices  |  |           |
                      |           |  +-----------+------------+  |           |
                      |           |              |               |           |
                      |           |  +-----------+------------+  |           |
                      |           |  |   LST Retrieval         |  |           |
                      |           |  |   - Mono-window        |  |           |
                      |           |  |   - Emissivity corr.   |  |           |
                      |           |  |   - 1.5C accuracy      |  |           |
                      |           |  +-----------+------------+  |           |
                      |           |              |               |           |
                      |           |  +-----------+------------+  |           |
                      |           |  |   UHI Detection         |  |           |
                      |           |  |   - Getis-Ord Gi*      |  |           |
                      |           |  |   - DBSCAN clustering  |  |           |
                      |           |  |   - Severity classif.  |  |           |
                      |           |  +-----------+------------+  |           |
                      |           +--------------+--------------+           |
                      |                          |                          |
                      |           +--------------v--------------+           |
                      |           |       AI ENGINE LAYER        |           |
                      |           |                              |           |
                      |           |  +------------------------+  |           |
                      |           |  |   Feature Engineering   |  |           |
                      |           |  |   - 47 features        |  |           |
                      |           |  |   - Spatial context    |  |           |
                      |           |  |   - Texture (GLCM)     |  |           |
                      |           |  |   - Temporal           |  |           |
                      |           |  +-----------+------------+  |           |
                      |           |              |               |           |
                      |           |  +-----------+------------+  |           |
                      |           |  |   ML Model Training     |  |           |
                      |           |  |   - 8 model types      |  |           |
                      |           |  |   - Hyperparam tuning  |  |           |
                      |           |  |   - Cross-validation   |  |           |
                      |           |  +-----------+------------+  |           |
                      |           |              |               |           |
                      |           |  +-----------+------------+  |           |
                      |           |  |   Ensemble Fusion       |  |           |
                      |           |  |   - Weighted avg       |  |           |
                      |           |  |   - Stacking           |  |           |
                      |           |  |   - Voting             |  |           |
                      |           |  +-----------+------------+  |           |
                      |           |              |               |           |
                      |           |  +-----------+------------+  |           |
                      |           |  |   XAI Engine            |  |           |
                      |           |  |   - SHAP (Tree/Linear) |  |           |
                      |           |  |   - Counterfactuals    |  |           |
                      |           |  |   - Feature importance |  |           |
                      |           |  +-----------+------------+  |           |
                      |           |              |               |           |
                      |           |  +-----------+------------+  |           |
                      |           |  |   Recommendation +      |  |           |
                      |           |  |   Optimization Engine   |  |           |
                      |           |  |   - 0/1 knapsack       |  |           |
                      |           |  |   - Scenario simul.    |  |           |
                      |           |  +-----------+------------+  |           |
                      |           +--------------+--------------+           |
                      |                          |                          |
                      |           +--------------v--------------+           |
                      |           |    PRESENTATION LAYER        |           |
                      |           |                              |           |
                      |           |  +------------------------+  |           |
                      |           |  |   React 19 Dashboard    |  |           |
                      |           |  |   - TypeScript + Vite  |  |           |
                      |           |  |   - TailwindCSS        |  |           |
                      |           |  |   - 10+ route pages    |  |           |
                      |           |  +------+---------+-------+  |           |
                      |           |         |         |          |           |
                      |           |  +------v--+ +---v--------+ |           |
                      |           |  |MapLibre | |  ECharts   | |           |
                      |           |  | GL 3D   | |  Charts    | |           |
                      |           |  +---------+ +------------+ |           |
                      |           +------------------------------+           |
                      |                                                      |
                      |           +------------------------------+           |
                      |           |    DATA INFRASTRUCTURE LAYER  |           |
                      |           |                              |           |
                      |           |  +----------+ +----------+  |           |
                      |           |  |PostgreSQL| |  Redis   |  |           |
                      |           |  | /PostGIS | |  Cache   |  |           |
                      |           |  +----------+ +----------+  |           |
                      |           |  +----------+ +----------+  |           |
                      |           |  |  MinIO   | |Celery Q  |  |           |
                      |           |  |  Object  | |  Tasks   |  |           |
                      |           |  +----------+ +----------+  |           |
                      |           +------------------------------+           |
                      +------------------------------------------------------+
```

### Legend

| Symbol | Meaning |
|--------|---------|
| `+--+` | Box = Component / Module |
| `|` , `-` | Lines = Data flow / Dependency |
| `v` | Direction of data flow |
| `...` | External boundary |
| **Layers** | Horizontal sections = Architectural layers |

### Explanation

The platform follows a strict layered architecture with unidirectional data flow:

1. **External Data Sources**: Satellite imagery providers (USGS, ESA, ISRO) feed data into the platform through standardized APIs (STAC, OGC).
2. **Data Acquisition Layer**: Handles authentication, search, download, and metadata parsing. Abstracts away differences between providers.
3. **Processing Engine Layer**: The scientific core — transforms raw satellite imagery into derived products (spectral indices, LST, UHI maps).
4. **AI Engine Layer**: Feature engineering, ML training/inference, ensemble fusion, XAI explanations, and decision optimization.
5. **Presentation Layer**: React dashboard with map (MapLibre GL) and chart (ECharts) visualization.
6. **Data Infrastructure Layer**: Persistent storage (PostgreSQL/PostGIS), caching (Redis), object storage (MinIO), and task queue (Celery).

Each layer communicates only with the adjacent layers, ensuring clean separation of concerns and testability.

---

## 2. Data Flow Diagram

```
+-----------------------------------------------------------------------------+
|                           DATA FLOW DIAGRAM                                  |
|                  Satellite Imagery to Actionable Recommendations              |
+-----------------------------------------------------------------------------+

  SATELLITE                    PROCESSING                     FEATURES
  ---------                    ----------                     --------

  Landsat 8/9 ---+             +----------+     +----------+
                 +--> Cloud ---+ Atmos.   +--->+ Resample +--->+ ROI Clip
  Sentinel-2 ----+     Mask    + Correct. +    + (10m)    +    + (Bounds)
                       (Fmask)  (DOS1)                      |
                                                           |
                +-------------------------------------------+
                v
         +----------+     +----------+     +----------+
         |  NDVI    |     |  NDBI    |     |  NDWI    |
         |Vegetation|     | Built-up |     |  Water   |    25+ Spectral
         | 0.3-0.9  |     |-0.5-0.3  |     |-0.8-0.2  |    Indices
         +----------+     +----------+     +----------+
                |              |                 |
                +--------------+-----------------+
                               v
                        +--------------+
                        |  Emissivity  |
                        |  Estimation  |
                        | (NDVI-thr)   |
                        +------+-------+
                               |
                               v
                        +--------------+
                        | Mono-Window  |
                        | LST Retrieval|
                        | 10.6-11.2um  |
                        +------+-------+
                               |
                               v
                        +--------------+
                        | UHI Hot Spot |
                        | Analysis     |
                        | Getis-Ord    |
                        | Gi* + FDR    |
                        +------+-------+
                               |
           +-------------------+-------------------+
           v                   v                   v
    +--------------+   +--------------+   +--------------+
    |  Features    |   |  Training    |   |  Inference   |
    |  - Spectral  |   |  - 70% split |   |  - New scenes|
    |  - Spatial   |   |  - 5-fold CV |   |  - Prediction|
    |  - Texture   |   |  - 8 models  |   |  - R2=0.91  |
    |  - Temporal  |   |  - HPO search|   |  - MAE=0.87C|
    +------+-------+   +------+-------+   +------+-------+
           |                  |                   |
           +------------------+-------------------+
                              v
                       +--------------+
                       |  Ensemble    |
                       |  Fusion      |
                       |  (Weighted)  |
                       +------+-------+
                              |
           +------------------+------------------+
           v                  v                  v
    +--------------+  +--------------+  +--------------+
    |  SHAP XAI    |  |Counterfactual|  |  Drift Check |
    |  - Force plot|  |  - What-if   |  |  - PSI > .25 |
    |  - Summary   |  |  - Feasible  |  |  - Retrain   |
    |  - Dependence|  |  - Actionable|  |  - Alert     |
    +------+-------+  +------+-------+  +--------------+
           |                  |
           +------------------+
                              v
                       +--------------+
                       |Recommendation|
                       |  Engine      |
                       |  6 strategies|
                       |  Cost-benefit|
                       +------+-------+
                              |
                              v
                       +--------------+
                       | 0/1 Knap.   |
                       |  Optimizer   |
                       | Max: sum(ben)|
                       | S.t. sum(cst)|
                       | <= budget    |
                       +------+-------+
                              |
                              v
                       +--------------+
                       |  Scenario    |
                       |  Simulator   |
                       |  Templates   |
                       |  Comparison  |
                       +------+-------+
                              |
                              v
                       +--------------+
                       |   Report     |
                       |   Generator  |
                       |   (PDF)      |
                       +--------------+
```

### Legend

| Symbol | Meaning |
|--------|---------|
| `+>` | Data transformation / processing step |
| `Products` | Intermediate data products |
| `(Bold)` | Key parameters / metrics |
| `Algorithms` | Named algorithms |
| `|` | Parallel branches / alternatives |

### Explanation

Data flows unidirectionally from raw satellite imagery through successive transformations:

1. **Raw to Processed**: Raw DN values to cloud-masked, atmospherically corrected, resampled radiance values.
2. **Processed to Products**: Radiance to spectral indices (25+), LST, emissivity, UHI hotspots.
3. **Products to Features**: Derived products to feature vectors (47 features per pixel/zone).
4. **Features to Models**: Feature vectors to trained ML models to predictions with metrics.
5. **Predictions to Insights**: Predictions to SHAP explanations, counterfactuals, drift assessment.
6. **Insights to Actions**: Explanations to cost-effectiveness scores to knapsack optimization to ranked recommendations.
7. **Actions to Evaluation**: Recommendations to scenario simulations to impact assessment to PDF reports.

---

## 3. ML Pipeline Diagram

```
+-----------------------------------------------------------------------------+
|                          ML PIPELINE DIAGRAM                                 |
|              End-to-End Machine Learning for Urban Heat Prediction          |
+-----------------------------------------------------------------------------+

                              +------------------+
                              |   Satellite Data  |
                              |   (Landsat, S2)   |
                              +--------+---------+
                                       |
                              +--------v---------+
                              |  Preprocessing    |
                              |  - Cloud mask    |
                              |  - Radiance corr |
                              |  - Resample 10m  |
                              +--------+---------+
                                       |
                              +--------v---------+
                              |  25+ Spectral    |
                              |   Indices        |
                              |  - NDVI, NDBI    |
                              |  - LST, albedo   |
                              +--------+---------+
                                       |
                              +--------v---------+
                              |  Feature         |
                              |  Engineering     |
                              |  (47 features)   |
                              +--------+---------+
                                       |
                    +------------------+------------------+
                    |                  |                  |
            +-------v-------+  +------v------+  +-------v-------+
            |  Training     |  |  Validation |  |  Test         |
            |  (70%)        |  |  (15%)      |  |  (15%)        |
            |  Spatially    |  |  Spatially  |  |  Held-out     |
            |  Blocked CV   |  |  Blocked    |  |  Evaluation   |
            +-------+-------+  +------+------+  +-------+-------+
                    |                  |                  |
                    +------------------+------------------+
                                       |
                            +----------v----------+
                            |  Hyperparameter     |
                            |  Optimization        |
                            |  (Random Search)     |
                            |  100 iterations      |
                            |  8 models x 5-fold   |
                            +----------+----------+
                                       |
              +------------------------+------------------------+
              |                        |                        |
     +--------v--------+    +---------v--------+    +---------v--------+
     |  Base Models     |    |  Tree Models     |    |  Neural Net      |
     |                   |    |                   |    |                   |
     |  Linear (R2.68)  |    |  XGBoost (R2.89) |    |  MLP (R2.81)    |
     |  Ridge (R2.72)   |    |  LightGBM(R2.88) |    |                   |
     |                   |    |  CatBoost(R2.87) |    |                   |
     |                   |    |  RF (R2.85)      |    |                   |
     |                   |    |  GBR (R2.84)     |    |                   |
     +--------+---------+    +---------+--------+    +---------+--------+
              |                        |                        |
              +------------------------+------------------------+
                                       |
                            +----------v----------+
                            |  Ensemble Fusion     |
                            |                      |
                            |  +----------------+  |
                            |  |Weighted Avg    |  |  R2=0.91
                            |  |(Nelder-Mead)   |  |  RMSE=1.15
                            |  +----------------+  |
                            |  |Stacking        |  |  R2=0.90
                            |  |(Ridge Meta)    |  |  RMSE=1.18
                            |  +----------------+  |
                            |  |Voting          |  |  R2=0.89
                            |  |(Top-3 Avg)     |  |  RMSE=1.23
                            |  +----------------+  |
                            +----------+----------+
                                       |
                            +----------v----------+
                            |  Drift Detection     |
                            |                      |
                            |  Data Drift (PSI)    |
                            |  Concept Drift       |
                            |  (Residual Monitor)  |
                            |                      |
                            |  Alert if:           |
                            |  PSI > 0.25          |
                            |  MAE increase > 20%  |
                            +----------+----------+
                                       |
              +------------------------+------------------------+
              |                        |                        |
     +--------v--------+    +---------v--------+    +---------v--------+
     |  SHAP XAI       |    |  Counterfactual  |    |  Model Export    |
     |                   |    |                   |    |                   |
     |  TreeSHAP       |    |  Minimal pert.   |    |  Pickle format   |
     |  LinearSHAP     |    |  Realistic cons. |    |  MLflow registry |
     |  KernelSHAP     |    |  "If NDVI +0.2" |    |  Docker image    |
     |                   |    |  -> dT = -1.8C  |    |  API endpoint    |
     +-------------------+    +-------------------+    +------------------+
```

### Legend

| Symbol | Meaning |
|--------|---------|
| `Box` | Processing stage |
| `(...)` | Key metrics or parameters |
| `-|-` | Branching / multiple paths |
| **Bold** | Best performing models |
| `R2=0.91` | Example metric (R² score) |

### Explanation

The ML pipeline is designed for both predictive accuracy and scientific explainability:

1. **Data Preparation**: Satellite imagery is preprocessed and transformed into spectral indices and LST. Feature engineering produces 47 features per sample combining spectral, spatial, textural, and temporal information.

2. **Train/Val/Test Split**: Spatially blocked split prevents leakage between train and validation sets. 5-fold cross-validation with spatial blocking ensures robust evaluation.

3. **Hyperparameter Optimization**: Random search (100 iterations) for each of 8 model types. Each configuration is evaluated with 5-fold CV on the training set.

4. **Base Model Training**: 8 models trained in parallel — from simple linear baselines to sophisticated gradient boosting. Each model captures different aspects of the urban heat phenomenon.

5. **Ensemble Fusion**: Three fusion strategies combine model strengths. Weighted averaging (Nelder-Mead optimization) outperforms all individual models at R² = 0.91.

6. **Drift Detection**: Continuous monitoring of data and concept drift. Population Stability Index (PSI) flags feature distribution shifts. Residual monitoring catches concept drift.

7. **Explainability**: SHAP (three variants) provides both global and local explanations. Counterfactual generation translates ML insights into actionable planning language.

---

## 4. Deployment Architecture Diagram

```
+-----------------------------------------------------------------------------+
|                        DEPLOYMENT ARCHITECTURE                               |
|                    Docker Microservices on Single Host                        |
+-----------------------------------------------------------------------------+

  +-------------------------------------------------------------------------+
  |                          INTERNET / USERS                                |
  |                         (Browser / API Clients)                          |
  +-----------------------------------+-------------------------------------+
                                      |
                                      v
                              +---------------+
                              |   Nginx        |
                              |   Port 443     |
                              |   (HTTPS)      |
                              |   Port 80      |
                              |   (Redirect)   |
                              |                |
                              |  Rate Limiting |
                              |  SSL Term.     |
                              +-------+-------+
                                      |
              +-----------------------+-----------------------+
              |                       |                       |
              v                       v                       v
    +------------------+   +------------------+   +------------------+
    |  Frontend        |   |  API Server      |   |  Monitoring      |
    |  (React 19)      |   |  (FastAPI)       |   |  (Grafana)       |
    |                   |   |  Uvicorn x4     |   |  Port 3000       |
    |  Nginx           |   |  Port 8000       |   |                   |
    |  Port 80/443     |   |                   |   |  Dashboards      |
    |                   |   |  REST + WebSocket|   |  Alerts          |
    |  Cache: Browser  |   |  CORS, Auth     |   |                   |
    +------------------+   +--------+----------+   +------------------+
                                    |
          +-------------------------+-------------------------+
          |                         |                         |
          v                         v                         v
+------------------+   +------------------+   +------------------+
|  PostgreSQL      |   |  Redis           |   |  Celery Workers  |
|  (PostGIS)       |   |  (Cache/Broker)  |   |  (x2-4)          |
|  Port 5432       |   |  Port 6379       |   |                   |
|                   |   |                   |   |  Async Tasks:    |
|  Geo. Queries    |   |  Session Store   |   |  - Preprocess    |
|  Raster Storage  |   |  Result Cache    |   |  - Compute       |
|  Alembic Migrate |   |  Task Queue      |   |  - Train         |
|                   |   |                   |   |  - Report        |
|  Volume: pgdata  |   |  Volume: redis   |   |  - Export        |
+------------------+   +------------------+   +------------------+
                                                        |
                                                        v
                                               +------------------+
                                               |  MinIO Object    |
                                               |  Storage (S3)    |
                                               |  Port 9000       |
                                               |                   |
                                               |  GeoTIFF Archive |
                                               |  ML Model Store  |
                                               |  Report Assets   |
                                               |                   |
                                               |  Volume: minio   |
                                               +------------------+

  +-------------------------------------------------------------------------+
  |                      MONITORING STACK                                     |
  |                                                                           |
  |  +--------------+  +--------------+  +--------------+  +--------------+  |
  |  |  Prometheus  |  |    Grafana   |  |    Loki      |  |  OpenTelemetry|  |
  |  |  Port 9090   |  |    Port 3000  |  |  Port 3100   |  |  Port 4317   |  |
  |  |              |  |              |  |              |  |              |  |
  |  | Metrics      |  | Dashboards   |  | Logs         |  | Traces       |  |
  |  | Scrape       |  | Alerts       |  | Query        |  | Span Export  |  |
  |  | Storage      |  | Annotations  |  | Structured   |  | Distributed  |  |
  |  +--------------+  +--------------+  +--------------+  +--------------+  |
  |                                                                           |
  |  +--------------+  +--------------+                                      |
  |  |  Flower      |  |  cAdvisor    |                                      |
  |  |  Port 5555   |  |  Port 8080   |                                      |
  |  |              |  |              |                                      |
  |  |  Celery      |  |  Container   |                                      |
  |  |  Monitoring  |  |  Metrics     |                                      |
  |  +--------------+  +--------------+                                      |
  +-------------------------------------------------------------------------+

  +-------------------------------------------------------------------------+
  |                      VOLUMES & PERSISTENCE                                |
  |                                                                           |
  |  pgdata:/var/lib/postgresql/data        Database files                   |
  |  redis:/data                            Redis persistence                 |
  |  minio:/data                            Object storage                   |
  |  prometheus:/prometheus                 Metrics data                     |
  |  grafana:/var/lib/grafana               Dashboard configurations          |
  |  loki:/loki                             Log data                          |
  |  backup:/backup                         Automated DB dumps                |
  |  mlflow:/mlflow                         Model registry                    |
  +-------------------------------------------------------------------------+

  +-------------------------------------------------------------------------+
  |                      NETWORK ISOLATION                                    |
  |                                                                           |
  |  +----------------------------------------------------------------------+ |
  |  |  External Network (nginx -> internet)                                 | |
  |  |   - Frontend, API exposed via Nginx reverse proxy                    | |
  |  |   - Grafana (optional: expose or VPN-only)                           | |
  |  +----------------------------------------------------------------------+ |
  |                                                                           |
  |  +----------------------------------------------------------------------+ |
  |  |  Internal Network (Docker bridge)                                    | |
  |  |   - All services communicate over internal network                   | |
  |  |   - Database ports not exposed to host                               | |
  |  |   - Worker processes have no external access                         | |
  |  +----------------------------------------------------------------------+ |
  +-------------------------------------------------------------------------+
```

### Legend

| Symbol | Meaning |
|--------|---------|
| `Box` | Docker service / container |
| `Port xxxx` | Exposed port |
| `Volume: name` | Persistent Docker volume |
| `+--+` | Grouped services |
| `-+-` | Network connection |
| `(Config)` | Configuration detail |

### Explanation

The deployment architecture follows a microservices pattern with Docker Compose:

1. **Reverse Proxy**: Nginx terminates SSL, handles rate limiting, and routes requests to either the frontend (static files) or API server (reverse proxy).

2. **Application Services**: Frontend (React SPA served by Nginx) and API (FastAPI with 4 Uvicorn workers) handle user requests. WebSocket connections provide real-time progress updates.

3. **Background Processing**: Celery workers consume tasks from Redis broker. Each worker can handle 4 concurrent tasks. Celery Beat schedules periodic tasks (data refresh, model retraining).

4. **Data Services**: PostgreSQL with PostGIS extension handles all structured and geospatial data. Redis provides caching and task queue. MinIO offers S3-compatible object storage for imagery and models.

5. **Monitoring Stack**: Prometheus collects metrics, Grafana visualizes dashboards, Loki aggregates logs, OpenTelemetry traces distributed requests. Flower monitors Celery tasks.

6. **Persistence**: Docker volumes ensure data survives container restarts. Automated backups run daily.

7. **Network Isolation**: External-facing services (Nginx) are on the external network. All other services communicate over an internal bridge network, with no host port exposure for databases.

---

## 5. Module Dependency Tree

```
+-----------------------------------------------------------------------------+
|                         MODULE DEPENDENCY TREE                               |
|                       Python Backend -- Import Graph                          |
+-----------------------------------------------------------------------------+

                                    app
                                     |
                    +----------------+----------------+
                    |                |                |
                  core              api             engine
                    |                |                |
        +-----------+-----------+    |     +----------+----------+
        |           |           |    |     |          |          |
     config     database     cache   |  satellite  preprocess  spectral
        |           |           |    |     |          |          |
        +-----------+           |    |     +----------+          |
        |                      |    |     |                     |
     security               celery   |     |                     |
        |                      |    |     |                     |
        +----------------------+    |     v                     |
                                    |    lst                    |
                                    |     |                     |
                                    |     +---------------------+
                                    |     v
                                    |    features
                                    |     |
                                    |     +----------+----------+
                                    |     v          v          v
                                    |   models     hpo       drift
                                    |     |          |          |
                                    |     +----------+          |
                                    |     v                     |
                                    |  ensemble                 |
                                    |     |                     |
                                    |     +---------------------+
                                    |     v
                                    |    xai
                                    |     |
                                    |     +---------------------+
                                    |     v                     v
                                    | counterfactual      recommendation
                                    |                          |
                                    |                     optimizer
                                    |                          |
                                    |                     simulation
                                    |                          |
                                    |                       report
                                    |
                              +-----+-----+
                              |           |
                            tasks      monitoring
                              |
                    +---------+---------+
                    |         |         |
                process   report    train

  +-------------------------------------------------------------------------+
  |  MODULE DEPENDENCIES (DIRECTED ACYCLIC GRAPH)                            |
  |                                                                           |
  |  Layer 0 (Foundation): config, database, cache, security                 |
  |  Layer 1 (Infrastructure): celery, monitoring                            |
  |  Layer 2 (Acquisition): satellite, preprocess                            |
  |  Layer 3 (Scientific): spectral, lst, uhi, features                      |
  |  Layer 4 (AI/ML): models, hpo, ensemble, drift, xai, counterfactual      |
  |  Layer 5 (Decision): recommendation, optimizer, simulation, report       |
  |  Layer 6 (Orchestration): tasks, api                                     |
  +-------------------------------------------------------------------------+

  +-------------------------------------------------------------------------+
  |  LAYER STRUCTURE                                                         |
  |                                                                           |
  |  +---------------------------------------------------------------------+ |
  |  |  Layer 6: Orchestration (tasks, api)                                 | |
  |  +---------------------------------------------------------------------+ |
  |  |  Layer 5: Decision (recommendation, optimizer, simulation, report)  | |
  |  +---------------------------------------------------------------------+ |
  |  |  Layer 4: AI/ML (models, ensemble, hpo, drift, xai, counterfactual) | |
  |  +---------------------------------------------------------------------+ |
  |  |  Layer 3: Scientific (spectral, lst, uhi, features)                 | |
  |  +---------------------------------------------------------------------+ |
  |  |  Layer 2: Acquisition (satellite, preprocess)                       | |
  |  +---------------------------------------------------------------------+ |
  |  |  Layer 1: Infrastructure (celery, monitoring)                       | |
  |  +---------------------------------------------------------------------+ |
  |  |  Layer 0: Foundation (config, database, cache, security)            | |
  |  +---------------------------------------------------------------------+ |
  |                                                                           |
  |  Dependency rule: A module can only depend on modules in the same or     |
  |  lower layer. No upward dependencies.                                    |
  +-------------------------------------------------------------------------+
```

### Legend

| Symbol | Meaning |
|--------|---------|
| `app` | Root package |
| `core`, `api`, `engine` | Sub-packages |
| `module` | Individual module |
| `|` | Dependency line |
| `+-+` | Branching dependency |
| `Layer N` | Architecture layer |

### Explanation

The module dependency tree follows a strict layered architecture:

**Dependency Rule**: A module at layer N can only depend on modules at layer N or lower. This ensures testability, maintainability, and clear separation of concerns.

**Layer 0 -- Foundation**: Configuration, database connection, caching, and security utilities. Every other module depends on these.

**Layer 1 -- Infrastructure**: Celery task configuration and monitoring instrumentation. Depends on Layer 0.

**Layer 2 -- Acquisition**: Satellite data download (STAC API, Bhuvan OGC) and preprocessing (cloud masking, atmospheric correction). Depends on Layers 0-1.

**Layer 3 -- Scientific**: Core domain logic -- spectral indices, LST retrieval, UHI detection, feature engineering. Depends on Layers 0-2.

**Layer 4 -- AI/ML**: Model training, hyperparameter optimization, ensemble fusion, drift detection, XAI, counterfactuals. Depends on Layers 0-3.

**Layer 5 -- Decision**: Recommendation engine, knapsack optimizer, scenario simulation, report generation. Depends on Layers 0-4.

**Layer 6 -- Orchestration**: Celery tasks and API routes. These are the entry points that compose workflows from lower layers. Depends on all lower layers.

This architecture ensures:
- Each layer can be tested independently
- Changes in lower layers propagate upward (never downward)
- New algorithms can be added at the appropriate layer without disturbing others
- Modules can be replaced as long as they maintain the same interface

---

## Diagram Index

| Diagram | Section | Description |
|---------|---------|-------------|
| High-Level Component | Section 1 | Full system architecture with all layers |
| Data Flow | Section 2 | End-to-end data transformation pipeline |
| ML Pipeline | Section 3 | Detailed ML training and inference workflow |
| Deployment | Section 4 | Docker microservices deployment architecture |
| Module Dependency | Section 5 | Python module import graph and layer structure |

---

*Architecture Diagrams v1.0 -- Bharat Antariksh Hackathon 2026*
