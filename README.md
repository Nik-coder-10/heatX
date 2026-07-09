<div align="center">

# HeatX - Urban Heat Mitigation Platform

[![Build](https://img.shields.io/github/actions/workflow/status/urbanheat/uhmp/ci.yml?branch=main&style=flat-square&logo=github)](https://github.com/urbanheat/uhmp/actions)
[![Tests](https://img.shields.io/badge/tests-450+_passing-2ea44f?style=flat-square&logo=pytest)](https://github.com/urbanheat/uhmp)
[![Coverage](https://img.shields.io/codecov/c/github/urbanheat/uhmp/main?style=flat-square&logo=codecov)](https://codecov.io/gh/urbanheat/uhmp)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Node 20](https://img.shields.io/badge/node-20_LTS-339933?style=flat-square&logo=node.js&logoColor=white)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)
[![Conventional Commits](https://img.shields.io/badge/conventional_commits-1.0.0-FE5196?style=flat-square&logo=git)](https://www.conventionalcommits.org/)

**AI-powered satellite remote sensing platform for detecting, predicting, and mitigating urban heat islands.**

[Features](#features) • [Architecture](#architecture) • [Quick Start](#quick-start) • [Workflow](#example-workflow) • [API](#api) • [Documentation](#documentation) • [Contributing](#contributing)

</div>

---

## Problem Statement

Urban Heat Islands (UHIs) cause cities to be 3–10°C hotter than surrounding
rural areas, leading to increased mortality, higher energy consumption,
worsened air quality, and disproportionate impacts on vulnerable communities.
Urban planners and policymakers lack accessible, data-driven tools to:

- Quantify UHI intensity at city-block resolution
- Predict future heat patterns under climate and land-use change
- Evaluate the cost-effectiveness of mitigation interventions
- Optimize limited budgets across competing mitigation strategies

The Urban Heat Mitigation Platform bridges this gap by combining satellite
remote sensing, machine learning, explainable AI, and geospatial optimization
into an end-to-end, open-source solution.

## Motivation

**Climate Change** — Global temperatures are rising, and urban areas bear the
brunt through the UHI effect. Cities are already 1–3°C warmer than their rural
hinterlands, and this gap widens during heatwaves.

**Public Health** — Extreme heat is the deadliest natural disaster in many
countries, causing more fatalities than floods, hurricanes, or tornadoes.
Heat-related mortality is projected to increase 3–5x by 2050.

**Social Equity** — UHI intensity is highest in low-income neighborhoods and
communities of color due to historical redlining and unequal distribution of
green infrastructure. Targeted mitigation can reduce this disparity.

**Actionable Science** — While satellite data and ML models exist in research
contexts, they remain inaccessible to city planners. This platform translates
cutting-edge remote sensing science into actionable urban policy tools.

## Features

| Category | Feature | Description |
|----------|---------|-------------|
| **Acquisition** | Landsat 8/9 | Scene search and download via USGS M2M API with cloud filtering |
| **Acquisition** | Sentinel-2 | Copernicus Data Space integration with Sen2Cor correction |
| **Acquisition** | ISRO Bhuvan | Indian subcontinent data access via Bhuvan APIs |
| **Acquisition** | Multi-sensor Fusion | Automatic cross-platform scene alignment and harmonization |
| **Indices** | NDVI | Normalized Difference Vegetation Index for vegetation health |
| **Indices** | NDWI | Normalized Difference Water Index for surface water detection |
| **Indices** | NDBI | Normalized Difference Built-up Index for impervious surfaces |
| **Indices** | NBRI | Normalized Burn Ratio Index for thermal anomalies |
| **Indices** | UI | Urban Index for density classification |
| **Indices** | BSI | Bare Soil Index for exposed soil mapping |
| **LST** | Split-Window | Dual-band TIRS algorithm with water vapor correction |
| **LST** | Mono-Window | Generalized single-channel for single-thermal-band sensors |
| **LST** | Emissivity Estimation | NDVI-threshold-based land surface emissivity |
| **LST** | Uncertainty Propagation | Pixel-wise error estimation from all input sources |
| **UHI** | Hotspot Detection | Getis-Ord Gi* statistics with FDR correction |
| **UHI** | Severity Zoning | 6-level classification (None to Extreme) |
| **UHI** | Temporal Profiling | Diurnal, seasonal, and interannual pattern analysis |
| **UHI** | Spatial Autocorrelation | Global and local Moran's I assessment |
| **Features** | 17 Geo-Features | NDVI, NDWI, NDBI, NBRI, UI, BSI, LST, UHI, Albedo, Elevation, Water Distance, Green Distance, Building Density, Population Density, Road Density, Aspect, Surface Roughness |
| **ML** | 8 Model Types | Random Forest, XGBoost, LightGBM, CatBoost, SVM, KNN, MLP, Gradient Boosting |
| **ML** | Ensemble Learning | Soft/hard voting, stacking with meta-learner |
| **ML** | Hyperparameter Search | GridSearch, RandomizedSearch, Optuna Bayesian optimization |
| **ML** | Cross-Validation | K-fold (3,5,10) with stratified sampling |
| **ML** | Drift Detection | Data drift (PSI, KS, JS) and concept drift (Page-Hinkley, ADWIN) |
| **XAI** | SHAP | Tree, Kernel, Deep, Linear explainers for all model types |
| **XAI** | Visualizations | Summary, dependence, waterfall, force, beeswarm, bar, violin |
| **XAI** | Counterfactuals | Genetic algorithm and gradient-based What-If analysis |
| **XAI** | Feature Importance | Permutation (with CI), Partial Dependence, ICE, H-statistic |
| **Mitigation** | 6 Profiles | Tree Plantation, Cool Roof, Green Roof, Reflective Pavement, Water Body Restoration, Urban Green Space |
| **Mitigation** | Cost-Effectiveness | Cooling potential per rupee with lifecycle cost models |
| **Mitigation** | Budget Optimization | 0/1 knapsack DP for constrained budget allocation |
| **Mitigation** | Pareto Frontier | Multi-objective optimization visualization |
| **Scenarios** | 7 Templates | Urban Greening, Cool Roof, Reflective Pavement, Combined, Climate Projection, Urban Growth, Custom |
| **Scenarios** | Monte Carlo | Latin Hypercube Sampling with 10,000+ iterations |
| **Scenarios** | Sensitivity | Sobol indices for parameter importance |
| **Dashboard** | Map Viewer | MapLibre GL with tile layers, vector boundaries, ROI tools |
| **Dashboard** | Charts | ECharts time-series, histograms, beeswarm, scatter, violin |
| **Dashboard** | Reports | PDF export with integrated maps and charts |
| **Dashboard** | Auth | JWT + OAuth2 with Google/GitHub SSO, RBAC |
| **Deployment** | Docker | Multi-stage builds, 13 containers, health checks |
| **Deployment** | Monitoring | Prometheus + Grafana + Loki + OpenTelemetry |
| **Deployment** | Database | PostgreSQL/PostGIS with Alembic migrations |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              React 19 SPA (TypeScript, Vite, TailwindCSS)            │  │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────────────┐  │  │
│  │  │MapLibre  │  │ ECharts   │  │Auth Views│  │ Scenario Designer │  │  │
│  │  │ GL Maps  │  │Visualizer │  │(JWT/OAuth)│  │ & Report Builder  │  │  │
│  │  └──────────┘  └───────────┘  └──────────┘  └───────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                    │  HTTPS / WSS
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          REVERSE PROXY                                     │
│                    Nginx (TLS, Rate Limiting, Gzip)                        │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                            API LAYER                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │         FastAPI (Python 3.11, async, Pydantic v2)                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ ┌──────────┐  │  │
│  │  │Satellite │ │ Indices  │ │  LST &    │ │  ML    │ │Mitigation│  │  │
│  │  │Acquisition│ │Computation│ │  UHI      │ │Inference│ │ & Scenarios│ │  │
│  │  └──────────┘ └──────────┘ └───────────┘ └────────┘ └──────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  ▼                  ▼                  ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   TASK QUEUE         │ │   AI/ML ENGINE       │ │   MONITORING        │
│  ┌───────────────┐  │ │  ┌───────────────┐  │ │  ┌───────────────┐  │
│  │   Celery      │  │ │  │ Model Training │  │ │  │  Prometheus   │  │
│  │(Redis Broker) │  │ │  │ • 8 Algorithms  │  │ │  │  (Metrics)    │  │
│  │ • Acquisition │  │ │  │ • Ensemble      │  │ │  └───────────────┘  │
│  │ • Processing  │  │ │  │ • HPO+CV       │  │ │  ┌───────────────┐  │
│  │ • Training    │  │ │  │ • Drift Detect  │  │ │  │   Grafana     │  │
│  │ • Simulation  │  │ │  └───────────────┘  │ │  │ (Dashboards)  │  │
│  └───────────────┘  │ │  ┌───────────────┐  │ │  └───────────────┘  │
└─────────────────────┘ │  │   SHAP XAI    │  │ │  ┌───────────────┐  │
                        │  │ • Explainer   │  │ │  │   Loki (Logs) │  │
┌─────────────────────┐ │  │ • Visuals     │  │ │  └───────────────┘  │
│   DATA LAYER         │ │  │ • Counterfact │  │ │  ┌───────────────┐  │
│  ┌───────────────┐  │ │  └───────────────┘  │ │  │ OpenTelemetry │  │
│  │ PostgreSQL    │  │ │  ┌───────────────┐  │ │  │ (Tracing)     │  │
│  │ / PostGIS     │  │ │  │Mitigation     │  │ │  └───────────────┘  │
│  │ • Vector data │  │ │  │• 6 Profiles   │  │ └─────────────────────┘
│  │ • Features    │  │ │  │• Knapsack Opt │  │
│  │ • Models reg  │  │ │  │• Pareto Front │  │
│  └───────────────┘  │ │  └───────────────┘  │
│  ┌───────────────┐  │ │  ┌───────────────┐  │
│  │   Redis       │  │ │  │  Scenarios    │  │
│  │ • Cache       │  │ │  │ • 7 Templates │  │
│  │ • Session     │  │ │  │ • Monte Carlo │  │
│  │ • Task broker │  │ │  │ • Sobol       │  │
│  └───────────────┘  │ │  └───────────────┘  │
│  ┌───────────────┐  │ └─────────────────────┘
│  │ Object Store  │  │
│  │ • Rasters     │  │
│  │ • Models (.onnx)│  │
│  └───────────────┘  │
└─────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19 + TypeScript | Component-based UI framework |
| **Frontend** | Vite | Build tool and development server |
| **Frontend** | TailwindCSS 3 | Utility-first styling |
| **Frontend** | MapLibre GL JS | WebGL vector map rendering |
| **Frontend** | ECharts | Interactive charting (60+ chart types) |
| **Frontend** | React Query | Server state management and caching |
| **Frontend** | React Hook Form + Zod | Form validation |
| **Backend** | Python 3.11 | Primary programming language |
| **Backend** | FastAPI | Async REST framework with auto-docs |
| **Backend** | SQLAlchemy 2.0 | Async ORM with relationship mapping |
| **Backend** | Alembic | Database migration management |
| **Backend** | Celery | Distributed task queue |
| **Backend** | Pydantic v2 | Data validation and settings |
| **ML/AI** | scikit-learn | ML framework (8 algorithm implementations) |
| **ML/AI** | XGBoost | Gradient boosting (GPU-accelerated) |
| **ML/AI** | LightGBM | Gradient boosting with GOSS |
| **ML/AI** | CatBoost | Gradient boosting with categorical support |
| **ML/AI** | SHAP | Model explainability (4 explainer types) |
| **ML/AI** | Optuna | Bayesian hyperparameter optimization |
| **Geospatial** | rasterio | Geospatial raster I/O and processing |
| **Geospatial** | geopandas | Vector geospatial operations |
| **Geospatial** | shapely | Geometric operations and predicates |
| **Geospatial** | PostGIS | Spatial database with GIST indexing |
| **Satellite** | earthengine-api | Google Earth Engine access |
| **Satellite** | sentinelhub | ESA Copernicus Data Space SDK |
| **Observability** | Prometheus | Time-series metrics collection |
| **Observability** | Grafana | Metrics visualization dashboards |
| **Observability** | Loki | Log aggregation system |
| **Observability** | OpenTelemetry | Distributed tracing |
| **Infrastructure** | Docker | Container runtime |
| **Infrastructure** | Docker Compose | Multi-service orchestration |
| **Infrastructure** | Nginx | Reverse proxy and TLS termination |
| **Infrastructure** | PostgreSQL | Relational database |
| **Infrastructure** | Redis | In-memory cache and message broker |

## Quick Start

### Prerequisites

- Docker 24+ and Docker Compose 2.20+
- Git 2.40+

### 1. Clone

```bash
git clone https://github.com/Nik-coder-10/heatX.git
cd heatX
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys for USGS, Copernicus, Bhuvan (optional for demo)
```

### 3. Deploy

```bash
docker compose up -d
```

This starts all 13 services:

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI backend |
| `frontend` | 80 | React SPA (via Nginx) |
| `celery-worker` | — | Background task processor |
| `celery-beat` | — | Scheduled task scheduler |
| `postgres` | 5432 | PostgreSQL + PostGIS |
| `redis` | 6379 | Cache and message broker |
| `nginx` | 443 | Reverse proxy (TLS) |
| `prometheus` | 9090 | Metrics collection |
| `grafana` | 3000 | Monitoring dashboards |
| `loki` | 3100 | Log aggregation |
| `otel-collector` | 4317 | Trace collection |
| `minio` | 9000 | Object storage (S3-compatible) |
| `tile-server` | 7800 | Raster tile serving (TiTiler) |

### Verify

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Response:
# {"status":"healthy","version":"1.0.0","services":{"postgres":"up","redis":"up","celery":"up"}}

# Open dashboard
open http://localhost:80

# Open API docs
open http://localhost:8000/docs
```

## Example Workflow

```
Satellite Acquisition  ──►  Index Computation  ──►  LST Retrieval
       │                                                    │
       ▼                                                    ▼
  Multi-Sensor Fusion                              UHI Hotspot Detection
       │                                                    │
       └──────────────────┬─────────────────────────────────┘
                          ▼
                  Feature Engineering
                  (17 Geo-Features)
                          │
                          ▼
              ┌─────────────────────┐
              │   ML Model Training  │
              │   (8 Algorithms)     │
              └─────────┬───────────┘
                        ▼
              ┌─────────────────────┐
              │   XAI Explanations   │
              │   (SHAP + Counter-   │
              │    factual Analysis) │
              └─────────┬───────────┘
                        ▼
              ┌─────────────────────┐
              │  Mitigation Recom-  │
              │  mendations (6 Pro- │
              │  files + Knapsack)  │
              └─────────┬───────────┘
                        ▼
              ┌─────────────────────┐
              │  Scenario Simula-   │
              │  tions (7 Templates │
              │  + Monte Carlo)     │
              └─────────┬───────────┘
                        ▼
              ┌─────────────────────┐
              │  Dashboard Visual-  │
              │  ization & Reports  │
              │  (Map + Charts +    │
              │  PDF Export)        │
              └─────────────────────┘
```

## Screenshots

> _Note: Screenshots are placeholders. Replace with actual images once the
> dashboard is running._

### Map View
![Satellite Map View](docs/screenshots/map-view.png)
*Interactive MapLibre GL map showing Landsat 8 imagery with NDVI overlay,
UHI severity zones, and administrative boundaries for Mumbai, India.*

### LST Analysis
![LST Analysis Dashboard](docs/screenshots/lst-analysis.png)
*Land Surface Temperature time-series with split-window algorithm results,
showing temperature distribution histogram and zonal statistics for each ward.*

### ML Training
![ML Training Interface](docs/screenshots/ml-training.png)
*Model training dashboard showing cross-validation results, hyperparameter
search progress, and performance comparison across 8 ML algorithms.*

### SHAP Explainability
![SHAP Explanation](docs/screenshots/shap-explanations.png)
*SHAP beeswarm summary plot showing feature importance rankings, SHAP
dependency plots for NDVI-LST interaction, and waterfall plot for a single
prediction.*

### Mitigation Recommendations
![Mitigation Recommendations](docs/screenshots/mitigation.png)
*Mitigation recommendation dashboard with cost-effectiveness scatter plot,
budget allocation pie chart, and geospatial map of recommended intervention
zones.*

### Scenario Simulation
![Scenario Simulation](docs/screenshots/scenario-simulation.png)
*Monte Carlo simulation results for cool roof adoption scenario, showing
probability distribution of temperature reduction, sensitivity analysis bar
chart, and scenario comparison table.*

## API

The REST API is organized under `/api/v1/`:

| Endpoint Group | Methods | Description |
|---------------|---------|-------------|
| `/api/v1/satellite` | GET, POST | Scene search, acquisition, fusion |
| `/api/v1/indices` | GET, POST | Spectral index computation and retrieval |
| `/api/v1/lst` | GET, POST | LST retrieval and uncertainty |
| `/api/v1/uhi` | GET, POST | UHI detection, zoning, profiling |
| `/api/v1/features` | GET, POST | Feature engineering and retrieval |
| `/api/v1/ml/models` | GET, POST, DELETE | Model registry |
| `/api/v1/ml/training` | POST | Start training jobs |
| `/api/v1/ml/predict` | POST | Run inference |
| `/api/v1/ml/drift` | GET, POST | Drift detection |
| `/api/v1/xai/shap` | POST | SHAP explanations |
| `/api/v1/xai/counterfactual` | POST | Counterfactual analysis |
| `/api/v1/recommendations` | GET, POST | Mitigation recommendations |
| `/api/v1/scenarios` | GET, POST | Scenario simulations |
| `/api/v1/tasks` | GET | Celery task status |
| `/api/v1/auth` | POST | Authentication and tokens |
| `/api/v1/users` | GET, PUT, DELETE | User management |
| `/api/v1/health` | GET | System health check |
| `/api/v1/metrics` | GET | Prometheus metrics |

Full API documentation with interactive testing is available at `/docs` when
the API server is running.

## Folder Structure

```
urbanheat-mitigation-platform/
│
├── app/                                # Backend application
│   ├── api/                            # API layer
│   │   ├── v1/                         # API version 1
│   │   │   ├── endpoints/              # Route handlers
│   │   │   │   ├── satellite.py
│   │   │   │   ├── indices.py
│   │   │   │   ├── lst.py
│   │   │   │   ├── uhi.py
│   │   │   │   ├── features.py
│   │   │   │   ├── ml.py
│   │   │   │   ├── xai.py
│   │   │   │   ├── recommendations.py
│   │   │   │   ├── scenarios.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   └── health.py
│   │   │   └── __init__.py
│   │   ├── deps.py                     # Dependency injection
│   │   └── errors.py                   # Error handlers
│   │
│   ├── core/                           # Core configuration
│   │   ├── config.py                   # pydantic-settings
│   │   ├── security.py                 # Auth & encryption
│   │   ├── cache.py                    # Redis client
│   │   ├── database.py                 # SQLAlchemy engine
│   │   └── logging.py                  # Structured logging
│   │
│   ├── models/                         # SQLAlchemy ORM models
│   │   ├── satellite.py
│   │   ├── indices.py
│   │   ├── lst.py
│   │   ├── uhi.py
│   │   ├── features.py
│   │   ├── model_registry.py
│   │   ├── training.py
│   │   ├── recommendation.py
│   │   ├── scenario.py
│   │   └── user.py
│   │
│   ├── schemas/                        # Pydantic schemas
│   │   ├── satellite.py
│   │   ├── indices.py
│   │   ├── lst.py
│   │   ├── uhi.py
│   │   ├── features.py
│   │   ├── ml.py
│   │   ├── xai.py
│   │   ├── recommendations.py
│   │   ├── scenarios.py
│   │   ├── auth.py
│   │   └── user.py
│   │
│   ├── services/                       # Business logic
│   │   ├── satellite/                  # Acquisition & fusion
│   │   │   ├── landsat.py
│   │   │   ├── sentinel.py
│   │   │   ├── bhuvan.py
│   │   │   └── fusion.py
│   │   ├── indices/                    # Spectral indices
│   │   │   ├── ndvi.py
│   │   │   ├── ndwi.py
│   │   │   ├── ndbi.py
│   │   │   ├── nbri.py
│   │   │   ├── ui.py
│   │   │   └── bsi.py
│   │   ├── lst/                        # Land surface temp
│   │   │   ├── split_window.py
│   │   │   ├── mono_window.py
│   │   │   ├── emissivity.py
│   │   │   └── uncertainty.py
│   │   ├── uhi/                        # UHI analysis
│   │   │   ├── hotspot.py
│   │   │   ├── zoning.py
│   │   │   ├── temporal.py
│   │   │   └── autocorrelation.py
│   │   ├── features/                   # Feature engineering
│   │   │   ├── extractor.py
│   │   │   ├── scaler.py
│   │   │   ├── encoder.py
│   │   │   └── store.py
│   │   ├── ml/                         # Machine learning
│   │   │   ├── trainer.py
│   │   │   ├── models.py               # 8 model wrappers
│   │   │   ├── ensemble.py
│   │   │   ├── search.py               # Hyperparameter search
│   │   │   ├── validation.py           # Cross-validation
│   │   │   ├── drift.py                # Data & concept drift
│   │   │   └── registry.py             # Model versioning
│   │   ├── xai/                        # Explainability
│   │   │   ├── shap_explainer.py
│   │   │   ├── permutation.py
│   │   │   ├── pdp.py
│   │   │   ├── counterfactual.py
│   │   │   └── visualizer.py
│   │   ├── recommendations/            # Mitigation
│   │   │   ├── profiles.py             # 6 profiles
│   │   │   ├── cost_effectiveness.py
│   │   │   ├── knapsack.py
│   │   │   └── pareto.py
│   │   └── scenarios/                  # Simulations
│   │       ├── templates.py            # 7 templates
│   │       ├── monte_carlo.py
│   │       ├── sensitivity.py
│   │       └── comparator.py
│   │
│   ├── tasks/                          # Celery tasks
│   │   ├── acquisition.py
│   │   ├── processing.py
│   │   ├── training.py
│   │   └── simulation.py
│   │
│   ├── main.py                         # FastAPI entry point
│   └── celery_app.py                   # Celery configuration
│
├── frontend/                           # React SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── map/                    # MapLibre GL components
│   │   │   │   ├── MapView.tsx
│   │   │   │   ├── LayerControl.tsx
│   │   │   │   ├── RoiDrawer.tsx
│   │   │   │   └── Inspector.tsx
│   │   │   ├── charts/                 # ECharts components
│   │   │   │   ├── TimeSeriesChart.tsx
│   │   │   │   ├── ShapSummary.tsx
│   │   │   │   ├── CostEffectiveness.tsx
│   │   │   │   └── ScenarioViolin.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── DashboardLayout.tsx
│   │   │   │   ├── MetricCard.tsx
│   │   │   │   └── TaskStatus.tsx
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   └── ProtectedRoute.tsx
│   │   │   └── common/
│   │   │       ├── Loading.tsx
│   │   │       ├── ErrorBoundary.tsx
│   │   │       └── ThemeToggle.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Satellite.tsx
│   │   │   ├── Training.tsx
│   │   │   ├── XaiView.tsx
│   │   │   ├── Recommendations.tsx
│   │   │   ├── Scenarios.tsx
│   │   │   └── Settings.tsx
│   │   ├── hooks/
│   │   │   ├── useSatellite.ts
│   │   │   ├── useTraining.ts
│   │   │   └── useScenario.ts
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── endpoints.ts
│   │   ├── store/
│   │   │   └── appStore.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── tests/                              # Test suite
│   ├── unit/
│   │   ├── test_indices.py
│   │   ├── test_lst.py
│   │   ├── test_uhi.py
│   │   ├── test_features.py
│   │   ├── test_ml.py
│   │   └── test_xai.py
│   ├── integration/
│   │   ├── test_api_satellite.py
│   │   ├── test_api_training.py
│   │   └── test_api_recommendations.py
│   └── e2e/
│       └── test_workflow.py
│
├── scripts/                            # Utility scripts
│   ├── seed_data.py
│   ├── download_demo_data.py
│   └── benchmark.py
│
├── docs/                               # Documentation
│   ├── api/                            # API reference
│   ├── adr/                            # Architecture decisions
│   └── screenshots/
│
├── deploy/                             # Deployment files
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.frontend
│   │   └── nginx/
│   │       └── default.conf
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── grafana/
│   │   ├── dashboards/
│   │   └── datasources/
│   ├── loki/
│   │   └── loki-config.yml
│   └── otel/
│       └── otel-collector-config.yml
│
├── alembic/                            # DB migrations
│   ├── versions/
│   └── env.py
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.test.yml
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## Testing

### Backend

```bash
# Run all tests (unit + integration)
pytest

# With coverage report
pytest --cov=app --cov-report=term-missing --cov-report=html

# Property-based tests
pytest -k "hypothesis" --hypothesis-show-statistics

# Specific domain
pytest tests/unit/test_lst.py -v
```

### Frontend

```bash
cd frontend
npm test                    # All tests
npm test -- --coverage      # With coverage
npm test -- --watch         # Watch mode
```

### End-to-End

```bash
docker compose -f docker-compose.test.yml up -d
pytest tests/e2e/ -v
```

Coverage targets: Backend **85%+**, Frontend **75%+**.

## Deployment

### Docker (Recommended)

```bash
# Production deployment
docker compose -f docker-compose.yml up -d

# Scale workers
docker compose up -d --scale celery-worker=4

# View logs
docker compose logs -f api celery-worker

# Update to latest
docker compose pull
docker compose up -d
```

### Production Checklist

- [ ] Set strong `SECRET_KEY`, `DB_PASSWORD`, `REDIS_PASSWORD` in `.env`
- [ ] Configure TLS certificates (Let's Encrypt via Certbot)
- [ ] Set up S3-compatible object storage (MinIO, AWS S3, etc.)
- [ ] Configure PostgreSQL backup (pg_dump cron, WAL archiving)
- [ ] Set Prometheus alerting rules and Alertmanager
- [ ] Configure Grafana notification channels (Slack, email, PagerDuty)
- [ ] Enable Redis persistence (AOF + RDB)
- [ ] Set rate limits in Nginx
- [ ] Run security scan: `trivy image uhmp-api:latest`
- [ ] Verify health checks for all services

### Cloud Deployment

| Provider | Service | Notes |
|----------|---------|-------|
| AWS | ECS / EKS | Fargate or EC2 launch types, RDS for PostgreSQL |
| GCP | Cloud Run / GKE | Cloud SQL for PostgreSQL, Memorystore for Redis |
| Azure | Container Apps / AKS | Azure Database for PostgreSQL, Cache for Redis |
| Self-hosted | Docker Compose / Swarm | Suitable for on-premise or single-server deployments |

## Scientific References

1. Qin, Z., Karnieli, A., & Berliner, P. (2001). A mono-window algorithm for
   retrieving land surface temperature from Landsat TM data and its application
   to the Israel-Egypt border region. *International Journal of Remote Sensing*,
   22(18), 3719–3746. https://doi.org/10.1080/01431160010006971

2. Jiménez-Muñoz, J. C., & Sobrino, J. A. (2003). A generalized single-channel
   method for retrieving land surface temperature from remote sensing data.
   *Journal of Geophysical Research: Atmospheres*, 108(D22).
   https://doi.org/10.1029/2003JD003480

3. Wan, Z. (2014). New refinements and validation of the collection-6 MODIS
   land-surface temperature/emissivity product. *Remote Sensing of Environment*,
   140, 36–45. https://doi.org/10.1016/j.rse.2013.08.027

4. Oke, T. R. (1982). The energetic basis of the urban heat island. *Quarterly
   Journal of the Royal Meteorological Society*, 108(455), 1–24.
   https://doi.org/10.1002/qj.49710845502

5. Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting
   model predictions. *Advances in Neural Information Processing Systems*, 30.
   https://papers.nips.cc/paper/7062-a-unified-approach-to-interpreting-model-predictions

6. Breiman, L. (2001). Random forests. *Machine Learning*, 45(1), 5–32.
   https://doi.org/10.1023/A:1010933404324

7. Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system.
   *Proceedings of the 22nd ACM SIGKDD*, 785–794.
   https://doi.org/10.1145/2939672.2939785

8. Getis, A., & Ord, J. K. (1992). The analysis of spatial association by use of
   distance statistics. *Geographical Analysis*, 24(3), 189–206.
   https://doi.org/10.1111/j.1538-4632.1992.tb00261.x

## Roadmap

- [x] **v0.1.0 — Pre-alpha** (Jan 2026): Project scaffolding, database models,
      Docker Compose, basic API structure
- [x] **v0.3.0 — Alpha** (Feb 2026): Satellite acquisition (Landsat, Sentinel,
      Bhuvan), spectral indices, LST retrieval, UHI detection, feature extraction
- [x] **v0.5.0 — Beta** (Apr 2026): 8 ML models, ensemble, hyperparameter search,
      cross-validation, drift detection, SHAP XAI, counterfactuals, mitigation
      recommendations, knapsack optimization, scenario simulations, Monte Carlo
- [x] **v1.0.0 — Stable** (Jun 2026): React 19 dashboard, MapLibre GL maps,
      ECharts visualizations, auth/RBAC, PDF reports, production monitoring
      (Prometheus/Grafana/Loki/OpenTelemetry), comprehensive testing, documentation
- [ ] **v1.1.0** (Q3 2026): Real-time satellite data streaming, deep learning
      integration (CNN-LSTM for spatiotemporal prediction), mobile app
- [ ] **v1.2.0** (Q4 2026): Multi-city comparison dashboard, climate projection
      downscaling (CMIP6), community reporting portal
- [ ] **v2.0.0** (Q1 2027): Real-time IoT sensor fusion, dynamic mitigation
      optimization, digital twin integration, global city deployment framework

## Contributing

We welcome contributions of all sizes — from fixing a typo to building a new
feature. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

Quick summary:
1. Fork the repo and create a branch: `feature/your-feature`
2. Follow code style: Black + Ruff (Python), ESLint + Prettier (TypeScript)
3. Write tests for new functionality
4. Use Conventional Commits for commit messages
5. Open a pull request against `main`
6. All checks must pass; maintainers will squash-merge

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for
full text.

## Acknowledgments

This project was built during the **Bharat Antariksh Hackathon** and uses
satellite data from **ISRO** (Bhuvan), **NASA** (Landsat), and **ESA**
(Sentinel-2). We thank the open source community for the foundational
projects listed in [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md).

---

<div align="center">

**Built with :heart: for cooler, more livable cities everywhere.**

[Report Bug](https://github.com/urbanheat/uhmp/issues) •
[Request Feature](https://github.com/urbanheat/uhmp/issues) •
[Documentation](https://urbanheat.github.io/uhmp)

</div>
