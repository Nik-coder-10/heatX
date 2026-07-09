# Urban Heat Mitigation Platform — User Guide

**Version 1.0.0** | July 2026

---

## Table of Contents

1. [Introduction to the Platform](#1-introduction-to-the-platform)
2. [Getting Started](#2-getting-started)
3. [Dashboard Overview](#3-dashboard-overview)
4. [Uploading Satellite Imagery](#4-uploading-satellite-imagery)
5. [Running Preprocessing](#5-running-preprocessing)
6. [Viewing Spectral Indices](#6-viewing-spectral-indices)
7. [Viewing LST Maps](#7-viewing-lst-maps)
8. [Running UHI Detection](#8-running-uhi-detection)
9. [Making Predictions](#9-making-predictions)
10. [Viewing Recommendations](#10-viewing-recommendations)
11. [Running Scenario Simulations](#11-running-scenario-simulations)
12. [Model Explainability](#12-model-explainability)
13. [Generating Reports](#13-generating-reports)
14. [Admin Features](#14-admin-features)
15. [Best Practices for Urban Planners](#15-best-practices-for-urban-planners)
16. [Troubleshooting Common User Issues](#16-troubleshooting-common-user-issues)
17. [Glossary of Terms](#17-glossary-of-terms)

---

## 1. Introduction to the Platform

The **Urban Heat Mitigation Platform** (UHMP) is an AI-powered decision-support system designed for urban planners, environmental scientists, and policymakers. It combines satellite remote sensing, machine learning, and geospatial analysis to detect, predict, and mitigate the Urban Heat Island (UHI) effect.

### Key Capabilities

| Capability | Description |
|---|---|
| **Satellite Ingestion** | Process Landsat 8/9, Sentinel-2, and custom imagery |
| **Spectral Indices** | Compute NDVI, NDBI, NDWI, MNDWI, UI, BSI, and more |
| **Land Surface Temperature** | Generate LST maps at 30m (Landsat) or 10m (Sentinel-2) resolution |
| **UHI Detection** | Identify heat hotspots with severity classification (Low/Moderate/High/Extreme) |
| **Predictive Modeling** | XGBoost, LightGBM, CatBoost, and ensemble models for future temperature prediction |
| **Mitigation Recommendations** | Budget-optimized intervention strategies with cost-benefit analysis |
| **Scenario Simulation** | What-if analysis for green roofs, cool pavements, tree canopies, and albedo changes |
| **Explainable AI** | SHAP values, feature importance plots, and counterfactual explanations |
| **Reporting** | PDF reports, CSV exports, and GeoJSON feature exports |

### Architecture Overview

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐
│  React 19   │◄──►│  FastAPI      │◄──►│  PostgreSQL   │
│  TypeScript │    │  (Python 3.11)│    │  + PostGIS    │
│  MapLibre   │    │  Celery Tasks │    │  + Redis      │
│  ECharts    │    │  ML Pipeline  │    │  + MinIO/S3   │
└─────────────┘    └──────────────┘    └───────────────┘
```

---

## 2. Getting Started

### 2.1 Accessing the Web Interface

Open your web browser and navigate to the platform URL provided by your administrator:

- **Local development:** `http://localhost:5173`
- **Production deployment:** `https://uhmp.yourcity.gov`

### 2.2 Login

1. Click the **Sign In** button in the top-right corner.
2. Enter your email address and password.
3. Click **Sign In**.

> **First-time users:** If you received an invitation email, click the activation link, set your password, and log in. If you did not receive an invitation, contact your system administrator.

### 2.3 Password Reset

1. On the login page, click **Forgot Password**.
2. Enter your registered email address.
3. Check your inbox for a password reset link (valid for 60 minutes).
4. Follow the link to set a new password.

### 2.4 Logout

Click your profile avatar in the top-right corner and select **Sign Out**.

### 2.5 User Roles

| Role | Description |
|---|---|
| **Viewer** | Can view dashboards, reports, and exports. Cannot upload data or run processing. |
| **Analyst** | Can upload data, run processing, generate predictions, and export reports. |
| **Administrator** | Full access including user management, system configuration, and billing. |

---

## 3. Dashboard Overview

The dashboard is the central hub after login. It provides a high-level summary of your urban heat island analysis.

### 3.1 Stat Cards (4 Cards)

At the top of the dashboard, four stat cards display aggregate metrics:

| Card | Description |
|---|---|
| **Mean LST (°C)** | Average land surface temperature across the study area for the latest available date |
| **Hotspot Area (km²)** | Total area classified as UHI hotspot (High + Extreme severity) |
| **Population Exposed** | Estimated population living in hotspot areas (derived from gridded population data) |
| **Mitigation Potential** | Estimated temperature reduction achievable with recommended interventions (weighted score) |

Each card shows:
- The current value with unit
- A percentage change vs. the previous time period (green for improvement, red for deterioration)
- A sparkline trend for the last 6 data points

### 3.2 Trend Charts

Located below the stat cards:

- **LST Trend:** Line chart of mean LST over time, with optional overlay of air temperature from local weather stations.
- **Hotspot Area Trend:** Bar chart showing hotspot area evolution across time periods.
- **Spectral Index Trends:** Toggleable series for NDVI (vegetation), NDBI (built-up), NDWI (water) over time.

Use the **Date Range Selector** (top-right of chart area) to filter by custom date ranges.

### 3.3 Base Map

The interactive map (powered by MapLibre GL) shows:

- **Base layer:** Satellite or street map tiles (toggleable).
- **LST overlay:** Thermal layer rendered with a冷暖 (blue-to-red) color ramp. Opacity slider available.
- **Hotspot polygons:** Red/orange boundaries outlining detected UHI hotspots.
- **Sample points:** Click on any point to see a popup with LST value, spectral indices, and severity class.

**Mouse controls:**
- Left-click drag: Pan
- Scroll wheel: Zoom
- Right-click drag: Rotate (3D mode)
- Click feature: Show popup with metadata

---

## 4. Uploading Satellite Imagery

### 4.1 Supported Formats

| Format | Extensions | Max File Size |
|---|---|---|
| GeoTIFF | `.tif`, `.tiff` | 2 GB |
| Cloud Optimized GeoTIFF | `.tif` (COG) | 2 GB |
| NetCDF | `.nc` | 1 GB |
| HDF5 | `.h5`, `.hdf5` | 1 GB |
| JPEG2000 | `.jp2` | 500 MB |
| ZIP archive of GeoTIFFs | `.zip` | 4 GB |

### 4.2 Supported Sensors

- **Landsat 8/9** (Collection 2, Level 1TP or Level 2)
- **Sentinel-2** (L1C or L2A)
- **MODIS** (MOD11, MYD11)
- **Custom UAV/Drone** imagery (requires georeferencing)

### 4.3 Upload via Drag-and-Drop

1. Navigate to **Data** → **Upload** in the sidebar.
2. Drag one or more files from your file explorer onto the dashed upload zone.
3. Alternatively, click **Browse Files** to open a file picker.
4. As files are added, they appear in the upload queue with:
   - Filename and size
   - Upload progress bar (percentage)
   - Estimated time remaining
5. After all files are queued, click **Start Upload**.

### 4.4 Upload via Remote Fetch

1. Click the **Remote URL** tab.
2. Enter the direct download URL of the satellite scene (e.g., a USGS EarthExplorer download link).
3. Click **Fetch**. The platform will download the scene server-side.

### 4.5 Upload Progress Monitoring

During upload, the **Upload Queue** panel shows:

- **Status indicators:** Queued → Uploading → Processing → Complete / Failed
- **Per-file progress:** Percentage and throughput (MB/s)
- **Overall progress:** Aggregate for multi-file batches
- **Cancel button:** Abort an in-progress upload
- **Retry button:** Re-attempt a failed upload

### 4.6 Data Validation

Upon upload completion, the platform automatically validates:

- Spatial reference system (must be WGS84 / EPSG:4326)
- Spatial extent (must overlap with any defined study area)
- Band count and order (minimum thermal band required for LST)
- Radiometric calibration metadata
- Cloud cover percentage (if available in metadata)

Failed validations trigger a notification with specific error messages.

---

## 5. Running Preprocessing

### 5.1 Preprocessing Pipeline

After imagery is uploaded, it must be preprocessed before analysis. The preprocessing pipeline includes:

1. **Cloud Masking** — Identifies and removes cloud pixels.
2. **Atmospheric Correction** — Converts top-of-atmosphere (TOA) reflectance to surface reflectance.
3. **Resampling** — Aligns all bands to a common spatial resolution.
4. **Reprojection** — Ensures consistent CRS (WGS84 / EPSG:4326).
5. **Tile Registration** — Splits large scenes into 256×256 tiles for efficient processing.

### 5.2 Starting Preprocessing

1. Navigate to **Data** → **Scenes**.
2. Find the scene you uploaded (status will show "Pending").
3. Click the scene row to open the detail panel.
4. Click **Run Preprocessing**.

### 5.3 Cloud Masking Options

| Option | Description | Default |
|---|---|---|
| **Method** | Fmask (Landsat), Sen2Cor (Sentinel-2), or custom threshold | Auto-detect based on sensor |
| **Cloud Confidence** | Threshold for cloud pixel removal (0–100) | 20 |
| **Cirrus Removal** | Whether to mask cirrus clouds | Enabled |
| **Shadow Removal** | Whether to mask cloud shadows | Enabled |
| **Smoothing** | Apply a 3×3 median filter after masking | Disabled |

### 5.4 Atmospheric Correction Options

| Option | Description | Default |
|---|---|---|
| **Method** | 6SV (Second Simulation of a Satellite Signal in the Solar Spectrum) or DOS (Dark Object Subtraction) | 6SV |
| **Aerosol Model** | Rural, Urban, Maritime, Desert | Urban |
| **Water Vapor** | Automatic (from metadata) or manual (g/cm²) | Automatic |
| **Ozone** | Automatic (from metadata) or manual (cm-atm) | Automatic |

### 5.5 Monitoring Preprocessing

The **Processing Queue** panel shows:

- **Current stage:** Cloud Masking → Atmospheric Correction → Resampling → Reprojection → Tiling
- **Per-stage progress:** Progress bar for each stage
- **Log output:** Real-time processing logs with timestamps
- **Estimated time remaining:** Total and per-stage ETA

### 5.6 Preprocessing Results

Upon completion:

- The scene status changes to **Processed**.
- A thumbnail preview is generated.
- Basic statistics (min, max, mean, std) are computed for each band.
- The scene is ready for spectral index computation and LST retrieval.

---

## 6. Viewing Spectral Indices

### 6.1 Available Spectral Indices

| Index | Formula | Purpose |
|---|---|---|
| **NDVI** | (NIR - Red) / (NIR + Red) | Normalized Difference Vegetation Index — vegetation health/density |
| **NDBI** | (SWIR1 - NIR) / (SWIR1 + NIR) | Normalized Difference Built-up Index — urban density |
| **NDWI** | (Green - NIR) / (Green + NIR) | Normalized Difference Water Index — water bodies |
| **MNDWI** | (Green - SWIR1) / (Green + SWIR1) | Modified NDWI — improved water detection |
| **UI** | (SWIR2 - NIR) / (SWIR2 + NIR) | Urban Index — built-up area identification |
| **BSI** | ((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue)) | Bare Soil Index — bare/sparse soil |
| **SAVI** | (NIR - Red) / (NIR + Red + L) × (1 + L) | Soil-Adjusted Vegetation Index — vegetation with soil correction |
| **EVI** | 2.5 × ((NIR - Red) / (NIR + 6 × Red - 7.5 × Blue + 1)) | Enhanced Vegetation Index — improved sensitivity in high-biomass areas |
| **BI** | sqrt((Red² + NIR² + SWIR1²) / 3) | Brightness Index — overall surface brightness |
| **NDMI** | (NIR - SWIR1) / (NIR + SWIR1) | Normalized Difference Moisture Index — vegetation moisture content |

### 6.2 Computing Indices

1. Navigate to **Analysis** → **Spectral Indices**.
2. Select one or more indices from the list (checkboxes).
3. Click **Compute**.
4. The platform queues the computation jobs. Progress is shown in the processing queue.
5. When complete, each index is available as a raster overlay on the map.

### 6.3 Interpreting Color Maps

Each index has a default color map optimized for interpretation:

| Index | Color Map | Value Range | Interpretation |
|---|---|---|---|
| **NDVI** | Red-Yellow-Green | -1 to +1 | Green = dense vegetation, Red = no vegetation |
| **NDBI** | Blue-White-Red | -1 to +1 | Red = built-up, Blue = vegetated/water |
| **NDWI** | Brown-Blue-White | -1 to +1 | Blue = water, Brown = dry land |
| **MNDWI** | Brown-Blue-White | -1 to +1 | Blue = water (better separation than NDWI) |
| **BSI** | Green-Yellow-Brown | -1 to +1 | Brown = bare soil, Green = vegetation/water |

**Color map controls:**
- **Opacity slider:** Adjust overlay transparency (0–100%)
- **Min/Max sliders:** Stretch the color ramp to emphasize specific value ranges
- **Palette picker:** Choose from 8 built-in color palettes
- **Reverse:** Flip the color ramp direction

### 6.4 Pixel Value Inspection

Click any point on the map to see the index value at that pixel in the popup. Use the **Point Sampling Tool** (crosshair icon) to collect multiple sample points and export them as CSV.

---

## 7. Viewing LST Maps

### 7.1 Computing Land Surface Temperature

LST is computed automatically after preprocessing using the split-window algorithm (Landsat) or the single-channel algorithm (Sentinel-2). To view:

1. Navigate to **Analysis** → **LST**.
2. Select the scene(s) to process.
3. **LST Method:** Single-Channel or Split-Window.
4. **Emissivity Source:** NDVI-based, ASTER GED, or custom.
5. Click **Compute LST**.

### 7.2 Temperature Scale

The LST map uses a冷暖 (blue-to-red) diverging color ramp:

| Color | Range | Interpretation |
|---|---|---|
| Dark Blue | 20–25 °C | Water bodies, dense vegetation |
| Light Blue | 25–30 °C | Parks, irrigated areas |
| Green | 30–35 °C | Suburban, mixed land cover |
| Yellow | 35–40 °C | Low-density urban |
| Orange | 40–45 °C | Dense urban, industrial |
| Red | 45–50 °C | Hotspots — bare soil, concrete, asphalt |
| Dark Red | 50+ °C | Extreme hotspots |

The color bar legend is displayed in the bottom-left corner of the map and updates dynamically when you adjust the min/max stretch.

### 7.3 Histogram Interpretation

The LST histogram (shown below the map) displays:

- **X-axis:** Temperature in °C (or °F, toggleable).
- **Y-axis:** Pixel count (frequency).
- **Mean line:** Dashed vertical line at the mean temperature.
- **Median line:** Dotted vertical line at the median temperature.
- **Standard deviation:** Shaded region ±1σ around the mean.
- **Threshold lines:** Optional display of UHI severity thresholds (see Section 8).

**Histogram controls:**
- **Zoom:** Click and drag to zoom into a temperature range.
- **Reset:** Double-click to reset the zoom.
- **Export:** Click the download icon to export the histogram as PNG or SVG.

### 7.4 Customizing the Display

- **Unit toggle:** Switch between °C and °F.
- **Color ramp:** Choose from 12 scientific color palettes (viridis, magma, inferno, SPL, etc.).
- **Stretch type:** Linear, Equalization, or Standard Deviation.
- **Transparency:** Slider to blend LST with the base map.

---

## 8. Running UHI Detection

### 8.1 What is UHI Detection?

UHI detection identifies urban heat hotspots by comparing LST values against a reference baseline (typically rural/vegetated areas). The platform uses statistical thresholding and spatial clustering to delineate hotspot polygons.

### 8.2 Running Detection

1. Navigate to **Analysis** → **UHI Detection**.
2. Select the LST scene (processed in Section 7).
3. Configure parameters:

| Parameter | Description | Default |
|---|---|---|
| **Threshold Method** | Standard deviation, Percentile, or Absolute | Standard deviation |
| **Threshold Value** | Multiplier or percentile cutoff | 1.5 (std dev) |
| **Minimum Cluster Size** | Minimum contiguous pixels for a hotspot | 10 |
| **Buffer Distance** | Buffer around hotspot polygons (meters) | 0 |
| **Reference Area** | Rural/vegetated area for baseline | Auto-detect |

4. Click **Run Detection**.

### 8.3 Hotspot Identification

Results are displayed as polygon overlays on the map:

- **Polygon color** indicates severity (see below).
- **Hover** over a polygon to see: area (km²), mean LST, max LST, mean NDVI.
- **Click** a polygon to highlight it and show detailed statistics in the side panel.

### 8.4 Severity Classification

| Severity | Color | Color Hex | Criteria | Recommendation Priority |
|---|---|---|---|---|
| **Low** | Light Yellow | #FDE68A | LST > 1 SD above rural mean | Monitor |
| **Moderate** | Orange | #F97316 | LST > 1.5 SD above rural mean | Consider intervention |
| **High** | Red | #EF4444 | LST > 2 SD above rural mean | Prioritize intervention |
| **Extreme** | Dark Red | #991B1B | LST > 3 SD above rural mean | Immediate action |

### 8.5 Results Summary Panel

The side panel displays:

- **Total hotspot area** by severity class (km² and % of study area)
- **Population exposure** estimate per severity class
- **Land cover breakdown** within hotspots (from spectral indices)
- **Top 10 hotspots** ranked by area × severity score
- **Export buttons** for GeoJSON and CSV

---

## 9. Making Predictions

### 9.1 Prediction Models

The platform includes four ML model types for predicting future LST and UHI intensity:

| Model | Description | Training Speed | Accuracy | Interpretability |
|---|---|---|---|---|
| **XGBoost** | Gradient-boosted decision trees | Fast | High | Medium |
| **LightGBM** | Leaf-wise gradient boosting | Very fast | High | Medium |
| **CatBoost** | Ordered boosting with categorical support | Moderate | Very high | Medium |
| **Ensemble** | Stacked ensemble of all three | Slow | Highest | Low |

### 9.2 Input Features

Predictions use the following feature set:

| Feature | Source | Description |
|---|---|---|
| Spectral Indices | Computed from satellite | NDVI, NDBI, NDWI, BSI, SAVI |
| LST Historical | Satellite LST | Trailing 12-month LST values |
| Albedo | Satellite or default | Surface albedo (0–1) |
| Impervious Surface | Derived from NDBI | % impervious cover per pixel |
| Vegetation Cover | Derived from NDVI | % vegetation cover per pixel |
| Population Density | Census data | Persons per km² |
| Building Height | LiDAR or OpenStreetMap | Mean building height (m) |
| Road Density | OpenStreetMap | Road length per km² |

### 9.3 Running Inference

1. Navigate to **Predict** → **Run Prediction**.
2. **Select Model Type:** XGBoost, LightGBM, CatBoost, or Ensemble.
3. **Select Study Area:** Choose a defined boundary or draw a custom area.
4. **Prediction Target:**
   - Mean LST (°C) — predicted average temperature
   - Hotspot Probability (%) — probability of becoming a hotspot
   - UHI Intensity (°C) — predicted UHI effect magnitude
5. **Time Horizon:** Next 3 months, 6 months, 12 months, or 24 months.
6. **Scenario:** "Business as usual" (default) or upload custom scenario parameters.
7. Click **Run Prediction**.

### 9.4 Interpreting Results

The prediction results page shows:

- **Prediction Map:** Raster overlay of predicted values on the map.
- **Confidence Map:** Optional overlay showing prediction confidence intervals.
- **Summary Statistics:**
  - Predicted mean LST (°C)
  - Predicted hotspot area (km²)
  - Predicted population exposed
  - Change compared to current baseline
- **Feature Importance Chart:** Bar chart showing which features most influenced the prediction (see Section 12).
- **Uncertainty Range:** Lower and upper bounds at 95% confidence.

### 9.5 Comparison with Current Data

Toggle **Overlay Current Data** to visually compare the prediction against the most recent observed LST map. The difference map (Predicted − Observed) highlights areas of projected warming or cooling.

---

## 10. Viewing Recommendations

### 10.1 How Recommendations Work

The platform uses a multi-objective optimization engine to recommend UHI mitigation strategies. It considers:

- **Cost:** Implementation and maintenance costs per strategy per unit area.
- **Impact:** Expected temperature reduction per strategy per unit area.
- **Co-benefits:** Environmental and social co-benefits (air quality, stormwater, health).
- **Budget:** User-defined total budget constraint.

### 10.2 Available Mitigation Strategies

| Strategy | Cost/m²/yr | Temp Reduction | Co-benefits |
|---|---|---|---|
| **Green Roofs** | $15–40 | 2–5 °C | Stormwater, air quality, biodiversity |
| **Cool Pavements** | $5–15 | 1–3 °C | Reduced runoff, durability |
| **Tree Canopy** | $8–25 | 3–8 °C | Shade, air quality, carbon sequestration |
| **Urban Parks** | $20–50 | 2–6 °C | Recreation, biodiversity, social |
| **Cool Roofs** | $3–10 | 1–4 °C | Energy savings, reduced HVAC load |
| **Green Facades** | $10–30 | 1–3 °C | Aesthetic, insulation, biodiversity |
| **Water Features** | $25–60 | 2–5 °C | Recreation, microclimate |
| **Albedo Increase** | $2–8 | 1–2 °C | Low cost, wide applicability |

### 10.3 Generating Recommendations

1. Navigate to **Recommendations**.
2. Enter your **Total Budget** (USD).
3. **Select Study Area:** Choose an existing boundary or draw on the map.
4. **Weighting Preferences** (sliders):
   - Temperature Reduction
   - Cost Efficiency
   - Co-benefits
   - Implementation Speed
5. Click **Generate Recommendations**.

### 10.4 Reviewing Options

The recommendations page displays:

- **Optimization Summary:**
  - Total expected temperature reduction (°C)
  - Total area treated (km²)
  - Cost breakdown by strategy
  - Cost per °C reduction
- **Strategy Allocation Chart:** Stacked bar chart showing area allocation across strategies.
- **Map Overlay:** Colored polygons showing recommended intervention zones.
- **Strategy Details Table:**

| Strategy | Area (ha) | Cost | Temp Reduction | Co-benefit Score | Priority |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | High/Med/Low |

### 10.5 Cost Analysis

The cost analysis panel includes:

- **Total investment:** Sum of all recommended strategy costs.
- **Cost per capita:** Total cost divided by exposed population.
- **Cost per °C:** Total cost per degree of average temperature reduction.
- **Annual maintenance:** Recurring costs for strategy upkeep.
- **Break-even period:** Years until benefits (energy savings, health, productivity) exceed costs.
- **Sensitivity analysis:** What-if sliders for cost variation (±25%).

---

## 11. Running Scenario Simulations

### 11.1 What are Scenario Simulations?

Scenario simulations allow you to model "what-if" situations — e.g., "What if we install green roofs on 30% of buildings?" or "What if we increase albedo by 0.2 across the downtown core?"

### 11.2 Available Scenario Templates

| Template | Description | Adjustable Parameters |
|---|---|---|
| **Green Roof Expansion** | Simulate widespread green roof adoption | Coverage (%), Building type filter, Growth period |
| **Cool Pavement Retrofit** | Replace conventional pavements with cool materials | Coverage (%), Road type filter, Albedo target |
| **Urban Tree Canopy** | Increase tree canopy coverage | Coverage (%), Species mix, Maturity period |
| **Albedo Modification** | Adjust surface albedo across land cover types | Albedo delta per LC type, Area constraint |
| **Combined Strategy** | Mix of all strategies with allocation weights | Budget, Strategy weights, Phasing |
| **Climate Adaptation** | Model under future climate scenarios | RCP scenario (4.5/8.5), Time horizon |
| **Custom** | User-defined parameter grid | Any combination of above |

### 11.3 Running a Simulation

1. Navigate to **Simulations** → **New Simulation**.
2. Select a **Template** from the list.
3. Name your simulation (e.g., "Downtown Green Roof 30%").
4. Adjust **Intensity Parameters**:
   - Use sliders, dropdowns, and number inputs as defined by the template.
   - The map preview updates in real time as you adjust parameters.
5. **Set Confidence Level:** Conservative (pessimistic), Moderate (most likely), Aggressive (optimistic).
6. Click **Run Simulation**.

### 11.4 Monitoring Simulation Progress

- Simulations run as background Celery tasks.
- The **Simulations** page shows all runs with status: Queued → Running → Complete / Failed.
- Estimated completion time is displayed.
- Live log output is available via the **View Logs** button.

### 11.5 Comparing Results

The **Scenario Comparison** view (accessible from the Simulations page) allows you to:

- **Side-by-side maps:** Compare baseline vs. simulated LST.
- **Difference map:** (Simulated − Baseline) highlighting reduction areas.
- **Statistics comparison:**

| Metric | Baseline | Simulated | Change |
|---|---|---|---|
| Mean LST | 38.2 °C | 34.7 °C | −3.5 °C |
| Hotspot Area | 12.4 km² | 6.8 km² | −45.2% |
| Population Exposed | 85,000 | 42,000 | −50.6% |

- **Export comparison report** as PDF or PNG.
- **Save simulation** as a reference scenario for future comparison.

---

## 12. Model Explainability

### 12.1 SHAP Values

SHAP (SHapley Additive exPlanations) values explain individual predictions by showing how each feature contributed to the output.

**How to use:**
1. After running a prediction (Section 9), click **Explain** → **SHAP Values**.
2. The SHAP summary plot shows:
   - **Y-axis:** Features ranked by importance.
   - **X-axis:** SHAP value (impact on model output).
   - **Color:** Feature value (red = high, blue = low).
3. Click any point to see the specific feature values and contribution breakdown.

### 12.2 Feature Importance

**Global importance** shows which features are most influential across all predictions:

- **Bar chart:** Mean absolute SHAP value per feature.
- **Gain chart:** XGBoost/LightGBM built-in feature importance (gain, cover, frequency).

**Local importance** explains a single prediction:
- **Force plot:** Waterfall chart showing feature contributions pushing the base value to the final prediction.
- **Decision plot:** Cumulative feature contributions from top to bottom.

### 12.3 Counterfactual Explanations

Counterfactuals answer the question: "What would need to change for this area to NOT be a hotspot?"

1. Click on any hotspot polygon on the map.
2. Click **Explain** → **Counterfactual**.
3. The platform computes the minimal feature changes required to reclassify the hotspot to non-hotspot:

| Feature | Current Value | Required Value | Change |
|---|---|---|---|
| NDVI | 0.12 | 0.45 | +0.33 |
| Albedo | 0.15 | 0.35 | +0.20 |
| Impervious Surface | 85% | 45% | −40% |

4. **Actionable Insight:** The counterfactual directly informs which interventions are needed (e.g., "Increase NDVI by 0.33 through tree planting").

### 12.4 Model Confidence

- **Confidence score:** 0–100% for each prediction.
- **Uncertainty decomposition:** Aleatoric (data noise) vs. Epistemic (model knowledge) uncertainty.
- **Out-of-distribution detection:** Areas where the model has not seen similar training data are flagged.

---

## 13. Generating Reports

### 13.1 Available Export Formats

| Format | Use Case | Contents |
|---|---|---|
| **PDF Report** | Stakeholder presentations, planning documents | Executive summary, maps, charts, statistics, recommendations |
| **CSV Export** | Spreadsheet analysis, further processing | Tabular data per pixel or per polygon |
| **GeoJSON Export** | GIS software (QGIS, ArcGIS, etc.) | Vector polygons with attribute tables |
| **GeoTIFF Export** | Raster analysis in GIS | Single-band or multi-band raster |
| **PNG/SVG Export** | Reports, presentations | Map screenshots, charts |

### 13.2 Generating a PDF Report

1. Navigate to **Reports** → **Generate Report**.
2. **Select Content:**
   - Executive Summary
   - Study Area Overview
   - LST Analysis
   - UHI Hotspot Map
   - Spectral Index Analysis
   - Prediction Results
   - Recommendations
   - Scenario Simulations
3. **Formatting:**
   - Include cover page (with project name, date, author)
   - Page orientation (portrait/landscape)
   - Logo upload (optional)
4. Click **Generate PDF**.

   The report is processed in the background. When complete, a download link is sent via notification and email.

### 13.3 Generating a CSV Export

1. Navigate to the data view you want to export (e.g., LST results, UHI polygons, spectral indices).
2. Click the **Export** button → **CSV**.
3. Select columns to include.
4. **Spatial Filter:** All data or current map extent only.
5. Click **Export CSV**.

### 13.4 Generating a GeoJSON Export

1. From the UHI Detection results or any polygon layer, click **Export** → **GeoJSON**.
2. Options:
   - **Coordinate System:** WGS84 (EPSG:4326) or Web Mercator (EPSG:3857).
   - **Attribute Fields:** Select which properties to include.
   - **Simplify Geometry:** Apply Ramer-Douglas-Peucker simplification (tolerance in meters).
3. Click **Export GeoJSON**.

---

## 14. Admin Features

*Requires Administrator role.*

### 14.1 User Management

1. Navigate to **Admin** → **Users**.
2. **User List:** Searchable table with columns:
   - Name, Email, Role, Status (Active/Inactive/Invited), Last Login, Created
3. **Actions per user:**
   - **Edit:** Change name, email, role.
   - **Deactivate/Activate:** Suspend or restore access.
   - **Delete:** Permanently remove user (irreversible).
4. **Invite User:** Click **Invite User**, enter email and role. An invitation email is sent automatically.

### 14.2 System Health

Navigate to **Admin** → **System Health** for a real-time overview:

| Component | Status Indicator | Details |
|---|---|---|
| API Server | Green/Yellow/Red | Uptime, requests/sec, latency p50/p95/p99 |
| Database | Green/Yellow/Red | Connection count, replication lag, query time |
| Redis | Green/Yellow/Red | Memory usage, hit rate, connected clients |
| Celery Workers | Green/Yellow/Red | Active tasks, queue depth, failure rate |
| MinIO/S3 | Green/Yellow/Red | Storage used, request rate, error rate |
| ML Models | Green/Yellow/Red | Model version, last trained, drift status |

**Alert history:** Table of recent alerts (time, severity, component, message, acknowledged status).

### 14.3 Configuration

Navigate to **Admin** → **Configuration** for runtime settings:

| Category | Editable Settings |
|---|---|
| **Processing** | Max upload size, concurrent tasks, timeout limits |
| **Maps** | Default center, default zoom, tile URL |
| **ML Models** | Active model version, retrain schedule, drift threshold |
| **Notifications** | Email sender, notification channels |
| **Security** | Session timeout, password policy, MFA enforcement |
| **Billing** | (If applicable) Pricing tiers, usage limits |

Changes take effect immediately and are persisted to the database.

### 14.4 Audit Log

Navigate to **Admin** → **Audit Log** to view:

- Timestamped log of all user actions
- Filters: Action type, user, date range
- Exportable as CSV

---

## 15. Best Practices for Urban Planners

### 15.1 Data Collection

- **Acquire multi-season imagery:** Capture at least one summer and one winter scene per year.
- **Use consistent sensors:** When doing time-series analysis, prefer the same satellite sensor to minimize cross-sensor bias.
- **Check cloud cover:** Aim for scenes with <20% cloud cover over your study area.
- **Validate with ground truth:** Deploy low-cost temperature loggers (e.g., HOBO or iButton) at 5–10 representative locations for validation.

### 15.2 Analysis Workflow

1. **Start with spectral indices** to understand land cover composition.
2. **Compute LST** and identify hotspots via UHI detection.
3. **Run predictions** to project future conditions under business-as-usual.
4. **Generate recommendations** with your actual or projected budget.
5. **Simulate top 2–3 scenarios** to compare cost-effectiveness.
6. **Export reports** for stakeholder communication.

### 15.3 Interpreting Model Outputs

- **Correlation ≠ causation:** High feature importance does not imply causal relationship.
- **Check confidence intervals:** Always consider the uncertainty range, not just the point estimate.
- **Ground-truth predictions:** Compare model predictions with field measurements before making large investments.
- **Re-evaluate annually:** Retrain models with new data each year to capture changing urban dynamics.

### 15.4 Stakeholder Communication

- Use the **Scenario Comparison** view to show "before vs. after" visuals to decision-makers.
- The **Cost per °C** metric is the most intuitive for budget discussions.
- Highlight **co-benefits** (air quality, stormwater, health) to justify cross-departmental funding.
- Use SHAP counterfactuals to explain *why* a specific area is a hotspot.

### 15.5 Integration with Planning Processes

- Incorporate UHMP outputs into **General Plans**, **Climate Action Plans**, and **Sustainability Master Plans**.
- Use hotspot maps to prioritize **Environmental Justice** communities disproportionately affected by heat.
- Align recommendations with **green infrastructure** and **complete streets** initiatives.
- Export GeoJSON layers directly into GIS workflows for zoning and permitting.

---

## 16. Troubleshooting Common User Issues

| # | Problem | Likely Cause | Solution |
|---|---|---|---|
| 1 | Upload fails with "Format not supported" | File is not a recognized format or is corrupted | Re-export as GeoTIFF from your GIS software |
| 2 | Preprocessing stuck at "Queued" | All Celery workers are busy | Wait for other tasks to complete, or ask admin to increase worker count |
| 3 | LST map shows no data (all black) | Cloud masking removed too many pixels | Reduce cloud confidence threshold and re-run |
| 4 | Spectral index values look incorrect | Scene was not atmospherically corrected | Re-run preprocessing with atmospheric correction enabled |
| 5 | UHI detection returns no hotspots | Threshold may be too strict for this area | Lower the threshold multiplier from 1.5 to 1.0 |
| 6 | Prediction confidence is very low | The model has not seen similar land cover in training | Collect and upload more training data for your region |
| 7 | Map tiles are not loading | Browser cache or network issue | Clear browser cache, check network connection, or try incognito mode |
| 8 | "Session expired" message | JWT token has timed out (default 24h) | Log out and log back in |
| 9 | Report generation fails | Large study area may exceed PDF memory limit | Reduce study area extent or increase granularity |
| 10 | Export download is very slow | Large raster file (GeoTIFF > 500 MB) | Use "Map Extent Only" filter or export as Cloud Optimized GeoTIFF |
| 11 | Charts are empty | No data for the selected date range | Expand the date range or upload more imagery |
| 12 | Drag-drop not working | Browser incompatibility | Use Chrome, Firefox, or Edge (latest versions) |
| 13 | "Insufficient storage" on upload | MinIO storage quota exceeded | Contact admin to increase storage or clean up old scenes |
| 14 | "Scene overlapping" warning | Uploaded scene bounds overlap existing data | Ignore if intended for time-series analysis, or delete duplicate scenes |
| 15 | Simulation results identical to baseline | Simulation parameters too conservative | Increase intensity parameters (coverage %, albedo change, etc.) |

---

## 17. Glossary of Terms

| Term | Definition |
|---|---|
| **Albedo** | Fraction of solar radiation reflected by a surface (0 = black, 1 = white). Higher albedo = cooler surface. |
| **Atmospheric Correction** | Removal of atmospheric scattering and absorption effects to recover true surface reflectance. |
| **Cloud Masking** | Identification and removal of pixels contaminated by clouds from satellite imagery. |
| **COG (Cloud Optimized GeoTIFF)** | A GeoTIFF file structured for efficient HTTP access without downloading the entire file. |
| **Counterfactual** | A minimal set of feature changes needed to alter a model's prediction. |
| **CRS** | Coordinate Reference System — defines how raster/vector coordinates map to positions on Earth. |
| **DOS (Dark Object Subtraction)** | A simple atmospheric correction method that subtracts the darkest pixel value. |
| **Emissivity** | Efficiency with which a surface emits thermal radiation (0–1). Critical for LST retrieval. |
| **Ensemble Model** | A machine learning model that combines multiple base models for improved accuracy. |
| **Fmask** | Function of mask — algorithm for cloud, shadow, and snow detection in Landsat imagery. |
| **GeoTIFF** | TIFF file with embedded georeferencing metadata for use in GIS. |
| **Hotspot** | A contiguous area of elevated LST significantly above the rural reference baseline. |
| **LST** | Land Surface Temperature — the radiative temperature of the Earth's surface. |
| **NDBI** | Normalized Difference Built-up Index — highlights urban/built-up areas. |
| **NDVI** | Normalized Difference Vegetation Index — measures vegetation health and density. |
| **NDWI** | Normalized Difference Water Index — highlights water bodies. |
| **PostGIS** | Spatial database extension for PostgreSQL that enables geographic queries. |
| **RCP** | Representative Concentration Pathway — climate change scenario (RCP 4.5 = moderate, RCP 8.5 = high emissions). |
| **Sen2Cor** | ESA's Sentinel-2 Level 2A processor for atmospheric correction. |
| **SHAP** | SHapley Additive exPlanations — game-theoretic approach for explaining model predictions. |
| **Single-Channel Algorithm** | LST retrieval method requiring one thermal band plus atmospheric parameters. |
| **Split-Window Algorithm** | LST retrieval method using two thermal bands to correct for atmospheric effects. |
| **UHI** | Urban Heat Island — urban areas that are significantly warmer than surrounding rural areas. |
| **6SV** | Second Simulation of a Satellite Signal in the Solar Spectrum — advanced atmospheric correction model. |

---

*© 2026 Urban Heat Mitigation Platform. All rights reserved.*
*For technical support, contact support@uhmp.example.com*
