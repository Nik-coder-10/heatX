# Urban Heat Mitigation Platform — Scientific Methods

## Satellite Acquisition

### Landsat 8/9 OLI/TIRS

The platform acquires Landsat 8 (OLI/TIRS) and Landsat 9 (OLI-2/TIRS-2) scenes from USGS Collection 2 Level-1 and Level-2 products. Scene selection uses the USGS STAC API and NASA's Common Metadata Repository (CMR).

**Acquisition criteria:**
- Cloud cover < 20% over area of interest (configurable)
- Scene center within 30-day window of target date
- Priority to Collection 2 Level-2 surface reflectance products
- Fallback to Level-1 with atmospheric correction if Level-2 unavailable

**Bands acquired:**
- Reflective: B1 (coastal), B2 (blue), B3 (green), B4 (red), B5 (NIR), B6 (SWIR1), B7 (SWIR2)
- Thermal: B10 (TIRS1), B11 (TIRS2)

### Sentinel-2 MSI

Sentinel-2 Level-1C (top-of-atmosphere) and Level-2A (bottom-of-atmosphere) products are acquired from ESA's Copernicus Open Access Hub and AWS Open Data registry.

**Acquisition criteria:**
- Cloud cover < 20% over area of interest
- Tile-based query using ESA's Sentinel-2 tiling grid
- Prefer Level-2A (already atmospherically corrected via Sen2Cor)

**Bands acquired:**
- 10m: B2 (blue), B3 (green), B4 (red), B8 (NIR)
- 20m: B5, B6, B7 (red edge), B8A (narrow NIR), B11 (SWIR1), B12 (SWIR2)
- 60m: B1 (coastal), B9 (water vapour), B10 (cirrus)

### ISRO Bhuvan

For the Indian subcontinent, Resourcesat-2/2A LISS-III and LISS-IV data are acquired via ISRO's Bhuvan API and NRSC data portal. AWiFS 56m data is used for regional-scale analyses.

**Limitations:** Bhuvan thermal data availability is limited. For LST retrieval over Indian cities, Landsat or Sentinel-2 (paired with thermal sharpening) is preferred.

---

## Preprocessing

### Cloud Masking

**Fmask (Function of mask) algorithm** (Zhu et al., 2015) is applied to all optical scenes. The algorithm uses:

1. **Cloud probability test**: Based on physical cloud properties (brightness, temperature, spectral variability)
2. **Cloud shadow test**: Geometric matching of cloud objects with potential shadow locations using solar geometry
3. **Snow test**: Normalized Snow Difference Index (NDSI) threshold
4. **Cirrus test**: Band 9 (1.36-1.38 um) for thin cirrus detection

**QA Band processing:** For Level-2 products, the QA band is used directly with bit-mask flags:
- Landsat: Pixel QA band bits 3-4 (cloud), bit 5 (cloud shadow), bit 6 (snow/ice)
- Sentinel-2: Scene Classification Layer (SCL) classes 3 (cloud shadow), 8-9 (cloud), 11 (snow)

**Implementation:** Binary erosion (kernel size 3x3) is applied to cloud masks to remove single-pixel artifacts. Cloud buffer of 300m is applied to reduce adjacency effects.

### Atmospheric Correction

**DOS1 (Dark Object Subtraction 1)** (Chavez, 1996):
- Assumes existence of dark objects (deep water, dense shadow) with near-zero surface reflectance
- Haze value computed from histogram minimum of each band
- Simplest correction; used when atmospheric parameters unavailable

**6S (Second Simulation of Satellite Signal in the Solar Spectrum)**:
- Full radiative transfer code accounting for molecular absorption, Rayleigh scattering, aerosol scattering
- Inputs: aerosol optical thickness (AOT), water vapor, ozone concentration
- Sources: MODIS MAIAC AOT product, OpenWeatherMap atmospheric parameters

**Selection logic:**
- Level-2 products (already corrected): Skip atmospheric correction
- Level-1 with atmospheric data available: Use 6S
- Level-1 without atmospheric data: Use DOS1

### Resampling

All bands are resampled to a common grid using bilinear interpolation:

- **Target resolution**: 30m (matching Landsat reflective bands)
- **Grid alignment**: Project-specific UTM zone or Web Mercator
- **Method**: Bilinear interpolation (preserves surface continuity)
- **Sentinel-2 10m bands**: Resampled to 30m (degradation) or kept at 10m if specified
- **Thermal bands (100m)**: Resampled to 30m using cubic convolution for LST computation

### Normalization

Feature-wise z-score normalization is applied during feature engineering (not at raster level):

```
z = (x - mu) / sigma
```

Where mu and sigma are computed from the training dataset and persisted for inference.

### Mosaicking

Multiple overlapping scenes are mosaicked using:
1. **Seamline generation**: Cost-function based on NDVI gradient (minimizes visible seams)
2. **Feathering**: Weighted averaging within 500m of seamline
3. **Priority**: Most recent scene (or least cloud cover) for overlap regions
4. **Blend method**: Linear blending for smooth transitions

---

## Spectral Indices

All indices are computed per-pixel on the preprocessed, cloud-masked raster stack.

### NDVI — Normalized Difference Vegetation Index

**Formula:**
```
NDVI = (NIR - Red) / (NIR + Red)
```

**Range:** -1 to +1. Values > 0.3 indicate vegetation; < 0 indicates water/bare soil.

**Rationale:** Most widely used vegetation index. Chlorophyll in plants strongly absorbs red light and reflects NIR. Used for emissivity estimation (NDVI threshold method), land cover classification, and as a key ML feature.

### NDWI — Normalized Difference Water Index

**Formula:**
```
NDWI = (Green - NIR) / (Green + NIR)
```

**Range:** -1 to +1. Values > 0 indicate water bodies.

**Rationale:** Maximizes reflectance of water in green wavelengths and minimizes in NIR. Used for water body delineation and as a feature for UHI prediction (water bodies have cooling effect).

### NDBI — Normalized Difference Built-up Index

**Formula:**
```
NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)
```

**Range:** -1 to +1. Values > 0 indicate built-up areas.

**Rationale:** Built-up areas have higher SWIR reflectance than NIR reflectance. Used to identify urban/built-up pixels and as a primary predictor of UHI intensity.

### NBRI — Normalized Burn Ratio Index

**Formula:**
```
NBRI = (SWIR1 - NIR) / (SWIR1 + NIR)
```

**Range:** -1 to +1. Alternative formulation used for burn scar mapping; adapted in this platform as an additional built-up/barren index.

**Note:** NBRI and NDBI share the same mathematical formulation but differ in application context.

### UI — Urban Index

**Formula:**
```
UI = (SWIR2 - NIR) / (SWIR2 + NIR)
```

**Range:** -1 to +1. Higher values indicate urban surfaces.

**Rationale:** Uses SWIR2 band (2.11-2.29 um) which has stronger separation between urban and vegetated surfaces than SWIR1.

### BSI — Bare Soil Index

**Formula:**
```
BSI = ((Red + SWIR1) - (NIR + Blue)) / ((Red + SWIR1) + (NIR + Blue))
```

**Range:** -1 to +1. Higher values indicate bare soil.

**Rationale:** Captures bare soil by combining the inverse relationship between soil reflectance (high in Red/SWIR, low in NIR/Blue). Used to distinguish bare soil from built-up and vegetated areas.

---

## Land Surface Temperature (LST)

### Mono-Window Algorithm (Qin et al., 2001)

Used for single thermal band sensors (Landsat 8 Band 10, Landsat 9 Band 10):

```
LST = Tb / [1 + (lambda * Tb / rho) * ln(epsilon)]
```

Where:
- `Tb` = Brightness temperature (K) from thermal band radiance
- `lambda` = Effective wavelength of thermal band (10.9 um for Band 10)
- `rho = h * c / sigma` = 14,387.7 um·K (Stefan-Boltzmann constant)
- `epsilon` = Land surface emissivity
- `h` = Planck's constant (6.626e-34 J·s)
- `c` = Speed of light (2.998e8 m/s)
- `sigma` = Boltzmann constant (1.381e-23 J/K)

**Brightness temperature calculation:**
```
Tb = K2 / ln(K1 / L_lambda + 1)
```
Where `K1` and `K2` are band-specific thermal constants from metadata, and `L_lambda` is the top-of-atmosphere radiance.

### Split-Window Algorithm (Sobrino et al., 2004; Jimenez-Munoz et al., 2009)

Used for sensors with two thermal bands (Landsat 8 Bands 10 + 11):

```
LST = Tb10 + 1.378 * (Tb10 - Tb11) + 0.183 * (Tb10 - Tb11)^2 + 0.268 + (1 - epsilon) * (-0.644 * (Tb10 - Tb11) + 0.445)
```

Where `epsilon` is the mean emissivity of bands 10 and 11.

**Advantages:** Atmospheric effects are partially canceled by the differential absorption between two thermal bands. Less sensitive to atmospheric water vapor uncertainty than mono-window.

### Emissivity Estimation

**NDVI Threshold Method (Sobrino et al., 2004):**

1. **NDVI < 0.2 (bare soil):** epsilon = 0.97 - 0.11 * FVC (Fractional Vegetation Cover)
2. **NDVI > 0.5 (full vegetation):** epsilon = 0.99
3. **0.2 <= NDVI <= 0.5 (mixed):** epsilon = 0.004 * FVC + 0.986

**Fractional Vegetation Cover:**
```
FVC = ((NDVI - NDVI_soil) / (NDVI_veg - NDVI_soil))^2
```
Where NDVI_soil = 0.2 and NDVI_veg = 0.5 (scene-adaptive percentiles may be used).

**Classification-based emissivity:** For pixels with known land cover (from supervised classification or existing land cover products), class-specific emissivity values are assigned (water: 0.991, urban: 0.970, forest: 0.985, soil: 0.975).

### Atmospheric Correction

**Radiative Transfer Equation (RTE) method:**
```
L_lambda = [epsilon * B(LST) + (1 - epsilon) * L_atm_down] * tau + L_atm_up
```
Where:
- `B(LST)` = Planck's law radiance at surface temperature
- `L_atm_down` = Downwelling atmospheric radiance
- `L_atm_up` = Upwelling atmospheric radiance
- `tau` = Atmospheric transmissivity

Atmospheric parameters are obtained from:
- MODIS MOD07/MYD07 atmospheric profile products
- NCEP/NCAR Reanalysis data
- OpenWeatherMap API (for local meteorological data)

---

## Urban Heat Island Detection

### LST Threshold Method

The simplest and most widely used UHI detection approach:

```
UHI_intensity = LST_urban - LST_rural
```

**Severity classification:**
| Severity | Criteria | Color |
|----------|----------|-------|
| Low | LST > mean + 0.5*std | Green |
| Moderate | LST > mean + 1.0*std | Yellow |
| High | LST > mean + 1.5*std | Orange |
| Extreme | LST > mean + 2.0*std | Red |

The mean and standard deviation are computed over the entire study area, or separately over urban/rural zones for normalized comparison.

### Urban-Rural Gradient Analysis

A series of concentric buffer zones are created from the city center outward. Mean LST is computed for each buffer and plotted as a function of distance from center. The UHI effect is characterized by:

1. **Magnitude**: Maximum temperature difference between urban core and rural surroundings
2. **Extent**: Distance at which urban-rural temperature difference falls below 1°C
3. **Intensity**: Area-weighted LST anomaly relative to rural baseline

### Hotspot Clustering (DBSCAN)

Density-Based Spatial Clustering of Applications with Noise identifies contiguous hotspot regions:

**Parameters:**
- `eps` (neighborhood radius): 500m (configurable)
- `min_samples`: 5 pixels (configurable)
- Distance metric: Haversine (geodesic) distance on lat/lon coordinates

**Output:** Each hotspot cluster is assigned:
- Unique cluster ID
- Centroid (lat, lon)
- Area (hectares)
- Mean, max, and range of LST within cluster
- Severity category
- Risk score (normalized 0-1 combination of temperature anomaly and area)

### Feature Engineering for ML

The 17 extracted geo-features:

| # | Feature | Description |
|---|---------|-------------|
| 1 | NDVI_mean | Mean NDVI within boundary |
| 2 | NDWI_mean | Mean NDWI within boundary |
| 3 | NDBI_mean | Mean NDBI within boundary |
| 4 | NBRI_mean | Mean NBRI within boundary |
| 5 | UI_mean | Mean Urban Index |
| 6 | BSI_mean | Mean Bare Soil Index |
| 7 | LST_mean | Mean Land Surface Temperature |
| 8 | LST_std | LST standard deviation (thermal variability) |
| 9 | LST_max - LST_min | LST range within boundary |
| 10 | Elevation_mean | Mean elevation from SRTM/DEM |
| 11 | Elevation_std | Elevation variability |
| 12 | Building_fraction | Fraction of built-up area |
| 13 | Vegetation_fraction | Fraction of vegetated area |
| 14 | Water_fraction | Fraction of water bodies |
| 15 | Albedo_mean | Mean surface albedo |
| 16 | Population_density | Population density (if available) |
| 17 | Distance_water | Minimum distance to water body |

Features are extracted per grid cell, administrative boundary, or hexagonal tessellation cell.

---

## Machine Learning Models

### Supported Models

| Model | Library | Type | Strengths |
|-------|---------|------|-----------|
| Random Forest | scikit-learn | Ensemble tree | Robust to outliers, feature importance built-in |
| XGBoost | xgboost | Gradient boosted trees | State-of-the-art tabular data, handles missing values |
| LightGBM | lightgbm | Gradient boosted trees | Faster training, lower memory, leaf-wise growth |
| CatBoost | catboost | Gradient boosted trees | Native categorical support, ordered boosting |
| SVM (RBF) | scikit-learn | Kernel method | Effective in high-dimensional spaces |
| KNN | scikit-learn | Instance-based | Simple, non-parametric, locally adaptive |
| MLP | scikit-learn | Neural network | Learns complex non-linear patterns |
| Gradient Boosting | scikit-learn | Gradient boosted trees | Classic implementation, robust defaults |

### Ensemble Methods

**Voting Ensemble:** Combines predictions from multiple models via:
- **Soft voting**: Weighted average of predicted probabilities (weights optimized on validation set)
- **Hard voting**: Majority vote across model predictions

**Stacking Ensemble:** Meta-learner (Logistic Regression) trained on base model predictions as features.

### Cross-Validation Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| k-Fold (k=5 or 10) | Random split into k folds | General purpose |
| Stratified k-Fold | Preserves class distribution per fold | Imbalanced classification |
| Spatial k-Fold | Geographic clustering-based split | Prevents spatial autocorrelation leakage |
| Temporal k-Fold | Chronological split for time series | Forecasting validation |

### Hyperparameter Search

| Method | Library | Description |
|--------|---------|-------------|
| GridSearchCV | scikit-learn | Exhaustive search over parameter grid |
| RandomizedSearchCV | scikit-learn | Random sampling from parameter distributions |
| Optuna | optuna | Bayesian optimization with pruning |

### Drift Detection

**Data drift:** Population stability index (PSI) comparing feature distributions between training and inference datasets.

**Concept drift:** Model accuracy monitoring on streaming predictions with ground-truth labels (when available).

**Model drift:** Performance degradation alerts triggered when accuracy drops below 0.85 threshold.

---

## Explainable AI (XAI)

### SHAP (SHapley Additive exPlanations)

**SHAP TreeExplainer:** Model-specific, exact computation for tree-based models (Random Forest, XGBoost, LightGBM, CatBoost, Gradient Boosting). Uses TreeSHAP algorithm (Lundberg et al., 2020) for O(n log n) computation.

**SHAP KernelExplainer:** Model-agnostic, uses weighted linear regression. Fallback for non-tree models (SVM, KNN, MLP). Uses background dataset of 100 samples from training data.

### Permutation Importance

Feature importance measured as increase in prediction error when feature values are randomly shuffled (Breiman, 2001). Repeated 5 times for stability. Reported as mean importance ± standard deviation.

### Counterfactual Explanations

Minimal feature changes needed to change a prediction outcome:

```
counterfactual = argmin||x - x'||_1 subject to f(x') != f(x)
```

Generated via:
1. **Random search**: Sample random perturbations, filter those that flip prediction
2. **Optimization-based**: Gradient descent on feature values to minimize prediction change while crossing decision boundary

### Visualization Types

1. **SHAP summary plot** — Beeswarm of SHAP values per feature
2. **SHAP bar plot** — Mean absolute SHAP value per feature
3. **SHAP dependence plot** — SHAP value vs. feature value for a single feature
4. **Feature importance bar chart** — Permutation importance with error bars
5. **Decision tree visualization** — First 3 levels of tree structure
6. **Counterfactual comparison** — Before/after feature values
7. **Confidence gauge** — Prediction confidence display

---

## Recommendation Engine

### Mitigation Strategies

| Strategy | Cost/HA | Temp Reduction | CO2 Sequestration | Priority |
|----------|---------|----------------|-------------------|----------|
| Tree Plantation | ₹5,00,000 | 2.5°C | 15 tCO2e/ha/yr | High |
| Cool Roof | ₹3,00,000 | 1.5°C | 2 tCO2e/ha/yr | Medium |
| Green Roof | ₹8,00,000 | 2.0°C | 5 tCO2e/ha/yr | Medium |
| Reflective Pavement | ₹4,00,000 | 1.8°C | 0 tCO2e/ha/yr | Medium |
| Water Body Restoration | ₹6,00,000 | 3.0°C | 3 tCO2e/ha/yr | High |
| Urban Green Space | ₹2,00,000 | 1.2°C | 10 tCO2e/ha/yr | High |

### Scoring Formula

Overall score is a weighted combination:
```
Score = 0.30 * CE + 0.25 * Feasibility + 0.20 * Temp + 0.15 * Priority + 0.10 * CO2
```

Where:
- CE = Cost-effectiveness (PV carbon benefit / net cost × 1e6)
- Feasibility = Based on area, cost, and landcover constraints
- Temp = Temperature reduction score (normalized)
- Priority = Priority level weight
- CO2 = Carbon sequestration score

### Budget Optimization (0/1 Knapsack)

**Objective:** Maximize total temperature reduction + carbon benefit subject to budget constraint.

**Algorithm:** Integer dynamic programming with cost scaling. Items exceeding budget are filtered before knapsack computation. Greedy fallback available for large problem instances.

---

## Scenario Simulation

### Templates

Seven built-in scenario templates: tree_plantation, cool_roof, green_roof, reflective_pavement, water_body_restoration, urban_green_space, combined_mitigation.

Each template defines feature modifiers (op: add/mul/set/scale_to + value + min/max bounds) applied to the feature vector before prediction.

### Monte Carlo Simulation

Multiple simulations (configurable: default 1000) with random perturbations to account for uncertainty. Results include confidence intervals and percentile-based risk assessment.

### Comparison Ranking

Scenarios are ranked by user-selected metric (cost_effectiveness, temp_reduction, total_cost, co2_reduction). Reports include best-case, worst-case, and median outcomes for each scenario.

---

## Validation Methodology

1. **Hold-out validation**: 80/20 train-test split for final model evaluation
2. **Spatial cross-validation**: Geographic folds prevent spatial autocorrelation leakage
3. **Temporal backtesting**: Models tested on historical data not seen during training
4. **Uncertainty quantification**: Prediction intervals via quantile regression and Monte Carlo dropout
5. **Ground truth validation**: LST comparisons with in-situ weather station data where available

---

## Scientific Assumptions

1. Planck's law approximation for thermal radiance conversion
2. Uniform emissivity within pixel (sub-pixel heterogeneity ignored)
3. Atmospheric profile assumed spatially uniform over scene (for single-scene corrections)
4. Temporal stationarity for ML forecasting (future patterns similar to historical)
5. Linear additivity of mitigation strategy effects in scenarios
6. Cost data based on Indian urban context (generalization requires local calibration)

---

## Known Limitations

1. Thermal band spatial resolution (100m Landsat, resampled to 30m)
2. Cloud cover limits usable scene availability (especially monsoon season)
3. Urban canyon effects not captured (3D urban geometry)
4. Anthropogenic heat flux not directly measured
5. ML models trained on Indian cities; transferability to other climates requires retraining
6. Recommendation costs are India-specific estimates

---

## Future Improvements

1. High-resolution thermal data from ECOSTRESS (70m) or thermal sharpening with Sentinel-2
2. SAR (Sentinel-1) integration for all-weather monitoring
3. 3D urban morphology from LiDAR or stereo imagery
4. Real-time data assimilation from IoT sensor networks
5. City-scale microclimate modeling (urban canopy models)
6. Integrated carbon credit estimation and trading platform
