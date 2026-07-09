# Urban Heat Mitigation Platform - Design Document

## 1. High-level Architecture

### Overview
The platform follows a microservices architecture with clear separation of concerns. It consists of the following layers:
- Client Layer (Web/Mobile)
- API Gateway
- Service Layer (Backend Services)
- Data Layer (Databases, Storage)
- AI/ML Layer
- GIS Layer
- Infrastructure (CI/CD, Monitoring, Logging)

### Core Services

#### 1.1 API Gateway
- **Technology**: NGINX Plus or Kong
- **Responsibilities**:
  - Request routing
  - SSL termination
  - Rate limiting
  - Authentication (JWT validation)
  - Request/response logging
  - Circuit breaker pattern

#### 1.2 Authentication Service
- **Technology**: Node.js with Express or Python FastAPI
- **Responsibilities**:
  - User registration/login
  - JWT token issuance/validation
  - OAuth2 integration (Google, ISRO SSO)
  - Password hashing (bcrypt)
  - Session management
  - Role-based access control (RBAC)

#### 1.3 User Service
- **Technology**: Python FastAPI
- **Responsibilities**:
  - User profile management
  - Preferences storage
  - Notification settings
  - Role management
  - GDPR compliance (data export/deletion)

#### 1.4 Project Service
- **Technology**: Python FastAPI
- **Responsibilities**:
  - CRUD operations for projects
  - Project metadata (name, description, location, timeline)
  - Collaboration features (sharing, permissions)
  - Version control for project configurations

#### 1.5 Satellite Service
- **Technology**: Python with GDAL/Rasterio
- **Responsibilities**:
  - Satellite imagery acquisition (Landsat, Sentinel, ISRO resources)
  - Metadata management
  - Cloud masking
  - Georeferencing
  - Temporal alignment

#### 1.6 GIS Service
- **Technology**: Python with GeoPandas, Shapely, PostGIS
- **Responsibilities**:
  - Vector/raster data processing
  - Spatial indexing
  - Coordinate transformations
  - Buffer analysis
  - Zone delineation (urban/rural)
  - Heat island boundary detection

#### 1.7 Heat Detection Service
- **Technology**: Python with Scikit-learn, TensorFlow/PyTorch
- **Responsibilities**:
  - Urban Heat Island (UHI) index calculation
  - Land Surface Temperature (LST) derivation
  - Anomaly detection
  - Trend analysis
  - Change detection

#### 1.8 ML Training Service
- **Technology**: Python with MLflow, Kubeflow Pipelines
- **Responsibilities**:
  - Model training orchestration
  - Hyperparameter tuning
  - Experiment tracking
  - Model versioning
  - Automated retraining triggers

#### 1.9 Inference Service
- **Technology**: Python FastAPI with TensorFlow Serving/TorchServe
- **Responsibilities**:
  - Real-time predictions
  - Batch processing
  - Model A/B testing
  - Input validation
  - Output post-processing

#### 1.10 Recommendation Engine
- **Technology**: Python with Neo4j (for graph-based recs) or collaborative filtering
- **Responsibilities**:
  - Mitigation strategy suggestions
  - Cost-benefit analysis
  - Prioritization of interventions
  - What-if scenario simulation
  - Policy recommendation generation

#### 1.11 Report Service
- **Technology**: Python with WeasyPrint or ReportLab
- **Responsibilities**:
  - PDF report generation
  - Chart/table embedding
  - Template management
  - Scheduled report delivery
  - Multi-language support

#### 1.12 Notification Service
- **Technology**: Python with Celery/RabbitMQ
- **Responsibilities**:
  - Email notifications (SMTP/SendGrid)
  - SMS (Twilio)
  - In-app notifications
  - Alert thresholds
  - Emergency alerting

#### 1.13 Admin Dashboard Service
- **Technology**: React/Kubernetes Dashboard
- **Responsibilities**:
  - System health monitoring
  - User management
  - Resource utilization
  - Audit log viewing
  - Configuration management
  - Service status overview

### Data Flow
1. User uploads satellite data or specifies AOI via API Gateway
2. Request routed to appropriate service (Project, Satellite)
3. Satellite Service fetches/processes imagery
4. GIS Service performs spatial analysis
5. Heat Detection Service computes UHI metrics
6. ML Models generate predictions/recommendations
7. Results stored in database/cache
8. User accesses results via frontend or receives reports/notifications

### External Integrations
- ISRO Bhuvan API for satellite data
- NASA Earthdata for supplementary imagery
- OpenWeatherMap for weather data
- Google Maps API for visualization
- PostgreSQL with PostGIS extension
- Redis for caching
- RabbitMQ/Kafka for message queuing
- Prometheus/Grafana for monitoring
- ELK stack for logging
- Docker/Kubernetes for orchestration

## 2. Folder Structure

```
urban-heat-platform/
├── docs/                  # Documentation
│   ├── architecture.md
│   ├── api-specs.md
│   ├── database-schema.md
│   └── deployment-guide.md
├── infra/                 # Infrastructure as Code
│   ├── terraform/         # Terraform configs
│   ├── kubernetes/        # K8s manifests
│   ├── docker-compose.yml # Local dev
│   └── ci-cd/             # GitHub Actions/Jenkins
├── services/              # Microservices
│   ├── api-gateway/
│   ├── auth-service/
│   ├── user-service/
│   ├── project-service/
│   ├── satellite-service/
│   ├── gis-service/
│   ├── heat-detection-service/
│   ├── ml-training-service/
│   ├── inference-service/
│   ├── recommendation-service/
│   ├── report-service/
│   ├── notification-service/
│   └── admin-dashboard-service/
├── shared/                # Shared libraries/components
│   ├── utils/             # Common utilities
│   ├── models/            # Shared data models
│   ├── exceptions/        # Custom exceptions
│   └── constants/         # Application constants
├── frontend/              # Web application
│   ├── public/            # Static assets
│   ├── src/               # React source code
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── context/
│   │   ├── services/      # API service layer
│   │   ├── store/         # State management (Redux/Zustand)
│   │   ├── utils/
│   │   └── styles/
│   ├── tests/             # Frontend tests
│   └── config/            # Webpack/Vite config
├── mobile/                # Mobile application (React Native/Flutter)
│   ├── ios/
│   ├── android/
│   └── shared/
├── ml/                    # Machine learning assets
│   ├── datasets/          # Training/validation datasets
│   ├── models/            # Trained model artifacts
│   ├── notebooks/         # Experimental notebooks
│   ├── pipelines/         # Training pipeline definitions
│   └── evaluation/        # Model evaluation scripts
├── gis/                   # GIS-specific assets
│   ├── projections/       # Coordinate system definitions
│   ├── templates/         # Map templates
│   └── scripts/           # Preprocessing scripts
├── tests/                 # Integration and end-to-end tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/               # Utility scripts
│   ├── deploy.sh
│   ├── backup.sh
│   └── migrate.sh
├── Dockerfile             # Base Dockerfile (if monolithic approach)
├── docker-compose.yml     # Local development
├── .gitignore
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── SECURITY.md
```

### Rationale
- **Separation of Concerns**: Each service is isolated with clear boundaries
- **Scalability**: Services can be scaled independently based on load
- **Maintainability**: Shared libraries reduce duplication
- **DevOps Friendly**: Infrastructure as code enables reproducible environments
- **Technology Agnostic**: Services can use different tech stacks as needed

## 3. API Design

### General Principles
- RESTful principles where appropriate
- JSON as primary exchange format
- Versioning via URL prefix (`/api/v1/`)
- Standard HTTP status codes
- Pagination for list endpoints (`limit`, `offset`)
- Filtering and sorting capabilities
- Consistent error response format
- HATEOAS for discoverability (optional)

### Common Response Formats

#### Success Response
```json
{
  "success": true,
  "data": {},
  "meta": {
    "timestamp": "2026-06-30T10:00:00Z",
    "request_id": "abc123"
  }
}
```

#### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}
```

### Authentication
- All endpoints require `Authorization: Bearer <jwt_token>` header
- Exceptions: `/auth/register`, `/auth/login`, `/health`

### Endpoint Categories

#### Auth Service (`/api/v1/auth`)
- `POST /register` - User registration
- `POST /login` - User login
- `POST /refresh` - Token refresh
- `POST /logout` - Token invalidation
- `GET /profile` - Get current user profile
- `PUT /profile` - Update user profile

#### User Service (`/api/v1/users`)
- `GET /` - List users (admin only)
- `GET /{id}` - Get user by ID
- `PUT /{id}` - Update user (admin/self)
- `DELETE /{id}` - Deactivate user (admin)
- `GET /{id}/projects` - Get user's projects

#### Project Service (`/api/v1/projects`)
- `GET /` - List projects (with filters: user_id, status, date)
- `POST /` - Create new project
- `GET /{id}` - Get project details
- `PUT /{id}` - Update project
- `DELETE /{id}` - Archive project
- `GET /{id}/collaborators` - List project collaborators
- `POST /{id}/collaborators` - Add collaborator
- `DELETE /{id}/collaborators/{user_id}` - Remove collaborator
- `GET /{id}/assets` - List project assets (images, reports)

#### Satellite Service (`/api/v1/satellite`)
- `GET /sources` - List available satellite sources
- `POST /search` - Search for imagery (by date, location, cloud cover)
- `POST /acquire` - Trigger imagery acquisition
- `GET /{image_id}/metadata` - Get image metadata
- `GET /{image_id}/download` - Download processed image (signed URL)
- `POST /{image_id}/process` - Initiate preprocessing (cloud masking, etc.)

#### GIS Service (`/api/v1/gis`)
- `POST /geocode` - Convert address to coordinates
- `POST /reverse-geocode` - Convert coordinates to address
- `POST /buffer` - Create buffer around geometry
- `POST /intersect` - Find intersecting geometries
- `POST /area` - Calculate area of geometry
- `POST /transform` - Transform coordinate reference system
- `POST /validate` - Validate geometry

#### Heat Detection Service (`/api/v1/heat`)
- `POST /detect` - Detect urban heat islands from image
- `GET /{project_id}/uhi-index` - Get UHI index time series
- `GET /{project_id}/hotspots` - Get detected hotspots
- `POST /{project_id}/analyze-trends` - Analyze temperature trends
- `GET /{project_id}/comparison` - Compare with baseline/neighboring areas

#### ML Service (`/api/v1/ml`)
- `GET /models` - List available models
- `GET /models/{model_id}/info` - Get model metadata
- `POST /predict` - Run inference on input data
- `POST /batch-predict` - Run batch inference
- `POST /train` - Initiate model training (async)
- `GET /train/{job_id}/status` - Get training job status
- `POST /evaluate` - Evaluate model performance

#### Recommendation Service (`/api/v1/recommendations`)
- `POST /generate` - Generate mitigation recommendations
- `GET /{project_id}/recommendations` - Get stored recommendations
- `POST /{project_id}/simulate` - Simulate intervention impact
- `GET /{project_id}/cost-benefit` - Get cost-benefit analysis

#### Report Service (`/api/v1/reports`)
- `POST /generate` - Generate report (PDF/HTML)
- `GET /{report_id}/download` - Download report
- `GET /{project_id}/reports` - List project reports
- `POST /schedule` - Schedule recurring report generation

#### Notification Service (`/api/v1/notifications`)
- `GET /` - List user notifications
- `PUT /{id}/read` - Mark notification as read
- `DELETE /{id}` - Delete notification
- `POST /preferences` - Set notification preferences

#### Admin Service (`/api/v1/admin`)
- `GET /health` - System health check
- `GET /metrics` - System metrics (Prometheus format)
- `GET /logs` - Retrieve system logs (with filters)
- `GET /users` - List all users
- `PUT /users/{id}/role` - Update user role
- `GET /services` - List service statuses
- `POST /maintenance` - Toggle maintenance mode

### WebSocket Endpoints (for real-time updates)
- `ws://api.urbanheat.isro.gov.in/ws/projects/{project_id}` - Project updates
- `ws://api.urbanheat.isro.gov.in/ws/notifications` - User notifications
- `ws://api.urbanheat.isro.gov.in/ws/ml-training/{job_id}` - Training progress

## 4. Database Design

### Technology Choice
- **Primary**: PostgreSQL 15+ with PostGIS 3.3+ extension
- **Caching**: Redis 7+
- **Object Storage**: Amazon S3/MininIO (for satellite images, reports)
- **Graph Database**: Neo4j (for recommendation relationships) - optional

### Database Schema

#### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone_number VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    role VARCHAR(50) DEFAULT 'user', -- admin, user, scientist
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    preferences JSONB DEFAULT '{}'
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

#### Projects Table
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, completed, archived
    center_point GEOGRAPHY(POINT, 4326),
    boundary GEOGRAPHY(POLYGON, 4326),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_location ON projects USING GIST (center_point);
CREATE INDEX idx_projects_boundary ON projects USING GIST (boundary);
```

#### Cities Table (for reference data)
```sql
CREATE TABLE cities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    population INTEGER,
    center_point GEOGRAPHY(POINT, 4326),
    boundary GEOGRAPHY(MULTIPOLYGON, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cities_name ON cities(name);
CREATE INDEX idx_cities_location ON cities USING GIST (center_point);
CREATE INDEX idx_cities_boundary ON cities USING GIST (boundary);
```

#### SatelliteImages Table
```sql
CREATE TABLE satellite_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL, -- LANDSAT, SENTINEL, RESOURCESAT
    acquisition_date TIMESTAMP WITH TIME ZONE NOT NULL,
    cloud_cover_percentage DECIMAL(5,2),
    sun_elevation DECIMAL(5,2),
    file_path VARCHAR(500), -- Path in object storage
    thumbnail_path VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_satellite_images_project_id ON satellite_images(project_id);
CREATE INDEX idx_satellite_images_acquisition_date ON satellite_images(acquisition_date);
CREATE INDEX idx_satellite_images_source ON satellite_images(source);
CREATE INDEX idx_satellite_images_cloud_cover ON satellite_images(cloud_cover_percentage);
```

#### HeatMaps Table
```sql
CREATE TABLE heat_maps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    satellite_image_id UUID REFERENCES satellite_images(id) ON DELETE SET NULL,
    map_type VARCHAR(50) NOT NULL, -- LST, UHI_INDEX, ANOMALY
    raster_path VARCHAR(500), -- Path to GeoTIFF in object storage
    min_value DECIMAL(10,3),
    max_value DECIMAL(10,3),
    mean_value DECIMAL(10,3),
    std_dev DECIMAL(10,3),
    unit VARCHAR(20), -- Celsius, Kelvin
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_heat_maps_project_id ON heat_maps(project_id);
CREATE INDEX idx_heat_maps_satellite_image_id ON heat_maps(satellite_image_id);
CREATE INDEX idx_heat_maps_map_type ON heat_maps(map_type);
```

#### Predictions Table
```sql
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    model_version VARCHAR(50) NOT NULL,
    prediction_type VARCHAR(50) NOT NULL, -- TEMPERATURE_FORECAST, UHI_PROJECTION
    horizon_days INTEGER NOT NULL, -- 1, 3, 7, 14, 30
    raster_path VARCHAR(500), -- Path to prediction raster
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_predictions_project_id ON predictions(project_id);
CREATE INDEX idx_predictions_model_version ON predictions(model_version);
CREATE INDEX idx_predictions_horizon_days ON predictions(horizon_days);
CREATE INDEX idx_predictions_valid_period ON predictions(valid_from, valid_until);
```

#### Recommendations Table
```sql
CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100), -- GREEN_INFRASTRUCTURE, COOL_ROOFS, URBAN_FORESTRY
    priority_score DECIMAL(3,2), -- 0.0 to 1.0
    estimated_cost DECIMAL(10,2),
    estimated_impact DECIMAL(3,2), -- Temperature reduction in Celsius
    implementation_time_months INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_recommendations_project_id ON recommendations(project_id);
CREATE INDEX idx_recommendations_category ON recommendations(category);
CREATE INDEX idx_recommendations_priority_score ON recommendations(priority_score);
```

#### SimulationResults Table
```sql
CREATE TABLE simulation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    recommendation_id UUID REFERENCES recommendations(id) ON DELETE SET NULL,
    scenario_name VARCHAR(100) NOT NULL,
    temperature_reduction_map_path VARCHAR(500),
    avg_temperature_reduction DECIMAL(5,2),
    max_temperature_reduction DECIMAL(5,2),
    affected_area_sqkm DECIMAL(10,2),
    cost_benefit_ratio DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_simulation_results_project_id ON simulation_results(project_id);
CREATE INDEX idx_simulation_results_recommendation_id ON simulation_results(recommendation_id);
```

#### Reports Table
```sql
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    report_type VARCHAR(50), -- SUMMARY, DETAILED, EXECUTIVE
    format VARCHAR(20), -- PDF, HTML
    file_path VARCHAR(500), -- Path in object storage
    generated_by UUID REFERENCES users(id),
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_reports_project_id ON reports(project_id);
CREATE INDEX idx_reports_generated_at ON reports(generated_at);
CREATE INDEX idx_reports_format ON reports(format);
```

#### AuditLogs Table
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- CREATE, UPDATE, DELETE, LOGIN, etc.
    entity_type VARCHAR(50), -- USER, PROJECT, SATELLITE_IMAGE
    entity_id UUID,
    changes JSONB, -- Store before/after states
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
```

### Relationships
- One-to-Many: User → Projects
- One-to-Many: Project → SatelliteImages
- One-to-Many: Project → HeatMaps
- One-to-Many: Project → Predictions
- One-to-Many: Project → Recommendations
- One-to-Many: Project → SimulationResults
- One-to-Many: Project → Reports
- One-to-Many: User → AuditLogs (where user performed action)
- Many-to-Many: Project ← Collaborators → User (handled via separate table not shown for brevity)

### Indexing Strategy
- Primary keys: UUID with default index
- Foreign keys: Indexed for JOIN performance
- Spatial queries
- Frequently filtered columns: status, type, dates
- Composite indexes for common query patterns
- GIST indexes for geometric/geographic queries
- Partial indexes for soft-deleted records (if implemented)

## 5. ML Pipeline

### Overview
The ML pipeline follows MLOps best practices with continuous training, validation, and deployment.

### Components

#### 5.1 Dataset Management
- **Sources**:
  - Historical satellite imagery (Landsat 8/9, Sentinel-2)
  - Ground truth temperature data (weather stations, ISRO meteorological data)
  - Land use/land cover maps
  - Urban morphology data (building height, density)
  - Socioeconomic data (for vulnerability analysis)
- **Storage**:
  - Raw data: Object storage (S3-compatible)
  - Processed features: Feature store (Feast or custom PostgreSQL schemas)
  - Versioned datasets: DVC or MLflow datasets
- **Preprocessing**:
  - Cloud masking (Fmask, Sen2Cor)
  - Atmospheric correction
  - Geometric registration
  - Temporal compositing (monthly/seasonal averages)
  - Feature extraction (NDVI, NDBI, albedo)
  - Patch-based sampling for CNN training

#### 5.2 Model Training
- **Architectures**:
  - CNN/U-Net for pixel-wise temperature prediction
  - LSTM/GRU for temporal forecasting
  - Graph Neural Networks for spatial dependencies
  - Ensemble methods (Random Forest, XGBoost) for interpretability
- **Training Framework**:
  - PyTorch Lightning or TensorFlow Keras
  - Distributed training (Horovod, TF Distribution Strategy)
  - Experiment tracking: MLflow
  - Hyperparameter optimization: Optuna or Ray Tune
- **Validation**:
  - Spatial cross-validation (to avoid data leakage)
  - Temporal hold-out validation
  - Metrics: RMSE, MAE, R², bias
  - Uncertainty quantification (Monte Carlo dropout, ensembles)
- **Compute**:
  - GPU-enabled Kubernetes nodes
  - Spot instances for cost optimization
  - Job scheduling: Kubeflow Pipelines or Argo Workflows

#### 5.3 Model Registry
- **Storage**: MLflow Model Registry or custom PostgreSQL-backed registry
- **Versioning**: Semantic versioning (MAJOR.MINOR.PATCH)
- **Stages**: None → Staging → Production → Archived
- **Metadata**:
  - Training dataset version
  - Hyperparameters
  - Evaluation metrics
  - Hardware/software environment
  - Input/output schema
- **Governance**:
  - Model approval workflow
  - Bias/fairness checks
  - Performance drift monitoring

#### 5.4 Inference Pipeline
- **Batch Inference**:
  - Triggered by new satellite imagery acquisition
  - Processes full scenes or project AOIs
  - Results stored as CloudOptimized GeoTIFFs
  - Metadata stored in PostgreSQL
- **Real-time Inference**:
  - REST/gRPC endpoint for on-demand predictions
  - Model serving: TensorFlow Serving, TorchServe, or BentoML
  - Autoscaling based on request volume
  - Latency SLA: <2 seconds for 256x256 pixel patches
- **Caching**:
  - Redis cache for frequent queries (city-level summaries)
  - CDN for static map tiles
  - In-memory cache for recent predictions

#### 5.5 Monitoring & Maintenance
- **Data Drift Detection**:
  - Statistical tests (KS test, PSI) on input features
  - Alert when drift exceeds threshold
- **Concept Drift Detection**:
  - Monitor prediction accuracy against ground truth (when available)
  - Track performance degradation over time
- **Model Retraining**:
  - Triggered by: data drift, concept drift, time-based (monthly)
  - Automated retraining pipeline
  - A/B testing of new models before promotion
- **Resource Monitoring**:
  - GPU utilization, memory usage
  - Inference latency, throughput
  - Error rates and failure patterns

### Example Workflow
1. New Landsat 8 image acquired for project AOI
2. Preprocessing: cloud masking, reprojection, NDVI calculation
3. Feature extraction: extract patches around urban areas
4. Batch inference: run UNet model to predict LST
5. Post-processing: apply scale factors, create confidence bands
6. Store results in object storage, update PostgreSQL with metadata
7. Trigger recommendation engine if significant UHI detected
8. Generate alert if temperature exceeds threshold

## 6. GIS Pipeline

### Overview
Handles all geographic data processing, from raw satellite imagery to actionable spatial insights.

### Components

#### 6.1 Satellite Download
- **Sources**:
  - USGS EarthExplorer (Landsat)
  - ESA Copernicus Open Access Hub (Sentinel)
  - ISRO Bhuvan (Resourcesat, Cartosat)
  - NOAA CLASS (GOES, AVHRR)
- **Automation**:
  - Scripts using respective APIs (boto3, sentinelsat, pyros)
  - Schedule: daily checks for new acquisitions
  - Filtering: by AOI, date range, cloud cover (<30%), sun angle
- **Storage**: 
  - Raw: Object storage with lifecycle policies (GLACIER after 30 days)
  - Metadata: PostgreSQL with raster-specific columns

#### 6.2 Preprocessing
- **Radiometric Correction**:
  - Convert DN to TOA reflectance/radiance
  - Atmospheric correction (6S, MODTRAN, or FLAASH)
- **Geometric Correction**:
  - Orthorectification using DEM (SRTM, ASTER)
  - Ground control point refinement
- **Cloud Masking**:
  - Landsat: Fmask, CFMask
  - Sentinel: Sen2Cor, QA60 band
  - Tropical: custom ML-based cloud detector
- **Temporal Processing**:
  - Create median/monthly composites
  - Gap filling (DINEOF, STARFM)
  - Anomaly detection (CCDC, LandTrendr)

#### 6.3 Raster Processing
- **Index Calculation**:
  - NDVI = (NIR - Red) / (NIR + Red)
  - NDBI = (SWIR - NIR) / (SWIR + NIR)
  - Albedo from broadband conversion
  - Emissivity estimation from NDVI
- **Temperature Retrieval**:
  - Single Channel Algorithm (SCA) for TIRS
  - Split Window Algorithm (SWA) for ASTER
  - Physics-based models for MODIS/VIIRS
  - Machine learning approaches (RF, CNN) for fusion
- **Resampling & Reprojection**:
  - Uniform grid (30m for Landsat, 10m for Sentinel-2)
  - Common projection: UTM zone based on AOI centroid
  - Resampling method: cubic spline for temperature, nearest for classification
- **Mosaicking**:
  - Combine multiple scenes for large AOIs
  - Handle overlap areas (average, select latest)

#### 6.4 Heat Detection
- **Urban Heat Island (UHI) Intensity**:
  - ΔT = T_urban - T_rural (reference from surrounding non-urban)
  - Urban/rural classification using Impervious Surface Area (ISA)
  - Local Climate Zone (LCZ) based classification
- **Surface Urban Heat Island (SUHI)**:
  - Direct LST comparison urban vs. non-urban buffers
  - Spatial statistics: Moran's I, Getis-Ord Gi*
- **Canopy Layer Heat Island**:
  - Requires air temperature data (from weather stations or models)
  - Regression between LST and air temperature
- **Trend Analysis**:
  - Mann-Kendall test for monotonic trends
  - Sen's slope estimator
  - Breakpoint detection (BFAST, ECMWF)

#### 6.5 Visualization
- **Static Maps**:
  - Generated via QGIS/ArcPy or Python (matplotlib, cartopy)
  - Color ramps: perceptually uniform (viridis, plasma)
  - Scale bars, north arrows, legends
  - Export: high-resolution PNG/TIFF for reports
- **Interactive Maps**:
  - Web: Leaflet/Mapbox GL JS with WMS/WMTS from GeoServer
  - Mobile: Mapbox SDK or Google Maps SDK
  - Layers: base imagery, heat maps, city boundaries, recommendations
  - Features: zoom, pan, measure, identify, swipe tool
  - Performance: vector tiles for large datasets, raster tiles for imagery
- **3D Visualization**:
  - Optional: CesiumJS for building height integrated analysis
  - Requires DSM/DTM data

#### 6.6 Recommendation Integration
- **Spatial Allocation**:
  - Overlay recommendations on heat map hotspots
  - Constraint-aware placement (zoning, land ownership, infrastructure)
  - Multi-criteria decision analysis (MCDA) for site suitability
- **Impact Modeling**:
  - Cool roof implementation: albedo increase → temperature decrease
  - Urban forestry: evapotranspiration cooling + shade
  - Green infrastructure: infiltration reduction + evaporative cooling
  - Use microclimate models (ENVI-met, SOLWEIG) for detailed analysis
- **Output**:
  - Recommendation suitability maps
  - Before/after simulation visualizations
  - Intervention prioritization rankings

### Tools & Libraries
- **Core**: GDAL, PROJ, GeoPandas, Shapely, Rasterio, Fiona
- **Processing**: Orfeo Toolbox, Sentinel Hub Python, earthpy
- **Analysis**: PySAL, scikit-spatial, statsmodels
- **Visualization**: matplotlib, seaborn, plotly, folium
- **Web Mapping**: GeoServer, TileServer GL, Mapbox
- **Database**: PostGIS (ST_Clip, ST_MapAlgebra, ST_Intersection, ST_ValueCount)

## 7. Security

### 7.1 Authentication & Authorization
- **JWT Implementation**:
  - Access tokens: 15-minute expiry
  - Refresh tokens: 7-day expiry, stored HTTP-only cookie
  - Signature: HS256 with secret rotated monthly
  - Claims: user_id, roles, permissions, project_access
- **Password Security**:
  - bcrypt with cost factor 12
  - Password history (last 5 passwords)
  - Lockout after 5 failed attempts (30-minute delay)
  - Password reset via email token (1-hour expiry)
- **Role-Based Access Control (RBAC)**:
  - Roles: admin, project_manager, scientist, viewer
  - Permissions granularity: create, read, update, delete, export
  - Project-level overrides for collaboration
- **OAuth2/OpenID Connect**:
  - Integration with ISRO SSO, Google Workspace
  - Just-in-time user provisioning
  - Token introspection for third-party access

### 7.2 Network Security
- **API Gateway**:
  - WAF rules (OWASP Top 10 protection)
  - DDoS protection (rate limiting, burst control)
  - Geo-blocking for restricted regions
  - Mutual TLS for service-to-service communication
- **Service Mesh** (Istio/Linkerd):
  - mTLS encryption between services
  - Authorization policies
  - Traffic splitting for canary deployments
- **Database Security**:
  - PostgreSQL: SSL connections, password authentication
  - Network: VPC isolation, security groups
  - Encryption: Transparent Data Encryption (TDE) for storage
  - Row-level security (RLS) for multi-tenancy
- **Object Storage**:
  - Pre-signed URLs with short expiry (5 minutes)
  - Bucket policies: least privilege access
  - Versioning and MFA-delete for critical data
  - Server-side encryption (SSE-S3 or SSE-KMS)

### 7.3 Application Security
- **Input Validation**:
  - Pydantic models for request validation
  - Whitelist validation for file uploads (MIME types, extensions)
  - Size limits: 50MB for images, 5MB for JSON
  - Sanitization: HTML escape for user-generated content
- **SQL Injection Prevention**:
  - ORM (SQLAlchemy) with parameterized queries
  - Raw query prohibition in application code
  - WAF as secondary defense
- **XSS Prevention**:
  - Content Security Policy (CSP) headers
  - HTTPOnly cookies
  - Template auto-escaping (Jinja2, React)
  - Sanitize HTML output with DOMPurify
- **CSRF Protection**:
  - SameSite cookie attributes
  - CSRF tokens for state-changing operations
  - Referer header validation
- **File Upload Security**:
  - Virus scanning (ClamAV) on upload
  - File type verification (magic bytes, not extension)
  - Isolation: process uploads in sandboxed containers
  - Storage: separate bucket with no execute permissions

### 7.4 Data Protection
- **Encryption at Rest**:
  - PostgreSQL: TDE or pgcrypto for sensitive fields
  - Redis: encrypted Redis (if using Redis Enterprise)
  - Object storage: SSE-S3 or customer-managed keys
  - Backups: encrypted with AES-256
- **Encryption in Transit**:
  - TLS 1.3 everywhere
  - HSTS preloading
  - Certificate pinning for mobile apps
- **Data Minimization**:
  - GDPR compliance: right to erasure, portability
  - Pseudonymization for analytics
  - Retention policies: raw imagery 2 years, processed data 5 years
- **Secrets Management**:
  - HashiCorp Vault or AWS Secrets Manager
  - Automatic rotation: database passwords, API keys
  - No hardcoded secrets in code or configs

### 7.5 Monitoring & Auditing
- **Security Logging**:
  - Failed login attempts
  - Privileged operations
  - Configuration changes
  - Access to sensitive data (PHI, PII)
- **Intrusion Detection**:
  - Falco for runtime security
  - Network flow analysis (Zeek)
  - Log analysis (ELK with security dashboards)
- **Vulnerability Management**:
  - Regular dependency scanning (Snyk, Dependabot)
  - Container image scanning (Trivy, Clair)
  - Periodic penetration testing
  - Bug bounty program via HackerOne/ISRO

## 8. Scalability

### 8.1 Horizontal Scaling
- **Stateless Services**:
  - All API services designed to be stateless
  - Session state stored in Redis
  - Enables instant scaling behind load balancer
- **Database Scaling**:
  - PostgreSQL: read replicas for query distribution
  - Sharding strategy: by user_id or project_id range (if needed)
  - Connection pooling (PgBouncer) to manage DB connections
- **Caching Layer**:
  - Redis Cluster for horizontal scaling
  - Cache warming strategies
  - TTL-based eviction with lazy expiration
- **Message Queues**:
  - Redis Streams or Apache Kafka for event-driven processing
  - Consumer groups for parallel processing
  - Dead letter queues for failed message handling

### 8.2 Vertical Scaling
- **Resource Optimization**:
  - CPU/memory requests/limits in Kubernetes
  - Vertical Pod Autoscaler (VPA) for automatic adjustment
  - Node affinity for specialized workloads (GPU nodes for ML)
- **GPU Acceleration**:
  - Dedicated node pools for ML training/inference
  - Time-sharing for development vs. production workloads
  - Container resource isolation

### 8.3 Load Handling Projections

#### 100 Users (Development/Pilot)
- **Peak Concurrency**: 10 simultaneous users
- **API Requests**: ~50 requests/minute
- **Data Volume**: <10 GB satellite imagery/month
- **ML Inference**: <100 predictions/day
- **Infrastructure**:
  - 2 API replicas per service
  - Single PostgreSQL instance (db.t3.medium)
  - Redis cache (cache.t2.micro)
  - 1 GPU instance for ML (optional)

#### 1,000 Users (Beta/Regional)
- **Peak Concurrency**: 100 simultaneous users
- **API Requests**: ~500 requests/minute
- **Data Volume**: ~100 GB satellite imagery/month
- **ML Inference**: ~1,000 predictions/day
- **Infrastructure**:
  - 3-5 API replicas per service
  - PostgreSQL primary + 2 read replicas
  - Redis Cluster (3 nodes)
  - 2 GPU instances for ML training
  - Auto-scaling based on CPU/utilization

#### 10,000 Users (Production/National)
- **Peak Concurrency**: 1,000 simultaneous users
- **API Requests**: ~5,000 requests/minute
- **Data Volume**: ~1 TB satellite imagery/month
- **ML Inference**: ~10,000 predictions/day
- **Infrastructure**:
  - 10+ API replicas per service (auto-scaling groups)
  - PostgreSQL primary + 4+ read replicas + partitioning
  - Redis Cluster (6+ nodes)
  - Dedicated ML pipeline: 5+ GPU instances for training, 10+ for inference
  - CDN for static assets (CloudFront/Akamai)
  - Object storage with cross-region replication
  - Kafka for high-throughput event processing
  - Monitoring: Prometheus federation, Grafana Enterprise

### 8.4 Bottleneck Mitigation
- **Database**: Read replicas, caching, query optimization, partitioning
- **Storage**: CDN for static assets, multipart uploads, parallel downloads
- **Network**: Regional deployment, edge caching, compressed responses
- **Compute**: Spot instances, preemptible VMs, serverless for spiky workloads
- **Third-party APIs**: Rate limiting, caching, fallback mechanisms

## 9. Coding Standards

### 9.1 Language-Specific Standards

#### Python (Backend Services)
- **Style**: PEP 8 with 88-character line length (Black formatter)
- **Typing**: Strict type hints (mypy strict mode)
- **Documentation**: Docstrings (NumPy or Google style)
- **Dependencies**: Poetry or Pipenv for lockfiles
- **Testing**: pytest with coverage >80%
- **Linting**: Flake8 + pylint
- **Security**: Bandit for security linting
- **Structure**: 
  - Clean Architecture: entities, use_cases, interfaces, frameworks
  - Dependency Injection: using dependency-injector or manual
  - Repository Pattern for data access
  - Service Layer for business logic

#### JavaScript/TypeScript (Frontend)
- **Style**: ESLint with Airbnb config + Prettier
- **Typing**: TypeScript strict mode
- **State Management**: Redux Toolkit or Zustand
- **Components**: Functional components with hooks
- **Styling**: CSS Modules or Tailwind CSS
- **Testing**: Jest + React Testing Library
- **Bundle Optimization**: code splitting, lazy loading, tree shaking

#### SQL
- **Style**: SQLFluff with PostgreSQL dialect
- **Naming**: snake_case for identifiers
- **Comments**: Explain why, not what
- **Transactions**: Explicit BEGIN/COMMIT/ROLLBACK
- **Indexes**: Document purpose in migrations

### 9.2 Architectural Principles

#### SOLID
- **Single Responsibility**: Each class/service has one reason to change
- **Open/Closed**: Extensible via inheritance/composition, not modification
- **Liskov Substitution**: Subtypes must be substitutable for base types
- **Interface Segregation**: Clients should not depend on unused methods
- **Dependency Inversion**: Depend on abstractions, not concretions

#### Clean Architecture
- **Layers** (inner to outer):
  1. Entities: Enterprise-wide business rules
  2. Use Cases: Application-specific business rules
  3. Interface Adapters: Controllers, presenters, gateways
  4. Frameworks & Drivers: Web, database, UI
- **Dependency Rule**: Inner layers know nothing of outer layers

#### Repository Pattern
- Encapsulates data access logic
- Provides collection-like interface for domain objects
- Enables mocking for testing
- Centralizes query optimization

#### Dependency Injection
- Inversion of Control container
- Explicit dependencies via constructor injection
- Facilitates testing and decoupling

### 9.3 Development Practices
- **Git Workflow**: GitHub Flow with protected main branch
- **Code Reviews**: Mandatory for all PRs, minimum 2 approvals
- **Continuous Integration**: 
  - Unit tests on every PR
  - Security scans (SAST, dependency check)
  - Code quality gates
- **Continuous Deployment**:
  - Canary releases for backend services
  - Blue-green deployments for frontend
  - Feature flags for gradual rollout
- **Documentation**:
  - API specs: OpenAPI 3.0 (Swagger)
  - Architecture decisions: ADR (Architecture Decision Records)
  - Onboarding: CONTRIBUTING.md, README.md
- **Observability**:
  - Structured logging (JSON format)
  - Distributed tracing (OpenTelemetry)
  - Health checks (liveness/readiness probes)

## 10. Development Roadmap

### Phase 0: Foundation (Weeks 1-4)
- **Goals**:
  - Project setup and tooling
  - Core architecture decisions
  - Basic authentication and user management
- **Deliverables**:
  - Repository initialized with CI/CD pipeline
  - Docker-compose for local development
  - Auth service with JWT
  - User service with basic CRUD
  - API gateway with rate limiting
  - Basic frontend login/register pages
- **Milestone**: Authenticated user can access basic dashboard

### Phase 1: Data Ingestion & GIS Core (Weeks 5-8)
- **Goals**:
  - Satellite imagery acquisition
  - Basic GIS processing
  - Project management
- **Deliverables**:
  - Satellite service with Landsat/Sentinel download
  - GIS service with coordinate transformations
  - Project service with AOI definition
  - Basic map visualization (Leaflet)
  - Database schema implemented
  - Admin dashboard for service monitoring
- **Milestone**: User can create project, download satellite data for AOI, view on map

### Phase 2: Heat Detection & Basic ML (Weeks 9-12)
- **Goals**:
  - Urban Heat Island detection algorithms
  - First ML model for temperature prediction
  - Result storage and retrieval
- **Deliverables**:
  - Heat detection service with LST calculation
  - ML training service for baseline model
  - Inference service for batch predictions
  - Heat map visualization (color gradients)
  - Database models for satellite images and heat maps
  - Basic report generation (PDF)
- **Milestone**: User can process satellite image to generate heat map and download report

### Phase 3: Recommendation Engine & Advanced Features (Weeks 13-16)
- **Goals**:
  - Recommendation system for mitigation strategies
  - Simulation and what-if analysis
  - Alerting and notification system
- **Deliverables**:
  - Recommendation service with rule-based engine
  - Simulation service for impact modeling
  - Notification service (email/in-app)
  - Alert thresholds and triggering
  - Advanced report templates
  - Role-based access control
- **Milestone**: User receives mitigation recommendations based on heat analysis

### Phase 4: Forecasting & Optimization (Weeks 17-20)
- **Goals**:
  - Temperature forecasting models
  - Performance optimization
  - Security hardening
- **Deliverables**:
  - ML forecasting service (LSTM/Transformer)
  - Real-time inference capabilities
  - Caching layer implementation (Redis)
  - Load testing and optimization
  - Security audit and penetration test
  - Documentation completion
- **Milestone**: System can forecast temperature trends and suggest proactive measures

### Phase 5: Scale & Production Readiness (Weeks 21-24)
- **Goals**:
  - High availability and disaster recovery
  - Monitoring and observability
  - Final user acceptance testing
- **Deliverables**:
  - Kubernetes production deployment
  - Auto-scaling configurations
  - Comprehensive monitoring (Prometheus/Grafana)
  - Log aggregation and alerting (ELK)
  - Disaster recovery drills
  - User training materials
  - Final security compliance check
- **Milestone**: Platform handles 10,000 concurrent users with <2s response time

### Post-Launch: Continuous Improvement
- **Ongoing**:
  - Model retraining pipelines
  - Feature requests from users
  - Performance optimization
  - Security updates
  - New satellite data source integration
  - Mobile application development

## VERIFICATION

### ✔ Architecture is Modular
- Confirmed: Each service has single responsibility
- Services communicate via well-defined APIs
- Shared libraries prevent duplication
- Clear separation of concerns (API, business logic, data access)

### ✔ Database Normalized
- Confirmed: Schema follows 3NF
- No repeating groups
- Foreign key constraints enforce relationships
- Indexes support query patterns without denormalization
- Spatial data types used appropriately for geospatial queries

### ✔ APIs Complete
- Confirmed: All major entities have CRUD endpoints
- Authentication and authorization covered
- Real-time capabilities via WebSockets
- Versioning and error handling standardized
- Pagination, filtering, sorting implemented
- Health check and admin endpoints included

### ✔ Folder Structure Scalable
- Confirmed: Separation by concern (services, frontend, ml, gis, infra)
- Room for new services without restructuring
- Technology-agnostic organization
- Clear distinction between source, config, and deployment

### ✔ No Missing Modules
- Reviewed against requirements:
  - Satellite imagery: ✓ (Satellite Service)
  - GIS: ✓ (GIS Service)
  - Machine Learning: ✓ (ML Training, Inference Services)
  - Deep Learning: ✓ (supported in ML services)
  - Urban Heat Island Detection: ✓ (Heat Detection Service)
  - Temperature Forecasting: ✓ (ML forecasting in Phase 4)
  - Recommendation Engine: ✓ (Recommendation Service)
  - Interactive Maps: ✓ (Frontend with Leaflet/Mapbox)
  - PDF Reports: ✓ (Report Service)
  - Authentication: ✓ (Auth Service)
  - Admin Dashboard: ✓ (Admin Dashboard Service)
- Additional modules identified as needed:
  - Notification Service: ✓
  - Audit Logging: ✓
  - Caching Layer: ✓ (implied in scalability)
  - ML Pipeline components: ✓

### ✅ Design Complete and Verified
All requested elements have been addressed. The design provides a production-ready foundation for the Urban Heat Mitigation Platform.