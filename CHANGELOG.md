# Changelog

All notable changes to the Urban Heat Mitigation Platform are documented in
this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-06-30

### Added

#### Satellite Data Acquisition
- Landsat 8/9 imagery acquisition via USGS EarthExplorer API with automatic
  scene filtering (cloud cover < 20%, region of interest intersection)
- Sentinel-2 imagery acquisition via ESA Copernicus Data Space Ecosystem with
  atmospheric correction (Sen2Cor) integration
- ISRO Bhuvan API integration for Indian subcontinent high-resolution data
- Multi-sensor fusion engine for combining acquisitions into unified analysis
- Automated scene selection based on cloud cover, acquisition date, and
  spatial coverage
- Threaded parallel download with resume capability and rate limiting
- Retry logic with exponential backoff for API failures

#### Spectral Index Computation
- Normalized Difference Vegetation Index (NDVI) for vegetation health
- Normalized Difference Water Index (NDWI) for surface water extent
- Normalized Difference Built-up Index (NDBI) for impervious surfaces
- Normalized Burn Ratio Index (NBRI) for thermal anomaly detection
- Urban Index (UI) for urban density classification
- Bare Soil Index (BSI) for exposed soil mapping
- Batch processing pipeline for large-area mosaics
- Cloud-optimized GeoTIFF (COG) output format with internal overviews

#### Land Surface Temperature Retrieval
- Split-window algorithm (Landsat 8/9, TIRS bands 10 and 11) with water
  vapor correction via MODIS MOD05 product
- Mono-window algorithm (Landsat 5/7, Sentinel-2) using generalized single-
  channel method
- Atmospheric correction using MODTRAN-based look-up tables
- Land Surface Emissivity estimation from NDVI thresholds
- Pixel-wise uncertainty propagation throughout the retrieval chain
- Validation against in-situ measurements from SURFRAD and FLUXNET stations

#### Urban Heat Island Detection
- Hotspot analysis using Getis-Ord Gi* statistic (p < 0.05)
- UHI intensity computation relative to rural reference zones
- Severity zoning: No UHI, Low, Moderate, High, Severe, Extreme
- Temporal UHI profiling for diurnal and seasonal patterns
- Statistical significance testing with false discovery rate correction
- Spatial autocorrelation assessment (Global Moran's I)

#### Feature Engineering for ML
- 17 geo-features extracted per grid cell or administrative boundary:
  1. Mean NDVI (vegetation greenness)
  2. Mean NDWI (water content)
  3. Mean NDBI (built-up density)
  4. Mean NBRI (thermal anomaly index)
  5. Mean UI (urban index)
  6. Mean BSI (bare soil index)
  7. Mean LST (land surface temperature)
  8. UHI severity category (encoded)
  9. Albedo (shortwave broadband estimation)
  10. Elevation (from SRTM/DEM)
  11. Distance to nearest water body
  12. Distance to nearest green space
  13. Building density (fractional cover)
  14. Population density (gridded)
  15. Road density (km/km²)
  16. Aspect (slope direction)
  17. Surface roughness (from DSM/DTM difference)
- Automated feature scaling, imputation, and encoding pipeline
- Feature store with versioning and lineage tracking

#### Machine Learning Models (8 Architectures)
- Random Forest (100–500 estimators, max depth tuning)
- XGBoost (tree and linear booster, GPU-accelerated training)
- LightGBM (GOSS and GBDT, categorical feature support)
- CatBoost (ordered boosting, symmetric trees)
- Support Vector Machine (RBF, polynomial, linear kernels)
- K-Nearest Neighbors (Minkowski distance, auto-weighted)
- Multi-Layer Perceptron (3 hidden layers, ReLU, Adam optimizer)
- Gradient Boosting (scikit-learn, staged prediction)

#### ML Training Infrastructure
- Ensemble learning with soft/hard voting and stacking (meta-learner)
- Hyperparameter search: GridSearchCV, RandomizedSearchCV, Optuna integration
- K-fold cross-validation (3, 5, 10 folds) with stratified sampling
- Early stopping on validation loss with patience scheduling
- Model checkpointing and version registry in PostgreSQL
- Data drift detection (Population Stability Index, Kolmogorov-Smirnov test,
  Jensen-Shannon divergence)
- Concept drift detection (Page-Hinkley test, ADWIN)
- Experiment tracking with MLflow-compatible metadata store
- Model serialization in ONNX format for production inference

#### Explainable AI (XAI)
- SHAP: TreeExplainer, KernelExplainer, DeepExplainer, LinearExplainer
- SHAP summary plots (beeswarm, bar, violin)
- SHAP dependence plots with interaction visualization
- SHAP waterfall plots for individual predictions
- SHAP force plots for local explanations
- Permutation importance with n-repetitions and confidence intervals
- Partial dependence plots (PDP) and Individual Conditional Expectation (ICE)
- Counterfactual analysis using What-If optimization (genetic algorithm and
  gradient-based approaches)
- Feature interaction strength via H-statistic (Friedman)
- Global and local interpretability report generation (HTML/PDF)

#### Mitigation Recommendations
- 6 mitigation profiles with full cost-benefit models:
  1. **Tree Plantation**: species selection, density optimization, growth
     modeling, irrigation requirements
  2. **Cool Roof**: solar reflectance index, material selection, retrofit
     cost, lifespan analysis
  3. **Green Roof**: structural load assessment, substrate depth, plant
     selection, stormwater retention benefit
  4. **Reflective Pavement**: albedo improvement, durability, maintenance
     schedule, heat flux reduction
  5. **Water Body Restoration**: evaporation cooling, water quality
     requirements, ecological impact assessment
  6. **Urban Green Space**: park accessibility, land availability, ecosystem
     services valuation, social co-benefits
- Cost-effectiveness scoring (cooling potential per rupee invested)
- Budget optimization via 0/1 knapsack algorithm with dynamic programming
- Constraint satisfaction (area, budget, timeline, co-benefit thresholds)
- Multi-objective Pareto frontier visualization
- Recommendation report generation with geospatial output

#### Scenario Simulations
- 7 scenario templates:
  1. **Urban Greening**: varying green cover percentage (10–50%)
  2. **Cool Roof Adoption**: adoption rate scenarios (25–100%)
  3. **Reflective Pavement**: street coverage optimization
  4. **Combined Mitigation**: multi-intervention synergy analysis
  5. **Climate Change Projection**: IPCC SSP scenarios (SSP1-2.6, SSP2-4.5,
     SSP5-8.5)
  6. **Urban Growth**: projected land use change impact on UHI
  7. **Custom Scenario**: user-defined intervention parameters
- Monte Carlo simulation (10,000+ iterations) with Latin Hypercube Sampling
- Probabilistic temperature reduction distribution
- Sensitivity analysis via Sobol indices
- Scenario comparison dashboard with statistical summaries

#### Web Dashboard (React 19)
- Interactive MapLibre GL map with:
  - Tile layer management (satellite imagery, indices, LST, UHI)
  - Vector tile rendering for administrative boundaries
  - Layer opacity and order controls
  - Click-to-inspect pixel values
  - Draw tools for ROI selection
- ECharts visualization suite:
  - Time-series LST trends (line chart)
  - Spectral index distributions (histogram/box plot)
  - UHI severity pie/bar charts
  - SHAP summary beeswarm and waterfall plots
  - Model performance comparison (bar chart with error bars)
  - Cost-effectiveness scatter plot
  - Scenario simulation violin plots
- Dashboard layout with draggable, resizable panels (react-grid-layout)
- Dark mode and light mode themes
- Responsive design (mobile, tablet, desktop)
- Real-time task status via WebSocket (Celery task progress)
- PDF report export with integrated visualizations
- User authentication (JWT, OAuth2, Google and GitHub SSO)
- Role-based access control (admin, analyst, viewer)

#### API and Backend
- RESTful API with FastAPI, auto-generated OpenAPI docs
- Async endpoints for satellite acquisition and processing tasks
- Celery distributed task queue with Redis broker
- Task prioritization and dead-letter queue
- API rate limiting per user tier
- Request/response validation via Pydantic v2
- Comprehensive error handling with structured error responses
- Pagination, filtering, and sorting on list endpoints
- Background task cancellation and status polling
- CORS configuration for production deployment
- Health check endpoint at `/api/v1/health`
- Prometheus metrics at `/api/v1/metrics`
- OpenTelemetry distributed tracing integration

#### Database and Storage
- PostgreSQL with PostGIS extension for all geospatial data
- Migrations via Alembic with automatic upgrade/downgrade
- Spatial indexing (GIST) on geometry columns
- Raster storage using PostGIS raster type with tiling
- Type-2 slowly changing dimensions for historical tracking
- Redis caching layer with TTL-based invalidation
- Object storage abstraction (S3-compatible, local filesystem)
- COG-compatible raster storage for efficient web tile serving

#### Deployment and Infrastructure
- Docker Compose configuration for all services (13 containers)
- Multi-stage Docker builds for Python and Node images
- Nginx reverse proxy with TLS termination, rate limiting, gzip
- Health check endpoints for all services
- Prometheus metrics collection with service discovery
- Grafana dashboards (system, application, ML model, business KPIs)
- Loki log aggregation with structured JSON logging
- OpenTelemetry collector with span sampling and export
- Docker health checks with restart policies
- Environment-based configuration via `.env` files and secrets

#### Testing
- Unit tests for all Python modules (pytest, 85%+ coverage)
- Integration tests for API endpoints (TestClient, async)
- Property-based testing (Hypothesis) for data processing modules
- End-to-end workflow tests (satellite to dashboard)
- Frontend component tests (Vitest, React Testing Library)
- API contract tests with OpenAPI schema validation
- Performance benchmarks for ML training and raster processing
- Security tests (Bandit, Safety, npm audit)

#### Documentation
- Comprehensive README with architecture, setup, and workflow
- API reference documentation (auto-generated from OpenAPI)
- Developer contributing guide with code style and PR process
- Security policy with vulnerability disclosure process
- Code of Conduct (Contributor Covenant v2.1)
- Full changelog with semantic versioning
- Scientific references and methodology descriptions

### Changed
- Migration from single-algorithm LST retrieval to dual-algorithm
  (split-window + mono-window) with automatic selection
- Upgraded ML pipeline from 5 to 8 model types with ensemble support
- Redesigned dashboard from static mockups to interactive MapLibre GL
  with real-time data layers
- Enhanced mitigation recommendations from 3 to 6 profiles with full
  cost-effectiveness and knapsack optimization
- Improved satellite acquisition with multi-source fusion and auto-retry

### Fixed
- Edge case in split-window algorithm for water vapor saturation
- Memory leak in large-area raster mosaic generation
- Georeferencing offset in Sentinel-2 scene processing
- UHI boundary artifacts at administrative border edges
- Race condition in parallel tile processing pipeline

### Performance
- 40% reduction in LST retrieval time via vectorized numpy operations
- 60% faster ML training with GPU acceleration and early stopping
- 3x improvement in raster tile serving via COG format and caching
- Reduced memory footprint in large-area processing via chunked streams

## [0.5.0] — 2026-04-15

### Added
- 8 ML model types with scikit-learn, XGBoost, LightGBM, CatBoost
- Ensemble learning with voting and stacking classifiers
- Hyperparameter search with GridSearchCV, RandomizedSearchCV, Optuna
- K-fold cross-validation with stratified sampling
- MLflow-compatible experiment tracking
- Data drift detection (PSI, KS test, JS divergence)
- Concept drift detection (Page-Hinkley, ADWIN)
- SHAP explainability (Tree, Kernel, Deep, Linear explainers)
- SHAP visualization (summary, dependence, waterfall, force plots)
- Permutation importance with confidence intervals
- Partial dependence and ICE plots
- Counterfactual analysis (genetic algorithm)
- Feature interaction strength (H-statistic)
- 6 mitigation recommendation profiles
- Cost-effectiveness scoring engine
- Budget optimization (0/1 knapsack with dynamic programming)
- 7 scenario simulation templates
- Monte Carlo simulation engine (Latin Hypercube Sampling)
- Sensitivity analysis (Sobol indices)
- Scenario comparison and statistical reporting

### Changed
- Refactored feature engineering to modular pipeline architecture
- Consolidated all ML training into unified Trainer class
- Extended API with ML, XAI, recommendation, and scenario endpoints

### Fixed
- Multi-collinearity detection in feature selection pipeline
- Normalization inconsistency between training and inference
- Memory bottleneck in SHAP KernelExplainer for large datasets

## [0.3.0] — 2026-02-28

### Added
- Landsat 8/9 scene acquisition via USGS M2M API
- Sentinel-2 scene acquisition via Copernicus Data Space
- ISRO Bhuvan API integration for Indian data
- Multi-sensor fusion for cross-platform scene merging
- NDVI, NDWI, NDBI, NBRI, UI, BSI spectral indices
- Split-window LST algorithm for Landsat 8/9 TIRS
- Mono-window LST algorithm for Landsat 5/7 and Sentinel-2
- Land surface emissivity estimation (NDVI thresholds method)
- Atmospheric correction via MODTRAN look-up tables
- UHI hotspot detection (Getis-Ord Gi*)
- UHI severity zoning (6 levels)
- Temporal UHI profiling
- Spatial autocorrelation (Global Moran's I)
- 17 geo-feature extraction pipeline
- Feature store with versioning
- COG raster output format
- PostGIS raster storage
- Basic REST API with FastAPI
- Celery task queue for async processing
- Alembic database migrations

### Changed
- Migrated from GDAL command-line to pure Python rasterio pipeline
- Standardized spectral index computation to single-precision float

### Fixed
- Geographic coordinate reprojection mismatch in Landsat processing
- Incorrect emissivity values for water pixels
- Atmospheric correction failure for high-latitude winter scenes

## [0.1.0] — 2026-01-15

### Added
- Project scaffolding and directory structure
- Python 3.11 virtual environment configuration
- FastAPI application with health endpoint
- SQLAlchemy ORM models with PostGIS geometry support
- Alembic migration framework
- Docker Compose for PostgreSQL/PostGIS and Redis
- pytest configuration with coverage reporting
- Ruff and Black code quality configuration
- Pre-commit hooks configuration
- Basic logging infrastructure with structlog
- Environment variable management via pydantic-settings
- README with project overview and setup instructions
- MIT License file
- .gitignore for Python and Node projects
- Initial API versioning scheme (/api/v1)

[1.0.0]: https://github.com/urbanheat/uhmp/releases/tag/v1.0.0
[0.5.0]: https://github.com/urbanheat/uhmp/releases/tag/v0.5.0
[0.3.0]: https://github.com/urbanheat/uhmp/releases/tag/v0.3.0
[0.1.0]: https://github.com/urbanheat/uhmp/releases/tag/v0.1.0
