from dataclasses import dataclass, field
from typing import Callable

from .exceptions import IndexNotFoundError


@dataclass
class IndexDefinition:
    name: str
    formula: str
    description: str
    interpretation: str
    urban_heat_relevance: str
    limitations: str
    common_misuse: str
    required_bands: list[str]
    optional_bands: list[str] = field(default_factory=list)
    value_range: tuple[float, float] = (-1.0, 1.0)
    typical_range: tuple[float, float] = (-0.5, 0.8)
    unit: str = "dimensionless"
    reference: str = ""
    tags: list[str] = field(default_factory=list)


INDEX_REGISTRY: dict[str, IndexDefinition] = {}


def register(index_def: IndexDefinition) -> None:
    INDEX_REGISTRY[index_def.name.lower()] = index_def


def get_index(name: str) -> IndexDefinition:
    key = name.lower()
    if key not in INDEX_REGISTRY:
        raise IndexNotFoundError(
            f"Index '{name}' not found. "
            f"Available: {', '.join(sorted(INDEX_REGISTRY))}"
        )
    return INDEX_REGISTRY[key]


def list_indices(tag: str | None = None) -> list[IndexDefinition]:
    if tag is None:
        return list(INDEX_REGISTRY.values())
    return [idx for idx in INDEX_REGISTRY.values() if tag in idx.tags]


def list_index_names(tag: str | None = None) -> list[str]:
    return [idx.name for idx in list_indices(tag)]


# ----- Vegetation Indices -----

register(IndexDefinition(
    name="NDVI",
    formula="(NIR - Red) / (NIR + Red)",
    description="Normalized Difference Vegetation Index. Quantifies vegetation greenness "
                "by measuring the difference between near-infrared and red reflectance.",
    interpretation="Values > 0.2 indicate vegetation. Dense vegetation > 0.5. "
                   "Sparse vegetation 0.1-0.2. Non-vegetated surfaces < 0.1.",
    urban_heat_relevance="Vegetation density directly correlates with cooling potential. "
                         "NDVI is the primary input for emissivity estimation in LST retrieval.",
    limitations="Saturates in dense vegetation. Affected by soil brightness in sparse canopies. "
                "Atmospheric effects can bias results.",
    common_misuse="Applying to non-atmospherically corrected data. "
                  "Comparing NDVI across different sensors without normalization.",
    required_bands=["nir", "red"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.2, 0.9),
    tags=["vegetation", "core", "lst_input"],
))

register(IndexDefinition(
    name="SAVI",
    formula="((NIR - Red) / (NIR + Red + L)) * (1 + L)",
    description="Soil-Adjusted Vegetation Index. Minimizes soil brightness influence "
                "by incorporating a soil adjustment factor L.",
    interpretation="L=0.5 for moderate vegetation. L=1 for sparse vegetation. "
                   "L=0 for dense (equivalent to NDVI). Similar interpretation to NDVI.",
    urban_heat_relevance="Better than NDVI in urban areas where soil background varies. "
                         "More accurate vegetation fraction estimation in heterogeneous landscapes.",
    limitations="Requires knowledge of soil conditions for optimal L factor. "
                "L factor choice affects comparability.",
    common_misuse="Using default L=0.5 without justification. "
                  "Comparing SAVI values with different L factors.",
    required_bands=["nir", "red"],
    optional_bands=["L"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.3, 0.8),
    tags=["vegetation", "soil_adjusted"],
))

register(IndexDefinition(
    name="EVI",
    formula="2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)",
    description="Enhanced Vegetation Index. Optimizes vegetation signal with improved "
                "sensitivity in high biomass regions and reduced atmospheric influences.",
    interpretation="Similar range to NDVI but more linear with LAI. "
                   "Less saturated in dense vegetation. Requires blue band for atmospheric correction.",
    urban_heat_relevance="More sensitive to urban vegetation gradients. "
                         "Better separation of vegetation types in park/forest areas.",
    limitations="Requires blue band. More complex processing. "
                "Coefficients optimized for MODIS; may need adjustment for other sensors.",
    common_misuse="Using without proper atmospheric correction. "
                  "Applying MODIS coefficients to very high resolution data without validation.",
    required_bands=["nir", "red", "blue"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.2, 0.8),
    tags=["vegetation", "enhanced", "atmospheric_corrected"],
))

register(IndexDefinition(
    name="MSAVI",
    formula="(2*NIR + 1 - sqrt((2*NIR + 1)^2 - 8*(NIR - Red))) / 2",
    description="Modified Soil-Adjusted Vegetation Index. Dynamically adjusts "
                "the soil brightness factor without requiring a predefined L value.",
    interpretation="Designed to reduce soil noise more effectively than SAVI. "
                   "Self-adjusting L factor based on vegetation density.",
    urban_heat_relevance="Useful in urban-agricultural interface zones. "
                         "Handles varying soil conditions across urban landscapes better than SAVI.",
    limitations="Noisier at very low vegetation cover. "
                "Imaginary results possible under certain conditions (clipped to zero).",
    common_misuse="Assuming identical behavior to SAVI under all conditions. "
                  "Using with non-normalized reflectance data.",
    required_bands=["nir", "red"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.2, 0.8),
    tags=["vegetation", "soil_adjusted", "modified"],
))

# ----- Built-up Indices -----

register(IndexDefinition(
    name="NDBI",
    formula="(SWIR1 - NIR) / (SWIR1 + NIR)",
    description="Normalized Difference Built-up Index. Highlights urban areas by "
                "exploiting higher SWIR reflectance of built surfaces relative to NIR.",
    interpretation="Positive values indicate built-up areas. "
                   "Urban areas typically 0.1-0.3. Vegetation negative. Water negative.",
    urban_heat_relevance="Directly identifies impervious surfaces which are primary "
                         "drivers of urban heat island intensity.",
    limitations="Confusion with bare soil. Mixed pixels in urban-fringe areas. "
                "Resolution-dependent performance.",
    common_misuse="Using as sole urban classifier without threshold calibration. "
                  "Applying globally without local validation.",
    required_bands=["swir1", "nir"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.5, 0.5),
    tags=["built_up", "urban", "impervious"],
))

register(IndexDefinition(
    name="IBI",
    formula="(NDBI - (SAVI + NDWI)/2) / (NDBI + (SAVI + NDWI)/2)",
    description="Index-Based Built-up Index. Combines NDBI, SAVI, and NDWI to "
                "enhance built-up area discrimination while suppressing vegetation and water.",
    interpretation="Positive values indicate built-up. "
                   "More selective than NDBI alone. Reduces bare soil confusion.",
    urban_heat_relevance="More accurate urban extent mapping. "
                         "Better separation of built-up from bare soil in urban peripheries.",
    limitations="Requires three indices computed first (computationally heavier). "
                "Propagates errors from each constituent index.",
    common_misuse="Using inappropriate NDWI formulation (should use McFeeters). "
                  "Not validating intermediate indices.",
    required_bands=["nir", "red", "swir1", "green"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.5, 0.5),
    tags=["built_up", "urban", "composite"],
))

register(IndexDefinition(
    name="UI",
    formula="(SWIR2 - NIR) / (SWIR2 + NIR)",
    description="Urban Index. Uses the longer SWIR2 band to better discriminate "
                "urban surfaces from bare soil compared to NDBI.",
    interpretation="Urban areas show positive values. "
                   "Less soil confusion than NDBI. Typical urban > 0.",
    urban_heat_relevance="Better built-up detection in semi-arid regions where "
                         "bare soil and built-up have similar SWIR1 signatures.",
    limitations="Requires SWIR2 band (not all sensors have it). "
                "Still some confusion with dry bare soil.",
    common_misuse="Assuming identical to NDBI interpretation. "
                  "Using in humid regions where SWIR2 performance may differ.",
    required_bands=["swir2", "nir"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.4, 0.4),
    tags=["built_up", "urban", "swir2"],
))

# ----- Water Indices -----

register(IndexDefinition(
    name="NDWI",
    formula="(Green - NIR) / (Green + NIR)",
    description="Normalized Difference Water Index (McFeeters 1996). "
                "Highlights open water by maximizing green reflectance and minimizing NIR.",
    interpretation="Positive values indicate water. Values > 0.2 typically open water. "
                   "Negative values indicate vegetation or bare soil.",
    urban_heat_relevance="Identifies water bodies that act as cooling sinks. "
                         "Essential for evaporative cooling analysis in urban climate studies.",
    limitations="Not suitable for turbid water or shallow water with submerged vegetation. "
                "May confuse shadow with water in urban canyons.",
    common_misuse="Using the Gao NDWI (with NIR, SWIR) formulation for open water detection. "
                  "Applying to shadow-rich urban scenes without shadow masking.",
    required_bands=["green", "nir"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.5, 0.8),
    tags=["water", "surface_water"],
))

register(IndexDefinition(
    name="MNDWI",
    formula="(Green - SWIR1) / (Green + SWIR1)",
    description="Modified Normalized Difference Water Index (Xu 2006). "
                "Replaces NIR with SWIR1 for better water detection in urban environments.",
    interpretation="More accurate than NDWI in urban areas because built-up surfaces "
                   "have higher NIR than SWIR reflectance. Positive = water.",
    urban_heat_relevance="Superior water detection in urban scenes. "
                         "Reduces false positives from built-up surfaces compared to NDWI.",
    limitations="Still affected by shadow in very dense urban areas. "
                "Requires SWIR1 band.",
    common_misuse="Using same thresholds as NDWI. "
                  "Not accounting for different water types (clear vs turbid).",
    required_bands=["green", "swir1"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.5, 0.8),
    tags=["water", "urban_water", "modified"],
))

# ----- Moisture Indices -----

register(IndexDefinition(
    name="NDMI",
    formula="(NIR - SWIR1) / (NIR + SWIR1)",
    description="Normalized Difference Moisture Index. Sensitive to vegetation water "
                "content using the NIR and SWIR1 reflectance difference.",
    interpretation="Higher values indicate higher vegetation water content. "
                   "Used for drought monitoring and fire risk assessment.",
    urban_heat_relevance="Vegetation moisture status affects latent heat flux. "
                         "Dry vegetation reduces evaporative cooling efficiency.",
    limitations="Affected by soil moisture in sparse canopies. "
                "Less sensitive in senescent vegetation.",
    common_misuse="Confusing with NDWI (different physics: moisture vs open water). "
                  "Applying without atmospheric correction.",
    required_bands=["nir", "swir1"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.5, 0.7),
    tags=["moisture", "vegetation_water", "drought"],
))

# ----- Bare Soil Indices -----

register(IndexDefinition(
    name="BSI",
    formula="((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))",
    description="Bare Soil Index. Identifies bare soil areas by combining SWIR, "
                "red, NIR, and blue reflectance characteristics.",
    interpretation="Positive values indicate bare soil. "
                   "Urban areas typically negative or near-zero. Vegetation negative.",
    urban_heat_relevance="Distinguishes bare soil from built-up for UHI source analysis. "
                         "Bare soil and built-up have different thermal properties.",
    limitations="Confusion with sparsely vegetated areas. "
                "Sensitive to soil moisture and color variations.",
    common_misuse="Using as standalone urban classifier. "
                  "Not accounting for soil type differences.",
    required_bands=["swir1", "red", "nir", "blue"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.5, 0.6),
    tags=["bare_soil", "soil", "exposed_surface"],
))

# ----- Thermal Helper -----

register(IndexDefinition(
    name="NDISI",
    formula="(TIR - (NIR + SWIR1 + SWIR2)/3) / (TIR + (NIR + SWIR1 + SWIR2)/3)",
    description="Normalized Difference Impervious Surface Index. Highlights "
                "impervious surfaces using thermal infrared and VNIR-SWIR bands.",
    interpretation="Positive values indicate impervious surfaces. "
                   "Water and vegetation show negative values.",
    urban_heat_relevance="Directly relates to surface temperature via TIR band. "
                         "Used for impervious surface fraction estimation in UHI analysis.",
    limitations="Requires thermal band (not always available). "
                "Lower spatial resolution typical of thermal bands.",
    common_misuse="Using with different band combinations across sensors without normalization. "
                  "Assuming linear relationship with impervious fraction.",
    required_bands=["tir", "nir", "swir1", "swir2"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.3, 0.6),
    tags=["thermal", "impervious", "urban"],
))

# ----- Additional vegetation -----

register(IndexDefinition(
    name="GNDVI",
    formula="(NIR - Green) / (NIR + Green)",
    description="Green Normalized Difference Vegetation Index. Uses green band "
                "instead of red for more sensitive chlorophyll estimation.",
    interpretation="Similar to NDVI but more sensitive to chlorophyll. "
                   "Often used for crop health and nitrogen status.",
    urban_heat_relevance="May better capture stress in urban vegetation "
                         "where chlorophyll degradation signals heat stress.",
    limitations="Less established than NDVI for general vegetation mapping. "
                "More sensitive to atmospheric scattering.",
    common_misuse="Applying NDVI-derived thresholds directly. "
                  "Not accounting for green band differences between sensors.",
    required_bands=["nir", "green"],
    value_range=(-1.0, 1.0),
    typical_range=(-0.2, 0.8),
    tags=["vegetation", "chlorophyll", "stress"],
))
