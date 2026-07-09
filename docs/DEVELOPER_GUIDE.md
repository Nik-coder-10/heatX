# Urban Heat Mitigation Platform — Developer Guide

## Repository Structure

```
urbanheat/
├── backend/                        # Python FastAPI backend
│   ├── app/
│   │   ├── api/v1/endpoints/       # Route handlers (18 modules)
│   │   ├── core/                   # Config, DB, JWT, security
│   │   ├── database/               # Base, session, enums, mixins
│   │   ├── features/               # GeoFeature Engineering (17 modules)
│   │   ├── indices/                # Spectral Indices engine
│   │   ├── lst/                    # Land Surface Temperature engine
│   │   ├── ml/                     # ML Forecasting engine (8 model types)
│   │   ├── preprocessing/          # Raster preprocessing pipeline
│   │   ├── raster/                 # Raster management
│   │   ├── recommendation/         # Recommendation engine
│   │   ├── repositories/          # Data access layer
│   │   ├── satellite/              # Satellite acquisition
│   │   ├── scenario/              # Scenario simulation
│   │   ├── schemas/               # Pydantic request/response models
│   │   ├── services/              # Business logic layer
│   │   ├── shared/                # Shared utilities
│   │   ├── uhi/                   # UHI detection engine
│   │   └── xai/                   # Explainable AI engine
│   ├── tests/                     # 1351 test suite
│   ├── alembic/                   # Database migrations
│   └── alembic.ini
├── frontend/                       # React 19 + TypeScript + Vite
│   ├── src/
│   │   ├── components/            # UI, map, chart, layout components
│   │   ├── pages/                 # 11 route pages
│   │   ├── services/              # API client modules
│   │   ├── hooks/                 # Custom React hooks
│   │   ├── types/                 # TypeScript type definitions
│   │   └── utils/                 # Formatters, color maps
│   └── vite.config.ts
├── deploy/                         # Production deployment
│   ├── docker/                    # Dockerfiles (backend, frontend, worker)
│   ├── docker-compose.prod.yml    # 15-service production stack
│   ├── monitoring/                # Prometheus, Grafana, Loki, OTel
│   ├── nginx/                     # Nginx configs
│   ├── scripts/                   # Deploy, backup, health-check
│   └── security/                  # Container hardening
├── docs/                           # Documentation
│   ├── api/                       # API reference
│   ├── architecture/              # Architecture diagrams
│   ├── demo/                      # Demo scripts, metrics
│   └── presentation/              # Pitch deck, diagrams
├── .github/                        # CI/CD, issue templates
├── requirements.txt               # Python dependencies
└── .env.production                # Environment template
```

## Development Environment

### Prerequisites

- Python 3.11+ (3.11 recommended)
- Node.js 20+ (20 LTS recommended)
- Docker Desktop 24+ with Docker Compose
- PostgreSQL 15+ with PostGIS 3.3+
- Redis 7+
- Git

### Quick Setup (Backend)

```bash
# Clone and enter backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r ../requirements.txt
pip install -r requirements-dev.txt  # if separate

# Set up environment
cp ../.env.production .env
# Edit .env with local development values

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Quick Setup (Frontend)

```bash
# Clone and enter frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Docker Development

```bash
# Single command (from project root)
./deploy/scripts/deploy.sh dev
```

## Coding Standards

### Python

| Rule | Standard | Enforcement |
|------|----------|-------------|
| Formatter | Black (line-length=120) | `black --check backend/` |
| Linter | Ruff (all rules) | `ruff check backend/` |
| Type checker | mypy (strict mode) | `mypy backend/` |
| Import order | isort (Black-compatible) | `isort --check backend/` |
| Docstrings | Google style | Manual review |

### TypeScript/React

| Rule | Standard | Enforcement |
|------|----------|-------------|
| Formatter | Prettier | `npx prettier --check src/` |
| Linter | ESLint (flat config) | `npm run lint` |
| Type checker | TypeScript (strict mode) | `tsc -b` |
| Component style | Functional components with hooks | ESLint react-hooks |

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Python modules | `snake_case` | `uhi_detection.py` |
| Python classes | `PascalCase` | `UrbanHeatIslandDetector` |
| Python functions | `snake_case` | `detect_hotspots()` |
| Python variables | `snake_case` | `lst_threshold` |
| TypeScript files | `camelCase.ts` | `hotspotLayer.ts` |
| React components | `PascalCase.tsx` | `HotspotLayer.tsx` |
| CSS classes | `kebab-case` | `uhi-severity-high` |
| API endpoints | `kebab-case` | `/api/v1/heat/detect` |
| Database tables | `snake_case` | `urban_heat_islands` |
| Git branches | `type/description` | `feat/add-sar-support` |

### Commit Convention (Conventional Commits)

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `perf`, `security`

Examples:
```
feat(ml): add CatBoost model support
fix(xai): handle edge case in SHAP explainer with single-feature input
docs(api): update recommendation endpoint response schema
test(uhi): add spatial cross-validation test for hotspot detection
```

## Architecture Decisions

### Why FastAPI?

- Async-native with `asyncio` for concurrent I/O (satellite downloads, database queries)
- Automatic OpenAPI/Swagger generation from Pydantic models
- High performance (on par with Node.js and Go)
- Native WebSocket support for real-time status updates
- Dependency injection system for clean service wiring
- Excellent Pydantic v2 integration for request/response validation

### Why PostgreSQL + PostGIS?

- Mature geospatial SQL support (ST_* functions, spatial indexing with GiST)
- Raster storage and analytics (ST_Clip, ST_Union for satellite imagery tiles)
- Transactional integrity for recommendation and scenario state
- JSONB for flexible schema evolution in feature stores
- Extensive ecosystem (pg_stat_statements, pg_partman, PostGIS raster)

### Why Celery + Redis?

- Reliable task queue with retries, rate limiting, and priority
- Long-running task support (satellite downloads can take 5-30 minutes)
- Task chaining and groups for complex pipelines (preprocess → index → detect)
- Redis as both broker and result backend reduces infrastructure complexity
- Flower dashboard for worker monitoring in development

### Why MapLibre GL (not Google Maps/Leaflet)?

- Open-source with no API key requirement or usage quotas
- Full vector tile support with Mapbox Vector Tile (MVT) spec
- Custom raster tile rendering for satellite imagery overlays
- WebGL-accelerated rendering for smooth 60fps map interactions
- Active community and maintained fork of Mapbox GL JS v1

### Why ECharts (not D3/Chart.js)?

- Built-in support for geospatial heatmaps, scatter maps, and flow maps
- Superior large-dataset rendering (WebGL backend for 100K+ points)
- Rich built-in interactivity (data zoom, brush selection, tooltip)
- Dark theme support out of the box
- Declarative option-based API (easier to maintain than D3 imperative)

## Module Registry Pattern

The platform uses a centralized registry pattern for extensibility:

```python
# app/shared/registry.py

MODEL_REGISTRY = {}
INDEX_REGISTRY = {}
RECOMMENDATION_REGISTRY = {}
SCENARIO_REGISTRY = {}

def register_model(name: str):
    """Decorator to register an ML model."""
    def decorator(cls):
        MODEL_REGISTRY[name] = cls
        return cls
    return decorator
```

### Adding a New ML Model

```python
from app.shared.registry import register_model, MODEL_REGISTRY

@register_model("my_new_model")
class MyNewModel(BaseModel):
    """Custom ML model implementation."""

    def __init__(self, **kwargs):
        super().__init__()
        self.model = None

    def fit(self, X, y):
        # Training logic
        pass

    def predict(self, X):
        # Inference logic
        pass

    def predict_proba(self, X):
        # Probability estimates
        pass
```

Then register it in the API:
```python
# In ml_training.py or inference.py
from app.ml.models import MODEL_REGISTRY

@router.post("/train")
def train_model(model_type: str = Body(...)):
    if model_type not in MODEL_REGISTRY:
        raise HTTPException(400, f"Unknown model: {model_type}")
    model_class = MODEL_REGISTRY[model_type]
    model = model_class(**kwargs)
```

### Adding a New Mitigation Strategy

1. Add to `app/recommendation/rules.py`:
```python
RULES.append({
    "name": "my_strategy",
    "cost_per_hectare": 500000,
    "temp_reduction_per_hectare": 0.15,
    "carbon_sequestration_per_hectare": 5.0,
    "landcover_requirements": [...],
    "min_ndvi": 0.0,
    "max_ndvi": 0.5,
})
```

2. Add scenario template in `app/scenario/templates.py`:
```python
TEMPLATES.append({
    "name": "my_strategy",
    "feature_modifiers": {
        "albedo": {"op": "add", "value": 0.15, "min": 0.1, "max": 0.8},
        "ndvi": {"op": "add", "value": 0.05},
    }
})
```

3. Add frontend card in Recommmendations and Scenario pages.

## Testing Guide

### Running Tests

```bash
# All backend tests
cd backend && pytest -v

# Specific module tests
pytest tests/test_ml.py -v
pytest tests/test_xai.py -v
pytest tests/test_recommendation.py -v
pytest tests/test_scenario.py -v
pytest tests/test_api_routes.py -v
pytest tests/test_uhi.py -v

# With coverage
pytest --cov=app --cov-report=term --cov-report=html

# Frontend tests
cd frontend && npm run test

# Deployment validation
pytest deploy/tests/test_deployment.py -v
```

### Test Structure

```
backend/tests/
├── test_ml.py              # 85 tests - all model types, ensemble, CV, HPO
├── test_xai.py             # 102 tests - SHAP, permutation, counterfactuals
├── test_recommendation.py  # 52 tests - rules, scoring, optimization
├── test_scenario.py        # 41 tests - templates, simulator, comparator
├── test_api_routes.py      # 17 tests - all endpoint integration
├── test_uhi.py             # 77 tests - detection engine
├── test_features.py        # 55 tests - feature engineering
├── test_lst.py             # LST engine tests
├── test_indices.py         # Spectral indices tests
├── test_preprocessing.py   # Preprocessing pipeline tests
└── test_satellite_*.py     # Satellite acquisition tests
```

### Writing Tests

Each test module follows the Arrange-Act-Assert pattern:

```python
class TestModelTraining:
    def test_random_forest_training(self, sample_features, sample_target):
        """Random Forest trains without errors."""
        model = RandomForestModel(n_estimators=100)
        model.fit(sample_features, sample_target)
        predictions = model.predict(sample_features)
        assert len(predictions) == len(sample_target)
        assert isinstance(predictions[0], float)
```

## Database Migrations

```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "add_sar_bands_table"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1

# View history
alembic history

# Show current version
alembic current
```

## Frontend Component Development

### Component Hierarchy

```
App
├── ThemeProvider
│   └── QueryClientProvider
│       └── BrowserRouter
│           └── MainLayout
│               ├── Sidebar (navigation, theme toggle)
│               ├── Header (breadcrumbs, user menu)
│               └── <Outlet> (page content)
│                   ├── Dashboard (stats + charts + map)
│                   ├── SatelliteUpload (drag-drop + table)
│                   ├── LSTViewer (map + charts)
│                   ├── SpectralIndices (selector + map)
│                   ├── UrbanHeatViewer (map + table + charts)
│                   ├── Forecasting (stats + chart + config)
│                   ├── Recommendations (stats + list + charts)
│                   ├── ScenarioSimulator (toggles + charts)
│                   ├── ModelExplainability (charts + gauges)
│                   ├── Reports (templates + form)
│                   └── Admin (stats + health + config)
```

### Creating a New Page

```typescript
// src/pages/MyNewPage.tsx
import { useState } from 'react';
import { Card, CardHeader, CardTitle } from '@/components/ui/Card';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';

export function MyNewPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['my-data'],
    queryFn: () => api.get('/api/v1/my-endpoint'),
  });

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>My New Feature</CardTitle>
        </CardHeader>
        {/* Content */}
      </Card>
    </div>
  );
}
```

Then add to the router:
```typescript
// src/App.tsx
import { MyNewPage } from '@/pages/MyNewPage';

<Route path="/my-new-feature" element={<MyNewPage />} />
```

## API Development

### Adding an Endpoint

```python
# backend/app/api/v1/endpoints/my_feature.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db

router = APIRouter(prefix="/my-feature", tags=["my-feature"])

@router.get("/")
def list_items(db: Session = Depends(get_db)):
    """List all items with pagination."""
    items = db.query(MyModel).all()
    return {"items": items, "total": len(items)}

@router.post("/")
def create_item(item: MySchema, db: Session = Depends(get_db)):
    """Create a new item."""
    db_item = MyModel(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
```

Then register in `backend/app/api/v1/api.py`:
```python
from app.api.v1.endpoints import my_feature
api_router.include_router(my_feature.router)
```

## Deployment

```bash
# Development
./deploy/scripts/deploy.sh dev

# Production
cp .env.production .env
# Edit .env with production values
./deploy/scripts/deploy.sh prod --monitoring

# Production with HTTPS
sudo ./deploy/scripts/init-letsencrypt.sh yourdomain.com email@example.com
./deploy/scripts/deploy.sh prod --https --monitoring
```

## Performance Optimization Tips

1. **Database queries**: Use eager loading (`selectinload`, `joinedload`) for related entities
2. **Raster processing**: Use `rasterio` windowed reads for large rasters
3. **ML inference**: Batch predictions where possible
4. **Caching**: Redis cache for frequently accessed geospatial queries
5. **Frontend**: Virtualize large lists with `@tanstack/react-virtual`
6. **Static assets**: Vite code splitting for route-based chunks
7. **Image optimization**: WebP format for satellite thumbnails

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Forgetting to run migrations before starting backend | Always run `alembic upgrade head` or use Docker health check |
| Frontend proxy not matching backend port | Check `vite.config.ts` proxy target |
| GIS library version conflicts (GDAL, GEOS) | Use Docker to avoid system library conflicts |
| Redis connection refused | Ensure `REDIS_HOST` env var matches Docker service name |
| Model import errors | Register model in `MODEL_REGISTRY` before importing |
| CORS errors in development | Check `BACKEND_CORS_ORIGINS` includes frontend URL |
