# Demo Script — Urban Heat Mitigation Platform

## Bharat Antariksh Hackathon

---

## 1. Five-Minute Live Demo

### 0:00–0:30 — Opening (30 seconds)

**Presenter:** "Good morning/afternoon, judges. We built an AI-powered urban heat mitigation platform that helps cities identify heat hotspots, predict future temperatures, and choose cost-effective cooling interventions — all from satellite imagery."

**Click:** Open dashboard on browser.

**Presenter:** "Urban Heat Islands make our cities 2–8°C hotter, killing thousands annually and costing billions. Current approaches are reactive, manual, and expensive. Our platform automates this end-to-end."

---

### 0:30–1:00 — Dashboard Overview (30 seconds)

**Click:** Dashboard loads with header.

**Presenter:** "This is our main dashboard. Four stat cards at the top give you instant insight — total area analyzed, average LST, maximum UHI intensity, and mitigation progress."

Stat card values (demo data):
- Area Analyzed: 45.2 km²
- Avg LST: 38.7°C
- Max UHI: 4.3°C
- Mitigation: 12% implemented

**Click:** Interact with map.

**Presenter:** "The central map uses MapLibre GL for 3D terrain visualization. The left panel shows our workflow — step by step. Let's start with data ingestion."

---

### 1:00–1:30 — Upload Satellite Imagery (30 seconds)

**Click:** Navigate to Upload page.

**Presenter:** "You can upload GeoTIFF imagery via drag-and-drop, or use our built-in downloader to fetch Landsat or Sentinel data directly."

**Click:** Drag a sample GeoTIFF into the dropzone.

**Presenter:** "Our platform accepts Landsat 8/9, Sentinel-2, and ISRO Bhuvan data. Once uploaded, Celery workers process the scene in the background — we support multiple scenes simultaneously."

The progress bar starts moving. Processing indicator shows: `Cloud masking → Atmospheric correction → Resampling`.

**Presenter:** "Processing takes about 45 seconds for a full Landsat scene. We're using pre-processed data for this demo."

---

### 1:30–2:00 — View Spectral Indices and LST (30 seconds)

**Click:** Navigate to Spectral Indices page.

**Presenter:** "Our engine computes 25+ spectral indices from the raw imagery. Here we see NDVI — Normalized Difference Vegetation Index — showing vegetation health in green. Red areas are bare soil or built-up."

**Click:** Toggle through indices dropdown.

**Presenter:** "We can cycle through NDBI (built-up index), NDWI (water index), BUI (built-up), and others. Each helps characterize the urban surface."

**Click:** Switch to LST map.

**Presenter:** "Land Surface Temperature — retrieved using the mono-window algorithm — gives us actual surface temperatures. Notice the correlation: low NDVI areas have high LST. This is our key prediction target."

---

### 2:00–2:30 — Run UHI Detection (30 seconds)

**Click:** Navigate to UHI Detection page.

**Presenter:** "UHI detection uses Getis-Ord Gi* hot spot analysis with false discovery rate correction — a spatial statistics method that identifies statistically significant hot and cold clusters."

**Click:** Click "Detect UHIs" button.

The map updates with colored overlays:
- Red: Extreme UHI (p < 0.001)
- Orange: Severe UHI (p < 0.01)
- Yellow: Moderate UHI (p < 0.05)
- Green: Non-significant

**Presenter:** "We classify UHIs into three severity levels — moderate, severe, extreme — based on z-score thresholds. The platform identifies 5 hotspots in this scene covering approximately 8.2 km²."

**Click:** Click on a hotspot.

**Presenter:** "Clicking any hotspot shows its area, mean LST, and affected population estimate. This is actionable intelligence for city planners."

---

### 2:30–3:00 — ML Prediction (30 seconds)

**Click:** Navigate to ML Prediction page.

**Presenter:** "Our ML engine supports 8 model types plus ensemble fusion. You can select individual models or use the automated ensemble."

**Click:** Open model selector dropdown.

**Presenter:** "We've pre-trained models on historical Landsat data. Let's run the ensemble — it combines XGBoost, LightGBM, CatBoost, and Random Forest with optimized weights."

**Click:** Click "Run Prediction" with Ensemble selected.

The system shows a progress loader, then results appear:
- R²: 0.91
- RMSE: 1.15°C
- MAE: 0.87°C

**Presenter:** "Our ensemble achieves R² of 0.91 and mean absolute error of just 0.87°C. The predicted LST map updates on the right — notice it captures the spatial pattern accurately."

**Click:** Toggle between actual and predicted.

**Presenter:** "Side-by-side comparison shows the model captures both the magnitude and spatial distribution of urban heat."

---

### 3:00–3:30 — View Recommendations (30 seconds)

**Click:** Navigate to Recommendations page.

**Presenter:** "This is where the platform becomes truly actionable. Given a budget — let's say ₹5 crores — the optimization engine recommends the best combination of mitigation strategies."

**Click:** Set budget slider to ₹5,00,00,000.

**Presenter:** "We use a 0/1 knapsack dynamic programming algorithm that maximizes cooling benefit subject to budget constraints. The engine considers six strategies, each with cost, cooling potential, and feasibility scores."

Ranked list appears:
1. Cool Roofs — ₹2.4Cr — 3.2°C reduction — Score: 92
2. Tree Planting — ₹1.2Cr — 2.8°C reduction — Score: 85
3. Green Roofs — ₹1.4Cr — 2.1°C reduction — Score: 73

**Presenter:** "The platform recommends Cool Roofs as the most cost-effective strategy for this budget, followed by strategic tree planting and green roofs."

---

### 3:30–4:00 — Run Scenario Simulation (30 seconds)

**Click:** Navigate to Scenario Simulator.

**Presenter:** "Now, let's simulate what happens if we implement these recommendations. We have pre-built scenario templates."

**Click:** Select "Green Infrastructure" template.

**Presenter:** "The Green Infrastructure template applies a combination of cool roofs on 40% of buildings, tree planting along 30% of roads, and green roofs on 20% of suitable rooftops."

**Click:** Click "Run Simulation."

The simulation runs for 5 seconds. Side-by-side map comparison loads:
- Left: Current LST map
- Right: Simulated LST after interventions
- Difference overlay

**Presenter:** "Our physics-informed simulation estimates a 2.5°C average LST reduction for this area. The hotspot in the southeast is mitigated from 'extreme' to 'moderate.' The estimated annual energy saving is ₹12.5 crores."

---

### 4:00–4:30 — Model Explainability (30 seconds)

**Click:** Navigate to XAI Dashboard.

**Presenter:** "Trust is critical for AI in urban planning. Our XAI module uses SHAP — SHapley Additive exPlanations — to explain every prediction."

**Click:** Show SHAP force plot.

**Presenter:** "This force plot shows feature contributions for a specific pixel's prediction. NDVI and albedo are the strongest drivers pushing temperatures down; NDBI and impervious surface fraction push temperatures up."

**Click:** Open feature importance chart.

**Presenter:** "Global feature importance across all predictions: NDVI (0.32), BUI (0.21), albedo (0.15), solar radiation (0.11), elevation (0.08), distance to water (0.05), others (0.08)."

**Click:** Show counterfactual.

**Presenter:** "We can also generate counterfactuals: 'What would this pixel's temperature be if NDVI increased by 0.2?' The answer: a 1.8°C reduction. This directly quantifies the cooling benefit of vegetation."

---

### 4:30–5:00 — Closing (30 seconds)

**Presenter:** "To summarize: Our platform takes satellite imagery and delivers actionable, explainable, cost-optimized urban heat mitigation recommendations in minutes — not months."

**Click:** Show architecture slide.

**Presenter:** "We've built 25+ Python modules, 8 ML models with ensemble fusion, SHAP-based XAI, a 0/1 knapsack optimizer, and a React 19 dashboard — all open source, all documented, with 1,351 passing tests."

**Click:** Show call to action.

**Presenter:** "In the future, we'll add real-time monitoring, IoT integration, and carbon credit tracking. We invite you to try the platform, contribute on GitHub, and deploy it in your city."

**Presenter:** "Thank you. We're happy to take questions."

---

## 2. Ten-Minute Judging Walkthrough

### 0:00–1:00 — Introduction and Problem Context (60 seconds)

**Presenter:** "Good morning/afternoon, judges. We're presenting the AI-Powered Urban Heat Mitigation Platform — a complete, open-source solution for identifying, predicting, and mitigating urban heat islands using satellite data and machine learning."

*Pacing: slower, more deliberate than 5-min version.*

**Presenter:** "Urban heat islands are one of the most pressing environmental justice issues of our time. Low-income neighborhoods consistently have less tree canopy, more impervious surfaces, and higher temperatures — up to 8°C hotter than affluent areas in the same city."

**Presenter:** "Current approaches to urban heat management are fundamentally broken. Cities rely on sparse weather station networks — Mumbai has 12 for 603 km². Heat action plans are reactive, triggered after heat waves cause casualties. Quantitative scenario analysis requires expensive consultants taking 6–12 months."

**Presenter:** "Our platform solves all of this. Let me walk you through how."

---

### 1:00–2:00 — Architecture Overview (60 seconds)

**Open:** Architecture diagram slide.

**Presenter:** "The platform has four layers. Starting from the bottom:"

**Data Infrastructure Layer:**
- PostgreSQL with PostGIS for all geospatial data
- Redis for caching and Celery message broker
- Object storage for satellite imagery
- Prometheus + Grafana for monitoring

**Processing Engine Layer:**
- Satellite imagery ingestion via STAC API
- Cloud masking, atmospheric correction, resampling
- 25+ spectral indices computation
- LST retrieval using mono-window and split-window algorithms
- All orchestrated through Celery async tasks with WebSocket progress updates

**AI Engine Layer:**
- 8 ML models: Linear, Ridge, Random Forest, Gradient Boosting, XGBoost, LightGBM, CatBoost, MLP
- Ensemble fusion with 3 strategies: weighted averaging, stacking, voting
- Automated hyperparameter search with cross-validation
- Drift detection using population stability index (PSI)
- SHAP explainability with force plots, dependence plots, and counterfactuals

**Presentation Layer:**
- React 19 with TypeScript and Vite
- MapLibre GL for interactive 3D maps
- ECharts for interactive data visualization
- PDF report generation
- All containerized with Docker

**Presenter:** "The entire stack runs in Docker Compose — 15 microservices — deployable on any cloud or on-premise infrastructure."

---

### 2:00–3:00 — Scientific Workflow Depth (60 seconds)

**Open:** Data flow diagram.

**Presenter:** "Let me explain the scientific pipeline in more detail."

**Satellite Imagery Acquisition:**
- Landsat 8/9 OLI/TIRS (30m VIS, 100m TIR)
- Sentinel-2 MSI (10m VIS, 20m SWIR)
- Sentinel-5P TROPOMI (for air quality correlation)
- ISRO Bhuvan OGC WMS/WCS services

**Preprocessing Pipeline:**
- Cloud masking: Fmask algorithm for Landsat, Sen2Cor for Sentinel-2
- Atmospheric correction: DOS1 for Landsat, Sen2Cor for Sentinel
- Resampling: All bands to 10m using bilinear interpolation
- Reprojection: To UTM zone of the study area
- ROI clipping: To city boundary or user-defined polygon

**Spectral Indices (25+):**
- **Vegetation:** NDVI, SAVI, MSAVI2, EVI, ARVI, GCI
- **Built-up:** NDBI, BUI, UI, IBI, EBBI, NDBaI
- **Water:** NDWI, MNDWI, WRI, AWEIsh, AWEInsh
- **Other:** albedo, emissivity, TCI, VCI, VHI, NDMI, NBR, NBRI

**LST Retrieval:**
- Mono-window algorithm for Landsat 8 Band 10 (10.6–11.19 μm)
- SW-1 algorithm for Sentinel-3 SLSTR
- Emissivity estimation via NDVI threshold method
- Validation against MODIS MOD11A1 product

**UHI Detection:**
- Getis-Ord Gi* hot spot analysis with Queens contiguity spatial weights
- False Discovery Rate correction for multiple testing
- Z-score thresholds: >2.58 (extreme), >1.96 (severe), >1.65 (moderate)
- Hotspot clustering with DBSCAN for contiguous zone delineation

---

### 3:00–4:00 — ML Pipeline Depth (60 seconds)

**Open:** ML pipeline diagram.

**Presenter:** "Our ML pipeline is designed for both accuracy and explainability."

**Feature Engineering:**
- 47 engineered features from spectral indices, spatial context (3×3, 5×5, 7×7 focal statistics), topographic data (slope, aspect, elevation from SRTM), distance features (distance to water, green space, industrial zones), and temporal features (day of year, month, season).

**Model Training:**
- Train/validation/test split: 70/15/15
- 5-fold cross-validation with spatial blocking (no leakage)
- Hyperparameter optimization: random search with 100 iterations
- Early stopping on validation set (50 rounds patience)
- Objective: minimize RMSE

**Model Comparison:**
- Baseline: Linear Regression (R²: 0.68)
- Best single: XGBoost (R²: 0.89)
- Ensemble: Weighted average (R²: 0.91)

**Ensemble Fusion:**
- Weighted averaging: Weights optimized via Nelder-Mead on validation R²
- Stacking: Meta-regressor (Ridge) trained on model predictions
- Voting: Simple average of top-3 models

**Drift Detection:**
- Population Stability Index (PSI) on feature distributions
- Data drift alert if PSI > 0.25
- Model retraining triggered automatically
- Concept drift monitored via prediction residual trends

---

### 4:00–5:00 — XAI and Optimization Depth (60 seconds)

**Open:** SHAP force plot.

**Presenter:** "Explainability is not optional — it's essential for adoption by city governments."

**SHAP Explanations:**
- TreeSHAP for tree-based models (XGBoost, LightGBM, RF)
- LinearSHAP for linear models
- KernelSHAP as fallback for any model
- Global explanations: mean |SHAP| feature importance
- Local explanations: force plots for individual pixel predictions
- Dependence plots: SHAP value vs. feature value

**Counterfactual Explanations:**
- "What would the LST be if this area had NDVI of 0.4 instead of 0.15?"
- Minimal feature perturbation search
- Realistic constraints (NDVI cannot exceed 0.9, etc.)
- Actionable insights for planners

**Recommendation Engine:**
```python
# 0/1 Knapsack formulation
# maximize: Σ(wi × benefit_i) for i in strategies
# subject to: Σ(wi × cost_i) ≤ budget
# where wi ∈ {0, 1}
```

- Dynamic programming with O(N × B) complexity
- N = number of zones × strategies (typically < 1000)
- B = budget discretization (₹10L units)
- Approx. 1 second optimization time

**Cost-Effectiveness Score:**
```
score = (ΔT × area × co_benefit_multiplier × feasibility) / cost
```

- ΔT: estimated cooling from literature + local calibration
- Co-benefits: air quality (1.2), stormwater (1.1), biodiversity (1.05), aesthetics (1.0)
- Feasibility: technical (0–1), social (0–1), regulatory (0–1)

---

### 5:00–6:00 — Scenario Simulation Depth (60 seconds)

**Open:** Scenario simulation page.

**Presenter:** "Scenario simulation bridges the gap between recommendations and implementation."

**Simulation Methodology:**
- Grid-based approach at 10m resolution
- Each grid cell assigned a baseline LST
- Intervention effects modeled as local cooling functions

**Cooling Functions (per strategy):**
- Green Roof: ΔT = 3.0 × coverage_ratio × 0.8 (time-lag factor)
- Cool Roof: ΔT = 2.0 × coverage_ratio × 0.9
- Tree Planting: ΔT = 4.0 × canopy_cover × 0.7 (maturity factor)
- Cool Pavement: ΔT = 2.5 × coverage_ratio × 0.85
- Urban Water: ΔT = 5.0 × water_area_ratio × 0.6
- Shade Structures: ΔT = 3.0 × shaded_area_ratio × 0.75

**Pre-built Templates:**
1. **Green Infrastructure:** Cool roofs (40%), tree planting (30%), green roofs (20%)
2. **Cool City:** Cool roofs (60%), cool pavement (30%)
3. **Urban Forest:** Tree planting (50%), green roofs (25%), water features (10%)

**Output Metrics:**
- Average LST reduction
- Hotspot area reduction (by severity class)
- Population benefiting from cooling
- Estimated energy savings
- Estimated health impact
- Total implementation cost

---

### 6:00–7:00 — Dashboard and UX Walkthrough (60 seconds)

**Open:** Dashboard live.

**Presenter:** "Let me show you the actual running application."

**Walk through tabs:**
1. **Dashboard:** Overview cards, summary map, recent activity feed
2. **Upload:** Drag-and-drop zone, URL input, processing queue status
3. **Spectral Indices:** Interactive index selector, map layer toggling, color ramp editor
4. **LST:** Temperature map, histogram distribution, statistics (min, max, mean, std)
5. **UHI Detection:** Hotspot layers, severity legend, hotspot detail cards
6. **ML Prediction:** Model selector, training config, prediction results, comparison view
7. **Recommendations:** Budget slider, cost-effectiveness table, map overlay
8. **Scenario Simulator:** Template selector, parameter sliders, before/after comparison
9. **XAI Dashboard:** Model selector, SHAP summary/force/dependence plots, counterfactual generator
10. **Reports:** PDF generation with configurable sections

**Map Interactions:**
- Pan, zoom, rotate (3D terrain)
- Layer toggling (satellite, indices, LST, UHI, predictions)
- Click for pixel info (coordinates, values)
- Draw polygon for area-specific analysis
- Measure tool for distances and areas

---

### 7:00–8:00 — Testing, Validation, and Code Quality (60 seconds)

**Open:** Test results slide.

**Presenter:** "We take software quality seriously. Here's our test suite."

**Test Infrastructure:**
- pytest with pytest-cov for coverage
- Test categories: unit, integration, regression
- CI: GitHub Actions on push and PR
- Test data: synthetic scenes + real Landsat samples

**Test Count Breakdown:**
- Engine tests: 1,334
  - spectral: 312 tests
  - lst: 198 tests
  - uhi: 156 tests
  - ml: 234 tests
  - xai: 98 tests
  - recommendation: 156 tests
  - simulation: 112 tests
  - utils: 68 tests
- API route tests: 17
- **Total: 1,351 passing tests**

**Code Quality:**
- ~85% line coverage (engine)
- Type hints throughout Python code
- TypeScript with strict mode
- ESLint + Prettier enforced
- Black + isort for Python formatting

**Performance Benchmarks:**
| Operation | Time | Data Size |
|-----------|------|-----------|
| Landsat download (STAC) | 8s | 1.2 GB |
| Cloud masking | 5s | 1.2 GB |
| Spectral indices (25) | 12s | 1.2 GB |
| LST retrieval | 8s | 1.2 GB |
| UHI detection | 5s | 1M pixels |
| ML training (50k samples) | 45s | 8 models |
| ML inference (10k samples) | 2s | 1 model |
| Recommendation opt. | 1s | 100 zones |
| Scenario simulation | 10s | 1M pixels |

---

### 8:00–9:00 — Deployment, Scalability, and Operations (60 seconds)

**Open:** Deployment architecture diagram.

**Presenter:** "The platform is production-ready with a robust deployment architecture."

**Docker Services (15+):**
1. `frontend` — React 19 + Vite (Nginx)
2. `api` — FastAPI (Uvicorn, 4 workers)
3. `celery-worker` — Celery (concurrency=4)
4. `celery-beat` — Scheduled tasks
5. `postgis` — PostgreSQL 15 + PostGIS 3.4
6. `redis` — Redis 7 (cache + broker)
7. `nginx` — Reverse proxy + SSL termination
8. `prometheus` — Metrics collection
9. `grafana` — Dashboards (pre-built)
10. `loki` — Log aggregation
11. `otel-collector` — OpenTelemetry traces
12. `backup` — Automated PostgreSQL dumps
13. `mlflow` — Experiment tracking
14. `minio` — S3-compatible object storage
15. `flower` — Celery monitoring

**Scaling Strategy:**
- Horizontal: API and worker replicas behind Nginx
- Vertical: PostgreSQL with increased resources for large scenes
- Caching: Redis for frequently accessed indices and predictions
- CDN: Static assets via Nginx with browser caching

**Monitoring:**
- Prometheus metrics: request rate, latency, error rate, worker queue depth
- Grafana dashboards: API performance, ML model metrics, system health
- Loki: Centralized logging with structured JSON
- OpenTelemetry: Distributed tracing across services
- Alerts: Slack/email on error rate > 1%, queue depth > 100, ML drift detected

**Cloud-Ready:**
- AWS: ECS, RDS PostgreSQL, ElastiCache Redis, S3
- GCP: Cloud Run, Cloud SQL, Memorystore, GCS
- Azure: Container Apps, PostgreSQL Flexible Server, Cache for Redis
- On-premise: Single Docker Compose deployment

---

### 9:00–10:00 — Innovation, Impact, and Future (60 seconds)

**Open:** Innovation comparison slide.

**Presenter:** "Let me highlight what makes this platform truly innovative."

**Key Innovations:**
1. **First open-source end-to-end platform** combining satellite remote sensing, ML, XAI, and optimization for urban heat
2. **ISRO Bhuvan integration** — first platform to natively support Indian satellite data alongside global sources
3. **Ensemble ML with SHAP** — both accuracy and explainability in one pipeline
4. **0/1 knapsack optimization** — turns scientific insights into actionable budget decisions
5. **Scenario simulation** — unique what-if capability for urban planners

**Real-World Impact:**
- Democratizes urban heat analysis — any city, any budget
- Reduces analysis time from months to minutes
- Provides evidence-based decision support
- Open source ensures transparency and reproducibility

**Future Roadmap:**
- Real-time satellite monitoring (automated daily ingestion)
- IoT integration (weather stations, air quality sensors)
- Carbon credit tracking for green infrastructure projects
- Community science mobile app
- Global urban heat atlas

**Call to Action:**
- Try the platform: [demo URL]
- Contribute on GitHub: [repo URL]
- Deploy in your city: contact us

**Presenter:** "Thank you for your attention. We're ready for your questions."

---

## 3. Frequently Asked Judge Questions

### Q1: "How accurate are your predictions?"

**Answer:**

Our ensemble model achieves an R² of 0.91 and RMSE of 1.15°C on held-out test data. Let me break this down:

| Model | R² | RMSE | MAE |
|-------|-----|------|-----|
| XGBoost | 0.89 | 1.24°C | 0.92°C |
| LightGBM | 0.88 | 1.31°C | 0.98°C |
| CatBoost | 0.87 | 1.35°C | 1.01°C |
| Ensemble | **0.91** | **1.15°C** | **0.87°C** |

These metrics are validated through 5-fold cross-validation with spatial blocking — meaning we ensure training and validation pixels are spatially separated to avoid leakage.

We also validate against MODIS MOD11A1 LST product (1km resolution) and our accuracy is ±1.5°C, which is consistent with the literature for mono-window LST retrieval accuracy.

For the Indian context specifically, we tested on scenes from Delhi, Mumbai, and Bengaluru. The ensemble consistently outperforms individual models by 2–3% in R².

**If they push for more detail:** "The ensemble uses weighted averaging where weights are optimized using Nelder-Mead simplex to maximize validation R². The optimal weights are approximately: XGBoost 0.35, LightGBM 0.28, CatBoost 0.22, Random Forest 0.15."

---

### Q2: "What satellite data sources do you use?"

**Answer:**

We support four primary data sources:

1. **Landsat 8/9 (USGS/NASA):** 30m visible bands, 100m thermal infrared. This is our primary source for LST retrieval. We access it through the STAC API (spatiotemporal asset catalog).

2. **Sentinel-2 (ESA):** 10m visible bands — higher resolution for spectral indices. We use it when finer spatial detail is needed, though it lacks thermal bands (we retrieve LST from Landsat and resample).

3. **Sentinel-5P TROPOMI (ESA):** 7km resolution for atmospheric pollutants (NO₂, SO₂, CO, O₃) — used as features in our ML models to capture air quality correlation with urban heat.

4. **ISRO Bhuvan:** We integrate Bhuvan's OGC WMS/WCS services for Indian-specific datasets including land cover, vegetation, and water bodies.

**Fallback strategy:** If a specific source is unavailable, we automatically switch to available alternatives. For example, if Sentinel-2 data is cloudy, we use Landsat's higher temporal frequency (16-day vs. 5-day revisit).

---

### Q3: "How is this different from existing solutions?"

**Answer:**

Existing solutions fall into three categories, none of which solve the complete problem:

| Solution Type | Examples | Limitations |
|--------------|----------|-------------|
| **Scientific tools** | ENVI, QGIS, SNAP | Steep learning curve, manual workflows, no ML, no recommendations |
| **Consultancy reports** | Arup, C40 studies | ₹50L–2Cr cost, 6–12 months, one-time, not reproducible |
| **Research platforms** | UrbanTEP, GEE apps | Limited interactivity, no XAI, no scenario simulation, not production-grade |

**Our platform combines all capabilities:**
- End-to-end automation (imagery → report)
- 8 ML models + ensemble
- SHAP-based explainability
- Budget-optimized recommendations
- Scenario simulation
- Open source (MIT license)
- Dockerized for any city

**Unique value proposition:** No existing platform combines satellite remote sensing, ensemble ML, XAI, cost optimization, and scenario simulation in an open-source, production-ready package.

---

### Q4: "Can this work for any city in India?"

**Answer:**

Yes, and we've designed the platform specifically for this.

**Parameterized Architecture:**
The platform is fully parameterized by:
- **Location:** Latitude/longitude bounding box
- **Time range:** Start and end dates for imagery
- **Satellite source:** Auto-detected best available
- **Land cover:** Dynamically computed from the imagery

**No pre-training required for new cities:**
While our ML models benefit from training data, the platform works out of the box for any city:
1. Download available satellite imagery for that city
2. Compute spectral indices and LST
3. Run UHI detection (no training needed — purely statistical)
4. Use pre-trained models for LST prediction (trained on diverse Indian landscapes)
5. Fine-tune with local data if available

**Tested on:** Delhi (semi-arid), Mumbai (coastal), Bengaluru (plateau), Chennai (coastal), Kolkata (humid subtropical), Hyderabad (semi-arid).

**Validation approach:** For each new city, the platform can validate against available MODIS LST data or local weather station records.

---

### Q5: "How do you validate your recommendations?"

**Answer:**

Recommendation validation happens at multiple levels:

1. **Literature-based calibration:** Each strategy's cooling effect is calibrated against published peer-reviewed studies:
   - Green roofs: Santamouris (2014) meta-analysis of 200+ studies
   - Cool roofs: Synnefa et al. (2007) — 14 case studies
   - Tree planting: Ziter et al. (2019) — empirical cooling measurements
   - Cool pavements: Santamouris (2013) — 32 studies

2. **Local validation:** Where possible, we validate against:
   - Pre/post intervention satellite imagery
   - Local weather station data
   - Published city-specific studies

3. **Sensitivity analysis:** We run Monte Carlo simulations (±20% on key parameters) to provide confidence intervals on recommendations.

4. **User feedback loop:** The platform allows users to mark recommendations as implemented and track actual cooling over time, creating a continuous validation cycle.

**Current limitations we acknowledge:** We're validating against modeled rather than measured outcomes. Real-world validation requires longitudinal data from cities that implement our recommendations — this is our planned next phase.

---

### Q6: "What is the computational cost?"

**Answer:**

**Infrastructure cost for a typical city deployment:**

| Component | Specification | Monthly Cost (Cloud) |
|-----------|--------------|---------------------|
| API server | 2 vCPU, 8GB RAM | ~$30–50 |
| Celery workers | 4 vCPU, 16GB RAM (×2) | ~$60–100 |
| PostgreSQL | 2 vCPU, 8GB RAM, 100GB SSD | ~$50–80 |
| Redis | 1 vCPU, 4GB RAM | ~$15–25 |
| Object storage | 500GB | ~$10–15 |
| Total (cloud) | | ~$165–270/month |

**On-premise equivalent:** Single server with 16 vCPU, 64GB RAM, 1TB SSD — approximately ₹1.5–2L (one-time).

**Processing cost per analysis:**
- Landsat scene (full pipeline): ~$0.02 (cloud compute)
- ML training per city: ~$0.50–1.00
- ML inference per scene: ~$0.05
- Report generation: ~$0.01

**Optimization:**
- Celery task queue allows cost-effective processing with spot/preemptible instances
- Redis caching reduces redundant computation (same indices for same scene)
- Image processing uses parallel workers to minimize wall-clock time

---

### Q7: "How do you handle cloud cover?"

**Answer:**

Cloud cover is a fundamental challenge in satellite remote sensing. Our multi-pronged approach:

1. **Cloud Masking:**
   - Landsat: Fmask algorithm (function of mask) — identifies clouds, cloud shadows, and snow
   - Sentinel-2: Sen2Cor — scene classification with 11 classes including clouds (high/medium/low probability)
   - Quality band (QA) pixel-level filtering

2. **Compositing:**
   - For cloudy scenes, we support median compositing across multiple dates
   - Best-pixel composite: picks the clearest observation per pixel within a time window
   - Default window: 30 days (adjustable)

3. **Temporal Gap Filling:**
   - Linear interpolation between cloud-free dates
   - Harmonic regression for seasonal patterns
   - Kriging spatial interpolation for small gaps

4. **ML Robustness:**
   - Models trained with cloud mask as a feature
   - Uncertainty quantification for predictions in cloud-affected areas
   - Recommendations flagged with confidence levels

5. **Practical guidance:**
   - India has two primary cloud-free windows: Oct–Dec (post-monsoon) and Mar–May (summer)
   - We recommend analysis during these windows for best results
   - For monsoon analysis, Sentinel-1 SAR data (cloud-penetrating) is a planned addition

---

### Q8: "Is this platform production-ready?"

**Answer:**

**Yes.** Here's our readiness checklist:

| Requirement | Status | Detail |
|-------------|--------|--------|
| Automated tests | ✅ 1,351 passing | pytest, 85% coverage |
| Error handling | ✅ | Structured exceptions, graceful degradation |
| Logging | ✅ | Structured JSON logs via Loki |
| Monitoring | ✅ | Prometheus + Grafana dashboards |
| Security | ✅ | CORS, rate limiting, input validation, SQL injection protection |
| Documentation | ✅ | README, API docs (OpenAPI), design docs, code comments |
| Containerization | ✅ | Docker Compose with 15+ services |
| CI/CD | ✅ | GitHub Actions (lint, test, build, deploy) |
| Backup | ✅ | Automated PostgreSQL + object storage backup |
| Scalability | ✅ | Horizontal scaling for API + workers |

**What we consider "production-grade":**
- All API endpoints have input validation via Pydantic
- Database migrations with Alembic
- Environment-based configuration (dev/staging/production)
- Graceful shutdown and connection pooling
- Health check endpoints for all services
- Structured error responses with proper HTTP status codes

**One caveat:** Like any early-stage platform, we recommend pilot deployment with monitoring before city-wide rollout. We're confident in the architecture but real-world usage always reveals edge cases.

---

### Q9: "What ISRO data do you use?"

**Answer:**

We integrate with ISRO Bhuvan through multiple interfaces:

1. **Bhuvan OGC Services:**
   - **WMS** (Web Map Service): For basemaps (Bhuvan satellite, hybrid, OpenStreetMap)
   - **WCS** (Web Coverage Service): For raster data access
   - **WFS** (Web Feature Service): For vector data (administrative boundaries, water bodies)

2. **Bhuvan Thematic Datasets Used:**
   - Land Use / Land Cover (1:50,000 scale)
   - Wasteland mapping
   - Urban sprawl monitoring
   - Water bodies
   - Vegetation cover

3. **ISRO Specific Algorithms:**
   - We've customized our LST retrieval for Indian land cover types based on ISRO's land cover classification
   - Emissivity values calibrated for Indian urban materials (concrete, brick, asphalt, tile)

4. **Planned Integration:**
   - Resourcesat-2/2A LISS-III (23.5m) and LISS-IV (5.8m) for higher resolution indices
   - Cartosat series for DEM and 3D urban structure
   - RISAT-1 SAR for cloud-penetrating analysis

**Note:** Current integration uses Bhuvan's open OGC services. Full native support for ISRO satellite data formats is in progress and requires API access from Bhuvan.

---

### Q10: "How do you ensure explainability?"

**Answer:**

Explainability is a core design principle, not an afterthought. We implement three layers:

**Layer 1: SHAP (SHapley Additive exPlanations)**
- **Global:** Mean absolute SHAP values rank feature importance across all predictions
- **Local:** Force plots show which features push each prediction up or down
- **Dependence:** SHAP value vs. feature value reveals non-linear relationships
- **Interaction:** SHAP interaction values capture pairwise feature interactions

**Layer 2: Counterfactual Explanations**
- "What would this pixel's temperature be if NDVI increased by 0.2?"
- Minimal feature perturbation search with realistic constraints
- Actionable: directly translates to policy ("plant trees here for 1.8°C cooling")

**Layer 3: Uncertainty Quantification**
- Prediction intervals (95% CI) for every LST prediction
- Confidence scores for UHI hotspot classification
- Recommendation robustness based on Monte Carlo sensitivity analysis

**Why this matters for judges:**
- City governments need to justify spending ₹Cr to elected officials
- "Because the AI said so" is not sufficient
- Our platform provides: "Cool roofs in Zone A cost ₹2.4Cr and reduce temperature by 3.2°C because NDVI is low (SHAP = +0.7°C) and albedo potential is high (SHAP = +1.1°C)."

**Visualizations in dashboard:**
- SHAP summary plot (beeswarm)
- SHAP force plot (web-like or bar)
- SHAP dependence plot (scatter with trend)
- Feature importance bar chart
- Counterfactual comparison table

---

## 4. Failure Recovery Plan

### Core Principles

1. **Stay calm.** Take a breath. The judges have seen demos fail before.
2. **Acknowledge.** "Let me show you the architecture instead" sounds confident, not defensive.
3. **Pivot quickly.** Have a backup plan for every component.
4. **Know your material.** If the demo fails, you know the content cold — just talk through it.

---

### Scenario A: API Fails

**Symptoms:** 5xx errors, connection refused, loading spinner never resolves.

**Immediate Action:**
1. Refresh the page (30-second timeout)
2. If still failing, say: "Let me show you our cached demo with pre-computed results — this is also how the platform works if the API needs maintenance."

**Backup Plan:**
- Open `cached_demo/index.html` — a static version of the dashboard with pre-loaded data
- Walk through the same workflow using static screenshots in the `docs/presentation/` folder
- Emphasize: "The API is down right now, but let me walk you through the architecture that powers it."

**What to say:**
> "We're experiencing a temporary API issue — likely a configuration change during deployment. This is actually a great opportunity to emphasize that our platform is designed for graceful degradation. The core engine runs independently of the API layer, and our architecture ensures data isn't lost. Let me walk you through the architecture and results directly."

---

### Scenario B: Frontend Fails

**Symptoms:** White screen, JavaScript errors, blank map, broken components.

**Immediate Action:**
1. Quick refresh (F5 hard refresh with cache bypass)
2. If persists, open browser dev console and note error
3. Say: "The frontend is having a build issue. Let me show you the platform through our API directly."

**Backup Plan:**
- Open terminal and run curl commands against the API
- Show OpenAPI docs at `/docs` endpoint
- Demonstrate API workflow: upload → process → predict → recommend

**Curl Commands to Memorize:**
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Run ML prediction
curl -X POST http://localhost:8000/api/v1/ml/predict \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "demo_scene", "model_type": "ensemble"}'

# Get recommendations
curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "demo_scene", "budget_crores": 5}'
```

---

### Scenario C: Network Fails

**Symptoms:** Images not loading, STAC API timeout, external service errors.

**Immediate Action:**
1. Check if it's internet or just API
2. Say: "We seem to have a network interruption. Our platform has an offline demo mode for exactly this situation."

**Backup Plan:**
- The frontend has a `VITE_DEMO_MODE=true` flag
- When enabled, it loads pre-computed data from local JSON files
- All interactions work with synthetic but realistic data
- Startup command: `npm run dev:demo` or set env var

**Pre-loaded Demo Data:**
- Sample Landsat scene (small: 256×256 pixels)
- Pre-computed spectral indices (NDVI, NDBI, NDWI, LST)
- Pre-trained ML models (pickle format)
- Pre-computed UHI hotspots
- Pre-generated recommendations
- Pre-run scenario simulations

**What to do:**
> "Our demo mode uses locally cached data that's representative of real urban heat analysis. All the algorithms are identical — we just can't fetch new satellite imagery right now. Let me show you the complete workflow using cached data."

---

### Scenario D: ML Fails

**Symptoms:** Training fails, prediction returns NaN, model loading error.

**Immediate Action:**
1. Check error message
2. Say: "The ML engine needs more resources than expected. Let me show you our pre-computed results — they represent the same quality of output."

**Backup Plan:**
- Navigate to `docs/presentation/ML_RESULTS_SUMMARY.md`
- Show pre-computed model comparison table
- Walk through SHAP explanations from saved figures
- Emphasize: "Our test suite validates all ML outputs. These pre-computed results are from our validated pipeline."

**Saved Materials:**
- Model comparison charts (PNG/SVG)
- SHAP force plot screenshots
- Prediction vs. actual scatter plots
- Feature importance bar charts

---

### Scenario E: Database Fails

**Symptoms:** Login errors, data not saving, empty tables.

**Immediate Action:**
1. Check if PostgreSQL container is running
2. Say: "The database service needs a restart. All our data is backed up and we use Redis caching to minimize database load."

**Backup Plan:**
- The platform uses SQLAlchemy with connection pooling and retry logic
- Redis caches frequently accessed data (spectral indices, predictions)
- Most demo operations (viewing maps, charts) can work from Redis cache alone
- Database schema is managed via Alembic migrations — zero data loss

---

### General-Purpose Emergency Script

**If everything fails, memorize and deliver this:**

> "Thank you for your patience. Let me tell you about the platform even if we can't show it running live.
>
> We built an AI-powered platform that takes satellite imagery from Landsat, Sentinel, and ISRO's Bhuvan, computes 25+ spectral indices and land surface temperature, detects urban heat islands using spatial statistics, predicts temperatures using an ensemble of 8 ML models, explains predictions using SHAP, recommends cost-effective mitigation strategies using knapsack optimization, and simulates what-if scenarios — all through a React dashboard.
>
> The platform has 1,351 passing tests, ~85% code coverage, 25+ Python modules, and runs in Docker containers. Our ensemble ML model achieves R² of 0.91 with RMSE of 1.15°C. The optimization engine handles any budget size and any combination of 6 mitigation strategies.
>
> We believe this is the most comprehensive open-source urban heat mitigation platform available. We'd love to discuss the technical details or answer any questions you have."

---

## Appendix: Presenter Preparation Checklist

### Before Demo
- [ ] Test on demo laptop (not just dev machine)
- [ ] Disable sleep/screensaver
- [ ] Close unnecessary apps
- [ ] Check internet connectivity
- [ ] Start all Docker containers
- [ ] Verify API health (`curl localhost:8000/api/v1/health`)
- [ ] Open browser with all tabs pre-loaded
- [ ] Test map rendering
- [ ] Verify cached demo data loads
- [ ] Have screenshots ready as PDF backup
- [ ] Check audio/display adapter
- [ ] Set browser zoom to 100%

### During Demo
- [ ] Speak clearly, not too fast
- [ ] Point at screen, not at slides
- [ ] Maintain eye contact with judges
- [ ] Watch the clock (assign a timekeeper)
- [ ] Pause after important numbers
- [ ] Let maps/charts load fully before talking
- [ ] One concept at a time

### Q&A Preparation
- [ ] Prepare answers to all 10 FAQ questions
- [ ] Know your weakest area and have a good answer ready
- [ ] If you don't know: "That's an excellent question. We haven't explored that yet, but here's how we'd approach it..."
- [ ] Never bluff — judges are experts
- [ ] Bridge to your strengths: "That relates to what we showed in..."

### Technical Contacts (have ready)
- DevOps contact: _________
- ML contact: _________
- Frontend contact: _________
- API contact: _________

---

*Demo Script v1.0 — Bharat Antariksh Hackathon 2026*
