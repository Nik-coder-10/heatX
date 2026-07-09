from dataclasses import dataclass, field
from .exceptions import InvalidMethodError


DETECTION_REGISTRY: dict[str, "DetectionMethodDef"] = {}
DETECTORS: dict[str, dict] = {}


@dataclass
class DetectionMethodDef:
    name: str
    description: str
    scientific_basis: str
    expected_inputs: list[str]
    limitations: list[str]
    computational_complexity: str
    urban_climate_applicability: str
    expected_accuracy: str = ""
    typical_failure_cases: list[str] = field(default_factory=list)


def register(method: DetectionMethodDef) -> None:
    DETECTION_REGISTRY[method.name.lower()] = method


def get(name: str) -> DetectionMethodDef:
    key = name.lower()
    if key not in DETECTION_REGISTRY:
        raise InvalidMethodError(
            f"Detection method '{name}' not found. "
            f"Available: {list(DETECTION_REGISTRY)}"
        )
    return DETECTION_REGISTRY[key]


def list_methods() -> list[DetectionMethodDef]:
    return list(DETECTION_REGISTRY.values())


register(DetectionMethodDef(
    name="adaptive_threshold",
    description="Adaptive LST Threshold using Otsu's method or local mean+k*std",
    scientific_basis="Otsu (1979) thresholding for bimodal distributions; "
                     "adaptive local threshold for heterogeneous urban landscapes. "
                     "LST distributions in urban areas are often bimodal (urban vs rural).",
    expected_inputs=["lst_celsius", "rural_mask"],
    limitations=["Requires sufficient urban-rural contrast",
                 "Otsu fails on unimodal distributions",
                 "Local window size affects results"],
    computational_complexity="O(n) for global; O(n*w) for local",
    urban_climate_applicability="Primary method for UHI detection. Works when urban-rural LST difference is clear.",
    expected_accuracy="+/- 1-3K threshold accuracy",
    typical_failure_cases=["Cloudy scenes", "Homogeneous land cover", "Water-dominated scenes"],
))

register(DetectionMethodDef(
    name="zscore",
    description="Local Z-score detection. Pixels with Z > threshold relative to local neighborhood mean/std.",
    scientific_basis="Standardized anomaly detection. Z = (LST_pixel - LST_local_mean) / LST_local_std. "
                     "Captures local thermal anomalies regardless of absolute temperature.",
    expected_inputs=["lst_celsius"],
    limitations=["Requires appropriate neighborhood size",
                 "Edge effects at image boundaries",
                 "May miss large, uniformly hot areas"],
    computational_complexity="O(n*w) for local statistics",
    urban_climate_applicability="Detects thermal anomalies relative to local context. Good for heterogeneous cities.",
    expected_accuracy="Identifies local hotspots 2+ std from mean",
    typical_failure_cases=["Uniformly hot scenes", "Small neighborhoods near cool features"],
))

register(DetectionMethodDef(
    name="percentile",
    description="Global percentile threshold. Pixels above configurable percentile (default 90th) detected as hotspots.",
    scientific_basis="Fixed percentile thresholding based on cumulative LST distribution. "
                     "Assumes hottest N% of scene are UHI pixels.",
    expected_inputs=["lst_celsius"],
    limitations=["Fixed percentage regardless of actual UHI extent",
                 "No spatial context consideration",
                 "Threshold varies with scene composition"],
    computational_complexity="O(n log n) for sorting",
    urban_climate_applicability="Simple baseline method. Useful for inter-city comparisons with fixed percentile.",
    expected_accuracy="+/- 5-10% area accuracy depending on scene",
    typical_failure_cases=["Scenes with unusual LST distributions", "Cloud-contaminated scenes"],
))

register(DetectionMethodDef(
    name="morans_i",
    description="Local Moran's I spatial autocorrelation. Identifies high-high clusters as UHI hotspots.",
    scientific_basis="Anselin (1995) Local Indicators of Spatial Association (LISA). "
                     "Detects statistically significant spatial clusters of high LST values. "
                     "Architecture-ready for PySAL integration.",
    expected_inputs=["lst_celsius", "weights_matrix"],
    limitations=["Computationally expensive for large rasters",
                 "Requires spatial weights matrix",
                 "PySAL dependency for full implementation"],
    computational_complexity="O(n^2) naive; O(n log n) optimized",
    urban_climate_applicability="Scientifically rigorous UHI delineation. Identifies statistically significant clusters.",
    expected_accuracy="Statistical significance-based (p < 0.05)",
    typical_failure_cases="Large datasets without optimization, edge effects",
))

register(DetectionMethodDef(
    name="dbscan",
    description="DBSCAN spatial clustering of high-LST pixels. Identifies arbitrary-shaped UHI clusters.",
    scientific_basis="Ester et al. (1996) Density-Based Spatial Clustering of Applications with Noise. "
                     "Groups nearby high-LST pixels into clusters without specifying cluster count.",
    expected_inputs=["lst_celsius", "coordinates"],
    limitations=["Sensitive to eps and min_samples parameters",
                 "Border points may be assigned inconsistently",
                 "Memory-heavy for large rasters"],
    computational_complexity="O(n log n) with spatial indexing",
    urban_climate_applicability="Identifies naturally shaped UHI clusters without geometric assumptions.",
    expected_accuracy="Depends on eps/min_samples tuning",
    typical_failure_cases="Varying density hotspots, very large scenes without sampling",
))

register(DetectionMethodDef(
    name="connected_components",
    description="Connected component analysis on binary threshold mask. Labels contiguous hotspot regions.",
    scientific_basis="Rosenfeld & Pfaltz (1966) connected component labeling. "
                     "Standard computer vision approach for identifying contiguous regions.",
    expected_inputs=["binary_mask"],
    limitations=["Requires prior thresholding",
                 "8-connectivity vs 4-connectivity affects results",
                 "No density consideration"],
    computational_complexity="O(n)",
    urban_climate_applicability="Post-processing for any threshold method. Produces labeled hotspot polygons.",
    expected_accuracy="Determined by input mask quality",
    typical_failure_cases="Threshold-dependent; disconnected hotspots",
))

register(DetectionMethodDef(
    name="hybrid",
    description="Hybrid Ensemble Detector. Weighted combination of multiple detection methods.",
    scientific_basis="Ensemble theory (Dietterich 2000). Combining multiple detectors reduces individual method biases "
                     "and improves robustness across diverse urban landscapes.",
    expected_inputs=["lst_celsius", "ndvi", "ndbi", "ndwi"],
    limitations=["Increased computational cost",
                 "Weight tuning required per region",
                 "Method dependency requires all sub-methods available"],
    computational_complexity="Sum of sub-method complexities",
    urban_climate_applicability="Most robust approach. Recommended for production UHI detection.",
    expected_accuracy="Best among methods when weights are tuned",
    typical_failure_cases="Overly conservative with equal weights",
))

# Build DETECTORS dict for dispatch
from . import detector as _detector

DETECTORS = {
    "adaptive_threshold": {
        "name": "Adaptive Threshold",
        "description": "Otsu/local adaptive LST thresholding",
        "function": _detector.detect_adaptive_threshold,
    },
    "zscore": {
        "name": "Local Z-Score",
        "description": "Local thermal anomaly via z-score",
        "function": _detector.detect_zscore,
    },
    "percentile": {
        "name": "Percentile Threshold",
        "description": "Global percentile-based LST threshold",
        "function": _detector.detect_percentile,
    },
    "morans_i": {
        "name": "Moran's I",
        "description": "Local spatial autocorrelation hotspot detection",
        "function": _detector.detect_morans_i,
    },
    "dbscan": {
        "name": "DBSCAN",
        "description": "Density-based clustering of high-LST pixels",
        "function": _detector.detect_dbscan,
    },
    "connected_components": {
        "name": "Connected Components",
        "description": "Connected component labeling on threshold mask",
        "function": _detector.detect_connected_components,
    },
    "hybrid": {
        "name": "Hybrid Ensemble",
        "description": "Weighted ensemble of multiple detection methods",
        "function": _detector.detect_hybrid,
    },
}
