# Urban Heat Mitigation Platform — Frequently Asked Questions (FAQ)

**Version 1.0.0** | July 2026

---

## Table of Contents

1. [General Questions](#1-general-questions)
2. [Technical Questions](#2-technical-questions)
3. [Data Questions](#3-data-questions)
4. [ML / AI Questions](#4-ml--ai-questions)
5. [Usage Questions](#5-usage-questions)
6. [Business Questions](#6-business-questions)

---

## 1. General Questions

### Q1: What is the Urban Heat Island (UHI) effect?

The **Urban Heat Island (UHI)** effect refers to the phenomenon where urban areas experience significantly higher temperatures than surrounding rural areas. This occurs because:

- **Dark surfaces** (asphalt, concrete, dark roofs) absorb and re-radiate solar energy as heat.
- **Reduced vegetation** means less evaporative cooling (evapotranspiration).
- **Building geometry** traps heat and reduces wind flow.
- **Waste heat** from vehicles, HVAC systems, and industrial processes adds thermal energy.

UHI can raise urban temperatures by 1–7 °C (1.8–12.6 °F) compared to nearby rural areas, with the greatest differences occurring at night.

### Q2: What is the Urban Heat Mitigation Platform?

The Urban Heat Mitigation Platform (UHMP) is an AI-powered decision-support system that helps urban planners, environmental scientists, and policymakers:

1. **Detect** urban heat hotspots using satellite remote sensing.
2. **Predict** future temperature patterns using machine learning.
3. **Recommend** cost-effective mitigation strategies.
4. **Simulate** what-if scenarios for urban cooling interventions.

It combines Landsat 8/9 and Sentinel-2 satellite imagery with XGBoost, LightGBM, and CatBoost models to provide actionable insights.

### Q3: Who is the platform designed for?

The platform serves multiple user groups:

| User Group | Primary Use Case |
|---|---|
| **Urban Planners** | Identify heat-vulnerable areas, plan green infrastructure |
| **Environmental Scientists** | Analyze LST patterns, validate models, publish research |
| **Policymakers** | Justify climate adaptation funding, set heat mitigation targets |
| **GIS Analysts** | Export data to existing GIS workflows |
| **NGOs / Community Groups** | Advocate for equitable heat mitigation investments |

### Q4: Is the platform free to use?

The platform is **open-source** under the MIT License. You can self-host it free of charge.

Hosted/SaaS versions may have pricing tiers depending on the provider:

| Tier | Limitations | Typical Pricing |
|---|---|---|
| Community | 5 scenes/month, 1 user | Free |
| Professional | 100 scenes/month, 10 users | $500/month |
| Enterprise | Unlimited, SSO, dedicated support | Custom pricing |

Check with your specific hosting provider for their pricing structure.

### Q5: How do I cite the platform in academic work?

Please use the following citation:

```
Urban Heat Mitigation Platform (UHMP) [Computer software]. (2026).
Version 1.0.0. Retrieved from https://github.com/yourorg/uhmp
```

For academic papers, also cite the relevant satellite data sources:

- Landsat: `U.S. Geological Survey. (2024). Landsat 8-9 Level 2, Collection 2. https://doi.org/10.5066/P9OGBGM6`
- Sentinel-2: `European Space Agency. (2024). Sentinel-2 MSI Level-2A. https://doi.org/10.5270/S2-znb3w0k`

---

## 2. Technical Questions

### Q6: What satellite imagery does the platform use?

The platform supports multiple satellite sensors:

| Sensor | Resolution | Bands Used | Revisit Time |
|---|---|---|---|
| Landsat 8/9 | 30 m (thermal: 100 m resampled to 30 m) | Visible, NIR, SWIR, Thermal | 16 days |
| Sentinel-2 | 10 m (visible/NIR), 20 m (SWIR) | Visible, NIR, SWIR | 5 days |
| MODIS | 1 km | Thermal | Daily |
| Custom UAV | Variable | User-defined | As needed |

Landsat and Sentinel-2 are the primary sources for UHI analysis due to their balance of resolution, thermal capability, and free access.

### Q7: Can I use my own aerial imagery or drone data?

Yes. The platform accepts custom GeoTIFF imagery. Requirements:

- Must be georeferenced (WGS84 / EPSG:4326 preferred).
- Must include at least one thermal infrared band (8–14 μm) for LST computation.
- Radiometric calibration metadata is strongly recommended.
- File size up to 2 GB per upload.

For best results, pre-process your imagery to surface reflectance before uploading.

### Q8: What machine learning models are used?

The platform includes four model types:

| Model | Type | Strengths |
|---|---|---|
| **XGBoost** | Gradient-boosted trees | Fast training, handles missing data, built-in regularization |
| **LightGBM** | Leaf-wise gradient boosting | Faster than XGBoost, lower memory usage, handles categorical features |
| **CatBoost** | Ordered boosting | Best for heterogeneous features, robust to overfitting, native categorical support |
| **Ensemble** | Stacked ensemble | Highest accuracy, combines all three models via meta-learner |

All models are trained on historical LST, spectral indices, land cover data, and demographic features.

### Q9: How are predictions evaluated?

Models are evaluated using standard regression metrics:

| Metric | Good | Excellent |
|---|---|---|
| R² Score | > 0.80 | > 0.90 |
| RMSE | < 2.0 °C | < 1.0 °C |
| MAE | < 1.5 °C | < 0.8 °C |
| MAPE | < 10% | < 5% |

Cross-validation is performed using 5-fold spatial cross-validation (by geographic region) to prevent spatial autocorrelation bias.

### Q10: What is SHAP and how does it work?

**SHAP** (SHapley Additive exPlanations) is a game-theoretic approach to explain machine learning model predictions. It works by:

1. Computing the contribution of each feature to the prediction.
2. Averaging contributions across all possible feature subsets (Shapley values).
3. Producing an additive explanation: `prediction = base_value + sum(feature_contributions)`.

In the platform, SHAP helps answer "Why is this area predicted to be a hotspot?" by showing which features (e.g., low NDVI, high impervious surface) drove the prediction.

### Q11: How does confidence scoring work?

Confidence scores are derived from:

- **Model uncertainty:** Variance across ensemble members (for ensemble model) or prediction intervals (for quantile regression).
- **Data uncertainty:** How similar the input features are to the training distribution (density estimation).
- **Spatial uncertainty:** Distance from nearest training data point.

The overall confidence is a weighted combination, expressed as a percentage (0–100%).

### Q12: What is counterfactual explanation?

A counterfactual explanation answers: "What would need to change for this area to NOT be a hotspot?"

For example, if an area has:
- NDVI = 0.12, Albedo = 0.15, Impervious = 85%

The counterfactual might show:
- NDVI = 0.45 (+0.33), Albedo = 0.35 (+0.20), Impervious = 45% (−40%)

This directly translates to actionable recommendations (e.g., "increase vegetation cover by X amount").

---

## 3. Data Questions

### Q13: How is Land Surface Temperature (LST) calculated?

LST is calculated using the following workflow:

1. **Thermal band calibration:** Convert DN to at-sensor radiance using metadata.
2. **Brightness temperature:** Convert radiance to brightness temperature using Planck's function.
3. **Land surface emissivity:** Estimate from NDVI (fractional vegetation cover method) or use ASTER GED emissivity library.
4. **LST retrieval:**
   - **Landsat (two thermal bands):** Split-window algorithm (Wan & Dozier, 1996).
   - **Sentinel-2 (no thermal band):** Single-channel algorithm using band 10 (TIRS-like) or relationship with spectral indices.
   - **MODIS:** Pre-processed LST product (MOD11).

The formula for the split-window algorithm is:
```
Ts = T1 + C1(T1 - T2) + C2(T1 - T2)^2 + C0 + (C3 + C4W)(1 - ε) + (C5 + C6W)Δε
```
Where T1/T2 are brightness temperatures in the two thermal bands, ε is mean emissivity, Δε is emissivity difference, W is atmospheric water vapor, and C0–C6 are coefficients.

### Q14: What satellite data sources are free?

All primary satellite data sources used by the platform are freely available:

| Source | Access URL | License |
|---|---|---|
| Landsat 8/9 | https://earthexplorer.usgs.gov | Free & open |
| Sentinel-2 | https://scihub.copernicus.eu | Free & open (ESA) |
| MODIS | https://lpdaac.usgs.gov | Free & open |
| ASTER GED | https://lpdaac.usgs.gov/products/ag100v003/ | Free & open |
| OpenStreetMap | https://www.openstreetmap.org | ODbL |

### Q15: How are recommendations calculated?

Recommendations use a **multi-objective optimization** approach:

1. **Objective functions:**
   - Maximize temperature reduction (ΔT).
   - Minimize total cost.
   - Maximize co-benefit score (air quality, stormwater, biodiversity, social).
   - Maximize implementation speed.

2. **Constraints:**
   - Total budget (user-defined).
   - Available area per land cover type.
   - Strategy applicability rules (e.g., green roofs only on buildings with slope < 30°).

3. **Algorithm:** NSGA-II (Non-dominated Sorting Genetic Algorithm II) generates a Pareto front of optimal solutions.

4. **Ranking:** Solutions are ranked using a weighted sum of objectives (weights configurable in the UI).

### Q16: How accurate is the temperature prediction?

Accuracy depends on data availability and regional characteristics:

| Scenario | Typical RMSE | Best Case RMSE |
|---|---|---|
| Well-sampled urban area (100+ scenes) | 1.2–1.8 °C | 0.8 °C |
| Moderate sampling (20–100 scenes) | 1.8–2.5 °C | 1.2 °C |
| Sparse sampling (< 20 scenes) | 2.5–4.0 °C | 2.0 °C |
| No local training data (global model) | 3.0–5.0 °C | 2.5 °C |

For best accuracy, upload at least 20 scenes covering different seasons and years for your study area.

### Q17: What data can I export?

| Format | Data Types | Max Size |
|---|---|---|
| PDF Report | Full analysis with maps, charts, tables | 50 MB |
| CSV | Point samples, polygon attributes, time series | 500 MB |
| GeoJSON | Hotspot polygons, study areas, sample points | 200 MB |
| GeoTIFF | LST rasters, spectral index rasters | 2 GB per band |
| PNG/SVG | Map screenshots, charts | 10 MB |

### Q18: How is population exposure estimated?

Population exposure is estimated using:

1. **Gridded population data:** WorldPop or GPWv4 at 1 km (global) or 100 m (selected countries) resolution.
2. **Spatial overlay:** Intersect hotspot polygons with population grids.
3. **Proportional allocation:** Sum population counts weighted by hotspot area fraction per grid cell.

**Limitation:** This assumes uniform population distribution within each grid cell. For more precise estimates, upload local census block data.

---

## 4. ML / AI Questions

### Q19: How often should models be retrained?

| Scenario | Recommended Retrain Frequency |
|---|---|
| Stable urban area, new seasonal data | Quarterly |
| Rapidly developing area | Monthly |
| After major heat events (heatwaves) | Immediately after |
| When drift is detected | As soon as possible |
| Best practice | At least annually |

The platform monitors feature drift continuously. An alert is triggered when the PSI exceeds 0.15.

### Q20: Can I train models on my own data?

Yes. The platform supports:

- **Fine-tuning:** Update existing models with new local data.
- **Full training:** Train from scratch on your curated dataset.
- **Transfer learning:** Use the global pre-trained model as a starting point.

Upload training data as a CSV with columns matching the feature set (see CONFIGURATION.md Section 6).

### Q21: What features are used in the ML models?

The standard feature set includes:

| Feature | Source | Type |
|---|---|---|
| NDVI | Satellite | Continuous (−1 to 1) |
| NDBI | Satellite | Continuous (−1 to 1) |
| NDWI | Satellite | Continuous (−1 to 1) |
| BSI | Satellite | Continuous (−1 to 1) |
| SAVI | Satellite | Continuous (−1 to 1) |
| Elevation | DEM | Continuous (m) |
| Slope | Derived from DEM | Continuous (degrees) |
| Albedo | Satellite | Continuous (0–1) |
| Impervious Surface % | Derived from NDBI | Continuous (0–100) |
| Vegetation Cover % | Derived from NDVI | Continuous (0–100) |
| Population Density | Census | Continuous (persons/km²) |
| Building Height | LiDAR/OSM | Continuous (m) |
| Road Density | OSM | Continuous (km/km²) |
| Distance to Water | Derived | Continuous (m) |
| Distance to Park | Derived | Continuous (m) |
| Land Cover Class | Classified | Categorical (10 classes) |
| Month | Calendar | Cyclical (1–12) |
| Hour (if diurnal) | Time of acquisition | Cyclical (0–23) |

### Q22: What is model drift and how is it detected?

**Model drift** occurs when the statistical relationship between features and target variables changes over time, causing predictions to become less accurate.

The platform detects drift using:

1. **Population Stability Index (PSI):** Measures distribution shift in features between training and production data.
   - PSI < 0.10: No significant drift
   - PSI 0.10–0.25: Moderate drift (alert triggered)
   - PSI > 0.25: Severe drift (model may be disabled)

2. **Kolmogorov-Smirnov (KS) Test:** Compares feature distributions.
   - p < 0.05: Significant distribution change

3. **Prediction vs. Actual monitoring:** When ground truth is available, tracks prediction error over time.

---

## 5. Usage Questions

### Q23: How do I get started quickly?

1. **Upload a satellite scene** (Data > Upload) — use a Landsat 8/9 scene from your area.
2. **Run preprocessing** — cloud masking and atmospheric correction.
3. **Compute NDVI and LST** (Analysis > Spectral Indices, Analysis > LST).
4. **Run UHI detection** (Analysis > UHI Detection) to see hotspots.
5. **Generate recommendations** (Recommendations) with a sample budget.

Total time from upload to first results: approximately 15–30 minutes for a standard Landsat scene.

### Q24: How many scenes do I need for meaningful analysis?

| Use Case | Minimum Scenes | Recommended |
|---|---|---|
| Single time-point hotspot mapping | 1 summer scene | 2–3 scenes (different years) |
 | Seasonal analysis | 4 scenes (1 per season) | 8+ scenes (2 years) |
| Trend analysis | 10+ scenes over 3+ years | 20+ scenes over 5+ years |
| ML model training | 20 scenes | 100+ scenes |
| Change detection | 2 scenes (before/after) | 4+ scenes (multiple time points) |

### Q25: How long does processing take?

Processing times depend on scene size, resolution, and server resources:

| Operation | Small Scene (10 km²) | Large Scene (100 km²) |
|---|---|---|
| Upload + Validation | 30 sec | 3 min |
| Cloud Masking | 1 min | 5 min |
| Atmospheric Correction | 2 min | 10 min |
| Spectral Index (per index) | 30 sec | 3 min |
| LST Computation | 2 min | 8 min |
| UHI Detection | 1 min | 5 min |
| ML Prediction | 30 sec | 3 min |
| Recommendation Engine | 1 min | 2 min |
| Scenario Simulation | 2 min | 10 min |
| PDF Report Generation | 1 min | 5 min |

### Q26: Can I collaborate with other users?

Yes. The platform supports:

- **Shared study areas:** Create a study area and grant access to other users.
- **Shared scenes:** Scenes uploaded by one user can be viewed/used by team members.
- **Comments:** Add comments to scenes, hotspots, and recommendations.
- **Role-based access:** Admin, Analyst, and Viewer roles (see USER_GUIDE Section 2.5).

### Q27: How do I interpret the color maps?

See USER_GUIDE Section 6.3 for detailed color map interpretation tables. Key guidelines:

- **LST:** Blue = cool (water/vegetation), Red = hot (urban/bare soil).
- **NDVI:** Green = dense vegetation, Red = sparse/no vegetation.
- **NDBI:** Red = built-up, Blue = vegetated/water.
- **Confidence:** Green = high confidence, Red = low confidence.

### Q28: Can I schedule recurring analyses?

Not yet in v1.0.0. This feature is planned for v2.0.0. In the meantime, you can:

- Use the API to trigger analyses programmatically.
- Set up cron jobs or CI/CD pipelines for periodic processing.
- Use Celery Beat to schedule periodic tasks (requires code customization).

---

## 6. Business Questions

### Q29: Can this platform help with regulatory compliance?

Yes. The platform can support:

- **Climate Action Plans:** Provide data-driven evidence for heat mitigation targets.
- **Environmental Justice Assessments:** Identify heat-vulnerable communities (when combined with demographic data).
- **Environmental Impact Reports:** Quantify heat impacts of proposed developments.
- **Grant Applications:** Provide visual evidence and cost-benefit analysis for funding requests.
- **Urban General Plans:** Inform land use and zoning decisions with heat vulnerability data.

### Q30: How does the platform handle data privacy?

- **User data isolation:** Multi-tenant architecture ensures user data is isolated.
- **Encryption:** Data encrypted at rest (MinIO/AES-256) and in transit (TLS 1.3).
- **Authentication:** JWT-based with optional MFA.
- **Audit logging:** All user actions are logged.
- **Data retention:** Users can delete their data at any time. Exports are auto-deleted after 7 days.
- **GDPR compliance:** Data can be exported and deleted upon request.

### Q31: Can I whitelabel the platform?

Yes. The platform supports:

- **Custom branding:** Logo, colors, and application name in the frontend.
- **Custom domain:** Deploy under your organization's domain.
- **Custom report templates:** Add your organization's logo and styling to PDF reports.
- **Custom email domain:** Send notifications from your domain.

Configuration options are available in the Admin panel and `.env` file.

### Q32: What support options are available?

| Tier | Hours | SLA | Price |
|---|---|---|---|
| Community | Self-service | Best effort | Free |
| Standard | Business hours | 8-hour response | Included with Professional plan |
| Premium | 24/7 | 1-hour response | Custom |
| Enterprise | 24/7 + dedicated engineer | 15-minute response | Custom |

### Q33: How do I request a feature?

Feature requests can be submitted via:

1. **GitHub Issues:** https://github.com/yourorg/uhmp/issues
2. **Community Forum:** https://community.uhmp.example.com
3. **Feature voting board:** https://features.uhmp.example.com

We follow a community-driven prioritization process:

1. Feature request submitted → triaged by maintainers
2. Community upvoting → prioritize by demand
3. Feasibility assessment → technical review
4. Roadmap inclusion → scheduled for development

---

*© 2026 Urban Heat Mitigation Platform. All rights reserved.*
*Last updated: July 2, 2026*
*For questions, contact support@uhmp.example.com*
