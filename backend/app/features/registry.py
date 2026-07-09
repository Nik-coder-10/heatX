from dataclasses import dataclass, field
from typing import Any

from .exceptions import FeatureNotFoundError


FEATURE_REGISTRY: dict[str, "FeatureDefinition"] = {}


@dataclass
class FeatureDefinition:
    name: str
    category: str
    description: str
    data_type: str
    units: str
    dependencies: list[str]
    scientific_meaning: str
    expected_range: tuple[float, float]
    ml_importance_notes: str
    urban_heat_relevance: str
    limitations: str
    interpretation: str


def register(fd: FeatureDefinition) -> None:
    FEATURE_REGISTRY[fd.name.lower()] = fd


def get(name: str) -> FeatureDefinition:
    key = name.lower()
    if key not in FEATURE_REGISTRY:
        raise FeatureNotFoundError(
            f"Feature '{name}' not found. Available: {list(FEATURE_REGISTRY)}"
        )
    return FEATURE_REGISTRY[key]


def list_features(category: str | None = None) -> list[FeatureDefinition]:
    if category:
        return [f for f in FEATURE_REGISTRY.values() if f.category == category]
    return list(FEATURE_REGISTRY.values())


def list_categories() -> list[str]:
    return sorted({f.category for f in FEATURE_REGISTRY.values()})


def list_feature_names(category: str | None = None) -> list[str]:
    return [f.name for f in list_features(category)]


def get_dependent_features(feature_name: str) -> list[str]:
    fd = get(feature_name)
    return fd.dependencies


register(FeatureDefinition(
    name="lst_kelvin", category="thermal",
    description="Land Surface Temperature in Kelvin from Single-Channel or Split-Window algorithm",
    data_type="float32", units="K",
    dependencies=["thermal_radiance", "ndvi", "emissivity"],
    scientific_meaning="Thermodynamic temperature of the Earth's surface from thermal infrared remote sensing. Planck's law inversion with atmospheric correction.",
    expected_range=(250.0, 350.0),
    ml_importance_notes="Primary dependent variable for UHI prediction. High feature importance in urban heat models.",
    urban_heat_relevance="Direct measure of urban heat island intensity. Core variable for all UHI analyses.",
    limitations="Requires accurate atmospheric correction. Cloud contamination degrades quality.",
    interpretation="Higher values indicate warmer surfaces. Urban areas typically 2-10K warmer than rural.",
))

register(FeatureDefinition(
    name="lst_celsius", category="thermal",
    description="Land Surface Temperature in Celsius",
    data_type="float32", units="degC",
    dependencies=["lst_kelvin"],
    scientific_meaning="LST converted from Kelvin to Celsius (K - 273.15). More intuitive for stakeholder communication.",
    expected_range=(-23.0, 77.0),
    ml_importance_notes="Interpretable alternative to Kelvin. Same information content.",
    urban_heat_relevance="Used for reporting UHI magnitude in stakeholder-friendly units.",
    limitations="Same as lst_kelvin.",
    interpretation="0-50 C typical for most surfaces. Urban >40 C indicates extreme heat risk.",
))

register(FeatureDefinition(
    name="brightness_temperature", category="thermal",
    description="At-sensor brightness temperature from thermal band Planck inversion. No atmospheric correction.",
    data_type="float32", units="K",
    dependencies=["thermal_radiance"],
    scientific_meaning="Temperature of a blackbody emitting the same radiance as observed at sensor. T_b = K2 / ln(K1/L + 1).",
    expected_range=(250.0, 340.0),
    ml_importance_notes="Useful as raw input feature. Differences between BT and LST encode atmospheric information.",
    urban_heat_relevance="Raw thermal measurement. Urban-rural BT differences detectable even without atmospheric correction.",
    limitations="Systematically lower than LST due to atmospheric absorption. Not corrected for emissivity.",
    interpretation="Lower than LST by 1-5K depending on atmospheric conditions and surface emissivity.",
))

register(FeatureDefinition(
    name="emissivity", category="thermal",
    description="Surface emissivity from NDVI Threshold Method (Sobrino et al. 2004, 2008)",
    data_type="float32", units="dimensionless",
    dependencies=["ndvi"],
    scientific_meaning="Efficiency of surface in emitting thermal radiation relative to a blackbody. Ranges 0.95-0.99 for natural surfaces.",
    expected_range=(0.90, 1.00),
    ml_importance_notes="Essential correction factor for LST. Contains land cover information complementary to NDVI.",
    urban_heat_relevance="Urban materials (concrete, asphalt) have lower emissivity (0.92-0.96) than vegetation.",
    limitations="NDVI-based method assumes typical soil/vegetation mixtures. Unusual materials may have incorrect values.",
    interpretation="Water ~0.99, vegetation ~0.98-0.99, bare soil ~0.96-0.97, urban ~0.92-0.96.",
))

register(FeatureDefinition(
    name="thermal_gradient", category="thermal",
    description="Spatial gradient magnitude of LST via Sobel operator. Quantifies thermal edge intensity.",
    data_type="float32", units="K/pixel",
    dependencies=["lst_kelvin"],
    scientific_meaning="First derivative of LST field. High gradient indicates thermal discontinuities (park-urban interface, water-urban boundaries).",
    expected_range=(0.0, 10.0),
    ml_importance_notes="Edge detection feature. Captures urban-rural thermal boundaries and fragmentation.",
    urban_heat_relevance="Identifies urban-rural thermal boundaries. High near parks, water bodies, urban edges.",
    limitations="Sensitive to LST retrieval noise. Scale-dependent; 30m vs 100m resolution gives different gradients.",
    interpretation="0-1 K/pixel = homogeneous. >3 K/pixel = strong thermal boundary.",
))

register(FeatureDefinition(
    name="local_temp_variance", category="thermal",
    description="Local variance of LST within 3x3 window. Measures thermal heterogeneity.",
    data_type="float32", units="K^2",
    dependencies=["lst_kelvin"],
    scientific_meaning="Second moment of LST distribution in local neighborhood. High variance indicates mixed thermal surfaces.",
    expected_range=(0.0, 50.0),
    ml_importance_notes="Captures microclimate heterogeneity. Important for urban climate zone classification.",
    urban_heat_relevance="Low variance = uniform surfaces (water, dense urban). High variance = heterogeneous (suburban).",
    limitations="Window size affects interpretation. 3x3 optimal for 30m Landsat.",
    interpretation="<1 K^2 = homogeneous. >10 K^2 = highly heterogeneous.",
))

register(FeatureDefinition(
    name="hotspot_distance", category="thermal",
    description="Euclidean distance from each pixel to nearest urban heat hotspot (>90th percentile LST)",
    data_type="float32", units="meters",
    dependencies=["lst_kelvin"],
    scientific_meaning="Proximity to extreme urban heat. Inversely related to cooling accessibility. Proxy for urban heat exposure risk.",
    expected_range=(0.0, 5000.0),
    ml_importance_notes="Spatial risk feature. Non-linear relationship with heat-related health outcomes.",
    urban_heat_relevance="Core metric for urban heat exposure assessment. Short distances indicate high-risk areas.",
    limitations="Threshold-dependent (90th percentile). May not capture temporal variations in hotspots.",
    interpretation="0m = within hotspot. Larger distances = greater cooling access.",
))

register(FeatureDefinition(
    name="ndvi", category="vegetation",
    description="Normalized Difference Vegetation Index. (NIR - Red) / (NIR + Red).",
    data_type="float32", units="dimensionless",
    dependencies=["red", "nir"],
    scientific_meaning="Most widely used vegetation index. Correlated with chlorophyll activity, leaf area index, and vegetation fraction.",
    expected_range=(-0.5, 1.0),
    ml_importance_notes="Top predictor in urban heat models. Strong negative correlation with LST.",
    urban_heat_relevance="Inversely related to surface temperature. 0.1 NDVI increase ~ 1-2K LST decrease.",
    limitations="Saturates in high-density vegetation (LAI > 3). Affected by soil brightness.",
    interpretation="<0 = water/urban. 0-0.2 = bare soil. 0.2-0.5 = sparse vegetation. >0.5 = dense vegetation.",
))

register(FeatureDefinition(
    name="savi", category="vegetation",
    description="Soil-Adjusted Vegetation Index. Uses soil brightness correction factor L.",
    data_type="float32", units="dimensionless",
    dependencies=["red", "nir"],
    scientific_meaning="NDVI variant that minimizes soil background influence. Optimal for semi-arid urban areas.",
    expected_range=(-0.3, 0.9),
    ml_importance_notes="More accurate than NDVI in sparsely vegetated areas with exposed soil. Complements NDVI.",
    urban_heat_relevance="Better characterizes vegetation in urban settings where soil background varies.",
    limitations="Requires soil brightness parameter L (typically 0.5). Less validated than NDVI.",
    interpretation="Similar to NDVI but adjusted for soil. L=0.5 gives ~0.7x NDVI values.",
))

register(FeatureDefinition(
    name="evi", category="vegetation",
    description="Enhanced Vegetation Index. Incorporates blue band for atmospheric and canopy background correction.",
    data_type="float32", units="dimensionless",
    dependencies=["red", "nir", "blue"],
    scientific_meaning="Optimized for high-biomass regions with reduced atmospheric sensitivity and soil background.",
    expected_range=(-0.3, 1.0),
    ml_importance_notes="Superior to NDVI in dense urban vegetation. Less correlated with atmospheric conditions.",
    urban_heat_relevance="Better captures cooling effect of dense urban parks. Less saturation in urban forests.",
    limitations="Requires blue band (not on all sensors). More complex computation.",
    interpretation="Higher = more vegetation. 0.3-0.7 typical for urban parks.",
))

register(FeatureDefinition(
    name="msavi", category="vegetation",
    description="Modified Soil-Adjusted Vegetation Index. Self-adjusting soil brightness correction.",
    data_type="float32", units="dimensionless",
    dependencies=["red", "nir"],
    scientific_meaning="Improves on SAVI by replacing fixed L with self-adjusting soil brightness factor.",
    expected_range=(-0.3, 1.0),
    ml_importance_notes="Best vegetation index for partial cover urban environments. Adapts to varying soil conditions.",
    urban_heat_relevance="Ideal for heterogeneous urban landscapes with patchy vegetation.",
    limitations="Noisier than NDVI in very low or very high vegetation cover.",
    interpretation="Similar range to NDVI. More sensitive to intermediate vegetation cover.",
))

register(FeatureDefinition(
    name="gndvi", category="vegetation",
    description="Green Normalized Difference Vegetation Index. Uses green band instead of red.",
    data_type="float32", units="dimensionless",
    dependencies=["green", "nir"],
    scientific_meaning="Sensitive to chlorophyll concentration. Green band penetrates atmosphere better in some conditions.",
    expected_range=(-0.3, 0.9),
    ml_importance_notes="Captures different vegetation information than NDVI. Useful ensemble feature.",
    urban_heat_relevance="May better detect urban grass and managed vegetation than NDVI alone.",
    limitations="Green band availability varies by sensor. Less literature support for urban studies.",
    interpretation="Similar to NDVI. Higher values = healthier vegetation.",
))

register(FeatureDefinition(
    name="vegetation_fraction", category="vegetation",
    description="Fractional Vegetation Cover from NDVI using scaled NDVI method.",
    data_type="float32", units="fraction (0-1)",
    dependencies=["ndvi"],
    scientific_meaning="Proportion of pixel area covered by green vegetation. FVC = ((NDVI - NDVI_s) / (NDVI_v - NDVI_s))^2.",
    expected_range=(0.0, 1.0),
    ml_importance_notes="Linear relationship with biophysical processes. More interpretable than NDVI for planning.",
    urban_heat_relevance="Direct measure of vegetation cover. 10% FVC increase ~ 0.5-1K LST reduction.",
    limitations="Assumes two-endmember model (soil + vegetation). Urban impervious surfaces complicate interpretation.",
    interpretation="0 = no vegetation. 0.3-0.7 = moderate. >0.7 = dense. Urban parks often >0.7.",
))

register(FeatureDefinition(
    name="vegetation_density_class", category="vegetation",
    description="Discretized vegetation density: 0=bare, 1=sparse, 2=moderate, 3=dense, 4=very_dense.",
    data_type="int32", units="categorical (0-4)",
    dependencies=["vegetation_fraction"],
    scientific_meaning="Categorical simplification of continuous FVC for rule-based models and stakeholder communication.",
    expected_range=(0.0, 4.0),
    ml_importance_notes="Useful for categorical models and interpretable ML. Reduces noise from fractional cover.",
    urban_heat_relevance="Enables threshold-based urban vegetation planning. Cities target specific density classes.",
    limitations="Threshold boundaries are subjective. Information loss compared to continuous FVC.",
    interpretation="0=bare/impervious, 1=some grass, 2=scattered trees, 3=park, 4=dense forest.",
))

register(FeatureDefinition(
    name="distance_to_vegetation", category="vegetation",
    description="Euclidean distance to nearest vegetated pixel (FVC > 0.3).",
    data_type="float32", units="meters",
    dependencies=["vegetation_fraction"],
    scientific_meaning="Proximity to significant vegetation. Parks and green corridors provide cooling; distance captures access.",
    expected_range=(0.0, 2000.0),
    ml_importance_notes="Spatial context feature. Cooling effect of vegetation extends 50-500m beyond vegetation boundary.",
    urban_heat_relevance="Nearby vegetation reduces local temperatures through evapotranspiration and shading.",
    limitations="Does not consider vegetation quality or type. Euclidean ignores barriers.",
    interpretation="0m = vegetated. <100m = significant cooling. >500m = limited cooling.",
))

register(FeatureDefinition(
    name="ndbi", category="builtup",
    description="Normalized Difference Built-up Index. (SWIR1 - NIR) / (SWIR1 + NIR).",
    data_type="float32", units="dimensionless",
    dependencies=["nir", "swir1"],
    scientific_meaning="Exploits higher SWIR reflectance of built-up surfaces compared to vegetation.",
    expected_range=(-0.5, 0.5),
    ml_importance_notes="Primary built-up indicator. Positive relationship with LST. Strong urban-rural discriminator.",
    urban_heat_relevance="Directly identifies urban surfaces. High NDBI areas correlate with high LST and UHI.",
    limitations="Confuses bare soil with built-up in arid regions. May miss some urban features.",
    interpretation="<0 = vegetation/water. >0.1 = built-up. >0.2 = dense urban.",
))

register(FeatureDefinition(
    name="ibi", category="builtup",
    description="Index-based Built-up Index. IBI = (NDBI - (SAVI+MNDWI)/2) / (NDBI + (SAVI+MNDWI)/2).",
    data_type="float32", units="dimensionless",
    dependencies=["ndbi", "savi", "mndwi"],
    scientific_meaning="Synthesizes three indices to isolate built-up while suppressing vegetation and water.",
    expected_range=(-0.8, 0.8),
    ml_importance_notes="More accurate built-up detection than NDBI alone. Reduced bare soil confusion.",
    urban_heat_relevance="Best spectral index for urban extent mapping. Reduces false positives from bare soil.",
    limitations="Requires three indices as input. May fail with unusual spectral mixtures.",
    interpretation=">0 = built-up. Higher = more intense urbanization.",
))

register(FeatureDefinition(
    name="urban_index", category="builtup",
    description="Urban Index. (SWIR2 - NIR) / (SWIR2 + NIR). Differentiates urban from soil.",
    data_type="float32", units="dimensionless",
    dependencies=["nir", "swir2"],
    scientific_meaning="Similar to NDBI using SWIR2 band. Supplementary built-up indicator.",
    expected_range=(-0.5, 0.5),
    ml_importance_notes="Additional built-up feature. May provide complementary information to NDBI.",
    urban_heat_relevance="Supplementary built-up indicator for urban heat studies.",
    limitations="SWIR2 not available on all sensors. Correlated with NDBI.",
    interpretation="Similar to NDBI. Positive = built-up surfaces.",
))

register(FeatureDefinition(
    name="impervious_surface_pct", category="builtup",
    description="Estimated impervious surface percentage from NDBI and urban index thresholds.",
    data_type="float32", units="percentage (0-100)",
    dependencies=["ndbi", "urban_index"],
    scientific_meaning="Fraction of pixel covered by impervious materials (concrete, asphalt, roofs). Key urbanization metric.",
    expected_range=(0.0, 100.0),
    ml_importance_notes="Continuous measure of urbanization intensity. Strongly correlated with LST.",
    urban_heat_relevance="Direct driver of UHI. Each 10% increase in impervious ~ 0.5-1.5K LST increase.",
    limitations="Estimate based on spectral indices. Validation requires ground truth.",
    interpretation="0-20% = pervious. 20-50% = suburban. 50-80% = urban. 80-100% = dense core.",
))

register(FeatureDefinition(
    name="building_density", category="builtup",
    description="Estimated building density from built-up index. Fraction of pixel covered by structures.",
    data_type="float32", units="fraction (0-1)",
    dependencies=["ndbi"],
    scientific_meaning="Subset of impervious surface related to structures. Derived from NDBI magnitude.",
    expected_range=(0.0, 1.0),
    ml_importance_notes="More specific than impervious surface. Different building densities have different thermal impacts.",
    urban_heat_relevance="High building density areas trap heat through canyon effects and reduced ventilation.",
    limitations="Cannot distinguish building types. Vertical dimension not captured.",
    interpretation="0 = no buildings. 0.1-0.3 = low density. >0.6 = high density.",
))

register(FeatureDefinition(
    name="builtup_ratio", category="builtup",
    description="Ratio of built-up to vegetated area in local neighborhood.",
    data_type="float32", units="fraction (0-1)",
    dependencies=["ndbi", "ndvi"],
    scientific_meaning="Local land cover composition metric. High = dominance of built-up surfaces.",
    expected_range=(0.0, 1.0),
    ml_importance_notes="Captures neighborhood-scale urbanization. Important for context-dependent UHI modeling.",
    urban_heat_relevance="Neighborhood composition is a key predictor of local microclimate.",
    limitations="Requires local window aggregation. Window size affects interpretation.",
    interpretation="0 = fully vegetated. >0.7 = urban-dominated. >0.9 = dense urban.",
))

register(FeatureDefinition(
    name="road_density", category="builtup",
    description="Road density proxy from built-up index. Future-ready for OpenStreetMap integration.",
    data_type="float32", units="km/km^2",
    dependencies=["ndbi"],
    scientific_meaning="Estimated road network density. Roads are significant contributors to urban heat.",
    expected_range=(0.0, 20.0),
    ml_importance_notes="Roads contribute to UHI through heat-absorbing asphalt. Important for heat exposure.",
    urban_heat_relevance="Asphalt roads can reach 60-70 C in summer. Major contributor to urban heat exposure.",
    limitations="Spectral estimate only. Real road density requires vector data.",
    interpretation="0-5 = low. 5-10 = moderate. 10-15 = high. >15 = very high.",
))

register(FeatureDefinition(
    name="ndwi", category="water",
    description="Normalized Difference Water Index. (Green - NIR) / (Green + NIR).",
    data_type="float32", units="dimensionless",
    dependencies=["green", "nir"],
    scientific_meaning="Exploits high green reflectance and low NIR reflectance of water. Positive = water.",
    expected_range=(-0.5, 0.5),
    ml_importance_notes="Primary water detection feature. Water surfaces show strong cooling on surrounding areas.",
    urban_heat_relevance="Water cool islands provide significant cooling. Water creates 1-5K local cooling.",
    limitations="Confuses shadows and dark surfaces with water. Turbid water may have lower NDWI.",
    interpretation="<0 = land. 0-0.2 = wet soil. >0.2 = open water.",
))

register(FeatureDefinition(
    name="mndwi", category="water",
    description="Modified NDWI. (Green - SWIR1) / (Green + SWIR1). Better for built-up areas.",
    data_type="float32", units="dimensionless",
    dependencies=["green", "swir1"],
    scientific_meaning="Improves on NDWI by using SWIR1 instead of NIR. Reduces confusion with built-up.",
    expected_range=(-0.5, 0.5),
    ml_importance_notes="Superior water detection in urban environments. Less confusion with shadows.",
    urban_heat_relevance="Better delineates urban water bodies (canals, fountains) that provide cooling.",
    limitations="Requires SWIR1 band. May miss very narrow water features.",
    interpretation="<0 = built-up/vegetation. >0.3 = water.",
))

register(FeatureDefinition(
    name="distance_to_water", category="water",
    description="Euclidean distance to nearest water pixel (MNDWI > 0.3).",
    data_type="float32", units="meters",
    dependencies=["mndwi"],
    scientific_meaning="Proximity to surface water bodies. Water provides cooling through evaporation and advection.",
    expected_range=(0.0, 5000.0),
    ml_importance_notes="Non-linear cooling effect. Cooling extends 50-500m from water depending on size.",
    urban_heat_relevance="Water proximity reduces LST by 1-5K. Urban planning uses water-access cooling zones.",
    limitations="Does not account for water body size. Cooling depends on wind direction and geometry.",
    interpretation="0m = water. <100m = significant cooling. 100-500m = moderate. >500m = limited.",
))

register(FeatureDefinition(
    name="water_density", category="water",
    description="Fractional coverage of water in local neighborhood.",
    data_type="float32", units="fraction (0-1)",
    dependencies=["mndwi"],
    scientific_meaning="Areal proportion of water surface within a local window.",
    expected_range=(0.0, 1.0),
    ml_importance_notes="Contextual feature. Even small water fractions affect local microclimate.",
    urban_heat_relevance="Water fraction is a strong predictor of neighborhood-scale cooling.",
    limitations="Window size affects interpretation. 300-500m recommended.",
    interpretation="0 = no water. >0.2 = significant water influence.",
))

register(FeatureDefinition(
    name="moisture_index", category="water",
    description="Normalized Difference Moisture Index (NDMI). (NIR - SWIR1) / (NIR + SWIR1).",
    data_type="float32", units="dimensionless",
    dependencies=["nir", "swir1"],
    scientific_meaning="Related to water content in vegetation and surface soil. Used for drought and ET estimation.",
    expected_range=(-0.5, 0.8),
    ml_importance_notes="Provides moisture context for urban thermal behavior. Wet surfaces show different thermal response.",
    urban_heat_relevance="Irrigated urban vegetation has different thermal inertia than dry surfaces.",
    limitations="Affected by atmospheric water vapor. Not direct soil moisture without calibration.",
    interpretation="<0 = dry. 0-0.2 = low moisture. 0.2-0.5 = moderate. >0.5 = high moisture.",
))

register(FeatureDefinition(
    name="bsi", category="baresoil",
    description="Bare Soil Index. ((SWIR1+Red) - (NIR+Blue)) / ((SWIR1+Red) + (NIR+Blue)).",
    data_type="float32", units="dimensionless",
    dependencies=["red", "nir", "blue", "swir1"],
    scientific_meaning="Designed to isolate bare soil by exploiting high SWIR and Red reflectance relative to NIR and Blue.",
    expected_range=(-0.5, 0.5),
    ml_importance_notes="Important for identifying exposed soil. Construction sites and vacant lots have high BSI.",
    urban_heat_relevance="Bare soil in urban areas contributes to urban heat. Construction sites are local heat sources.",
    limitations="Requires 4 bands. Confuses with built-up in some contexts.",
    interpretation="<0 = vegetation/water. >0.1 = bare soil. Construction sites show high positive values.",
))

register(FeatureDefinition(
    name="bare_soil_pct", category="baresoil",
    description="Estimated bare soil percentage from BSI thresholding.",
    data_type="float32", units="percentage (0-100)",
    dependencies=["bsi"],
    scientific_meaning="Fraction of pixel with exposed soil. Important for urban dust, heat, and hydrology.",
    expected_range=(0.0, 100.0),
    ml_importance_notes="Continuous soil exposure metric. Construction increases bare soil and local heating.",
    urban_heat_relevance="Bare soil heats rapidly compared to vegetated surfaces. Contributes to daytime UHI.",
    limitations="Estimate only. Temporal variation high in agricultural/construction areas.",
    interpretation="0-10% = minimal. >30% = significant. Construction sites >50%.",
))

register(FeatureDefinition(
    name="exposed_surface_pct", category="baresoil",
    description="Combined exposed surface (bare soil + impervious). Total unvegetated fraction.",
    data_type="float32", units="percentage (0-100)",
    dependencies=["bare_soil_pct", "impervious_surface_pct"],
    scientific_meaning="Total fraction of pixel not covered by vegetation or water. Comprehensive urbanization measure.",
    expected_range=(0.0, 100.0),
    ml_importance_notes="Single comprehensive urbanization metric. High correlation with LST across all land covers.",
    urban_heat_relevance="Most directly correlated simple feature with LST in urban areas. Core UHI predictor.",
    limitations="Combines distinct surface types. Loses specificity.",
    interpretation="0-30% = natural. 30-60% = suburban. 60-85% = urban. >85% = dense urban.",
))

register(FeatureDefinition(
    name="latitude", category="spatial",
    description="Latitude of pixel centroid in WGS84 decimal degrees.",
    data_type="float64", units="decimal degrees",
    dependencies=["transform", "geometry"],
    scientific_meaning="Geographic coordinate. Accounts for latitudinal climate gradients in temperature prediction.",
    expected_range=(-90.0, 90.0),
    ml_importance_notes="Captures large-scale climate gradients. Important for global models, less for city-scale.",
    urban_heat_relevance="Solar radiation varies with latitude, affecting absolute LST values.",
    limitations="Low spatial variance within a single city.",
    interpretation="Negative = Southern Hemisphere. Positive = Northern Hemisphere.",
))

register(FeatureDefinition(
    name="longitude", category="spatial",
    description="Longitude of pixel centroid in WGS84 decimal degrees.",
    data_type="float64", units="decimal degrees",
    dependencies=["transform", "geometry"],
    scientific_meaning="Geographic coordinate for continental/regional climate effects.",
    expected_range=(-180.0, 180.0),
    ml_importance_notes="Captures continental/regional climate effects. Coastal vs inland differences.",
    urban_heat_relevance="Coastal cities have different UHI patterns than inland cities.",
    limitations="Low spatial variance within single city.",
    interpretation="Negative = Western Hemisphere. Positive = Eastern Hemisphere.",
))

register(FeatureDefinition(
    name="pixel_area", category="spatial",
    description="Pixel area in square meters. Accounts for sensor resolution and projection distortions.",
    data_type="float64", units="m^2",
    dependencies=["transform", "resolution"],
    scientific_meaning="Actual ground area covered by each pixel. Varies with latitude in geographic projections.",
    expected_range=(0.0, 1000000.0),
    ml_importance_notes="Useful for area-based aggregation. Ensures comparability across sensors.",
    urban_heat_relevance="Different sensor resolutions capture different urban scales.",
    limitations="Constant for equal-area projections. Varies in geographic projections.",
    interpretation="Landsat: 900 m^2. Sentinel: 100 m^2. MODIS: 1,000,000 m^2.",
))

register(FeatureDefinition(
    name="elevation", category="terrain",
    description="Surface elevation above sea level from DEM (plugin-based).",
    data_type="float32", units="meters",
    dependencies=["dem"],
    scientific_meaning="Height above sea level. Temperature decreases with elevation (lapse rate ~6.5K/km).",
    expected_range=(-500.0, 9000.0),
    ml_importance_notes="Strong temperature predictor in topographically diverse urban areas.",
    urban_heat_relevance="Cities at higher elevations are cooler. UHI magnitude varies with elevation.",
    limitations="Requires DEM input. Static over time.",
    interpretation="Each 100m increase ~ 0.65K temperature decrease.",
))

register(FeatureDefinition(
    name="slope", category="terrain",
    description="Terrain slope angle in degrees derived from DEM.",
    data_type="float32", units="degrees",
    dependencies=["elevation"],
    scientific_meaning="Steepness of terrain. Affects solar radiation receipt and surface runoff.",
    expected_range=(0.0, 90.0),
    ml_importance_notes="Affects solar exposure and surface heating. South-facing slopes warmer in NH.",
    urban_heat_relevance="Steep slopes receive different solar radiation. Aspect-slope interactions affect microclimate.",
    limitations="Derived from DEM resolution. Coarse DEMs miss fine-scale features.",
    interpretation="0-2 = flat. 2-10 = gentle. 10-25 = moderate. >25 = steep.",
))

register(FeatureDefinition(
    name="aspect", category="terrain",
    description="Terrain aspect (compass direction). 0=N, 90=E, 180=S, 270=W.",
    data_type="float32", units="degrees",
    dependencies=["elevation"],
    scientific_meaning="Direction of maximum terrain slope. Determines solar exposure timing and intensity.",
    expected_range=(0.0, 360.0),
    ml_importance_notes="Circular feature. South-facing slopes (NH) receive more solar radiation.",
    urban_heat_relevance="Aspect affects building energy demand and outdoor thermal comfort.",
    limitations="Circular encoding needed (sin/cos). Flat areas have undefined aspect.",
    interpretation="N-facing = cooler/shaded. S-facing = warmer/sunny.",
))

register(FeatureDefinition(
    name="day_of_year", category="temporal",
    description="Day of year (1-366) of satellite acquisition. Captures seasonal solar cycle.",
    data_type="int32", units="day (1-366)",
    dependencies=["acquisition_date"],
    scientific_meaning="Annual solar cycle phase. Drives seasonal temperature variations through insolation.",
    expected_range=(1.0, 366.0),
    ml_importance_notes="Critical for seasonal adjustment of LST. Enables multi-temporal models.",
    urban_heat_relevance="UHI intensity varies seasonally. Summer UHI 2-5K, winter UHI 0-2K.",
    limitations="Cyclic feature needs encoding (sin/cos). Single-date only without time series.",
    interpretation="1-90=winter(NH). 91-181=spring. 182-273=summer. 274-366=autumn.",
))

register(FeatureDefinition(
    name="month", category="temporal",
    description="Month of acquisition (1-12). Coarser temporal resolution than day_of_year.",
    data_type="int32", units="month (1-12)",
    dependencies=["acquisition_date"],
    scientific_meaning="Monthly seasonal indicator. Lower temporal resolution reduces noise.",
    expected_range=(1.0, 12.0),
    ml_importance_notes="Useful for monthly or seasonal models. Less noise than day_of_year.",
    urban_heat_relevance="Captures seasonal UHI patterns. Summer months show strongest UHI.",
    limitations="Coarse temporal granularity. May miss intra-month variations.",
    interpretation="Month number. June-August = summer (NH).",
))

register(FeatureDefinition(
    name="season", category="temporal",
    description="Season of acquisition. Winter=0, Spring=1, Summer=2, Autumn=3.",
    data_type="int32", units="categorical (0-3)",
    dependencies=["month"],
    scientific_meaning="Seasonal classification for categorical analysis. Standard meteorological seasons.",
    expected_range=(0.0, 3.0),
    ml_importance_notes="Categorical seasonal control. Enables season-aware models.",
    urban_heat_relevance="UHI magnitude varies by season. Summer UHI most impactful for health.",
    limitations="Static seasonal boundaries. Tropical regions have wet/dry seasons.",
    interpretation="0=Winter, 1=Spring, 2=Summer, 3=Autumn (NH).",
))

register(FeatureDefinition(
    name="acquisition_time", category="temporal",
    description="Local solar time of satellite acquisition in hours. Landsat ~10:00, Sentinel ~10:30.",
    data_type="float32", units="hours (0-24)",
    dependencies=["acquisition_metadata"],
    scientific_meaning="Time of day of satellite overpass. LST varies diurnally, time normalization is critical.",
    expected_range=(0.0, 24.0),
    ml_importance_notes="Essential for combining acquisitions at different times. Diurnal LST curve varies by surface.",
    urban_heat_relevance="Morning overpasses show developing UHI. Afternoon overpasses show peak UHI.",
    limitations="Fixed overpass time for polar-orbiting satellites.",
    interpretation="10:00 = Landsat AM. 10:30 = Sentinel-2. Earlier = cooler.",
))

register(FeatureDefinition(
    name="years_since_baseline", category="temporal",
    description="Years since reference baseline date. Enables trend analysis.",
    data_type="float32", units="years",
    dependencies=["acquisition_date"],
    scientific_meaning="Temporal offset from reference. Enables detection of long-term LST trends and urbanization effects.",
    expected_range=(0.0, 50.0),
    ml_importance_notes="Key feature for time-series models. Enables trend detection and change analysis.",
    urban_heat_relevance="Urban heat trends over time. Enables detection of UHI intensification.",
    limitations="Requires defined baseline. Comparison across different periods requires caution.",
    interpretation="0 = baseline year. Positive = more recent.",
))

register(FeatureDefinition(
    name="cloud_pct", category="quality",
    description="Percentage of image area covered by clouds. Affects data usability.",
    data_type="float32", units="percentage (0-100)",
    dependencies=["cloud_mask"],
    scientific_meaning="Fractional cloud cover. Valid LST requires cloud-free conditions.",
    expected_range=(0.0, 100.0),
    ml_importance_notes="Data quality flag. High cloud scenes should be flagged for downstream models.",
    urban_heat_relevance="Cloud-free scenes critical for valid LST. Urban signals partially obscured by clouds.",
    limitations="Scene-level metric. Cloud shadow and thin cirrus may not be detected.",
    interpretation="0 = clear. <20 = mostly clear. 20-50 = partly cloudy. >50 = poor.",
))

register(FeatureDefinition(
    name="confidence_score", category="quality",
    description="Per-pixel confidence score (0-100) based on cloud, uncertainty, and data completeness.",
    data_type="float32", units="score (0-100)",
    dependencies=["quality_mask", "uncertainty"],
    scientific_meaning="Integrated quality indicator combining cloud, retrieval uncertainty, and data gaps.",
    expected_range=(0.0, 100.0),
    ml_importance_notes="Sample weight for ML models. Low confidence pixels should be down-weighted.",
    urban_heat_relevance="Ensures only reliable LST values used for urban heat analysis.",
    limitations="Weighting scheme may not capture all error sources.",
    interpretation="0-25=poor. 25-50=marginal. 50-75=good. 75-100=excellent.",
))

register(FeatureDefinition(
    name="missing_pixel_pct", category="quality",
    description="Percentage of pixels with missing or invalid values.",
    data_type="float32", units="percentage (0-100)",
    dependencies=["quality_mask"],
    scientific_meaning="Data completeness metric. High missing = processing or acquisition issues.",
    expected_range=(0.0, 100.0),
    ml_importance_notes="Dataset-level quality metric. High missing may require imputation or exclusion.",
    urban_heat_relevance="Ensures sufficient valid data for urban analysis.",
    limitations="Missing data may be non-random.",
    interpretation="<5 = good. 5-15 = acceptable. >15 = poor.",
))

register(FeatureDefinition(
    name="quality_flags", category="quality",
    description="Bitfield quality flags: cloud, water, snow, low_emissivity, missing, interpolated, high_uncertainty, hotspot.",
    data_type="uint8", units="bitfield",
    dependencies=["quality_mask"],
    scientific_meaning="Per-pixel quality flags from LST retrieval. Each bit indicates a specific issue.",
    expected_range=(0.0, 255.0),
    ml_importance_notes="Detailed quality information for filtering. Each flag enables selective exclusion.",
    urban_heat_relevance="Urban hotspot flag directly identifies potential UHI pixels.",
    limitations="Flags may be over-conservative. Trade-off between sensitivity and specificity.",
    interpretation="Bit 0=cloud, 1=water, 2=snow, 3=low_emissivity, 4=missing, 5=interpolated, 6=high_uncertainty, 7=hotspot.",
))

register(FeatureDefinition(
    name="sensor", category="quality",
    description="Satellite sensor: Landsat-8, Landsat-9, Sentinel-2, etc.",
    data_type="string", units="categorical",
    dependencies=["metadata"],
    scientific_meaning="Source sensor identification. Different sensors have different spectral/spatial/temporal characteristics.",
    expected_range=(0.0, 1.0),
    ml_importance_notes="Categorical feature for sensor harmonization. Enables cross-sensor models.",
    urban_heat_relevance="Sensor resolution affects UHI detail capture. Landsat 30m vs MODIS 1km.",
    limitations="Encoding needed for ML. One-hot or label encoding appropriate.",
    interpretation="Landsat-8: 30m TIR. Landsat-9: 30m TIR. Sentinel-2: 10-20m VNIR.",
))

register(FeatureDefinition(
    name="resolution", category="quality",
    description="Spatial resolution of source data in meters.",
    data_type="float32", units="meters",
    dependencies=["metadata"],
    scientific_meaning="Ground sampling distance. Finer resolution captures more urban detail but increases noise.",
    expected_range=(0.0, 1000.0),
    ml_importance_notes="Resolution normalization needed for cross-sensor models. Coarser = more mixed pixels.",
    urban_heat_relevance="30m suitable for urban block analysis. 1km sufficient for city-scale UHI.",
    limitations="Fixed per sensor. Resolution mismatch between bands (e.g., Landsat 30m VIS, 100m TIR).",
    interpretation="10m=Sentinel MSI. 30m=Landsat OLI/TIRS. 100m=Landsat TIR. 1km=MODIS.",
))
