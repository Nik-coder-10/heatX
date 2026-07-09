from .exceptions import (
    UHIError,
    DetectionError,
    MissingFeatureError,
    GeometryError,
    ClusteringError,
    SegmentationError,
    ConfigurationError,
)
from .configuration import UHIDetectionConfig
from .hotspot import Hotspot, UHIResult
from .registry import DETECTORS, DetectionMethodDef
from .detector import (
    detect_adaptive_threshold,
    detect_zscore,
    detect_percentile,
    detect_morans_i,
    detect_dbscan,
    detect_connected_components,
    detect_hybrid,
)
detect_hybrid_ensemble = detect_hybrid
from .segmentation import label_connected_components, mask_to_polygons
from .clustering import cluster_dbscan, merge_clusters_by_overlap, filter_small_clusters
from .morphology import apply_morphology
from .classification import classify_severity, classify_severity_map
from .severity import SEVERITY_COLORS, SEVERITY_RECOMMENDATIONS, SEVERITY_ORDER
from .spatial_analysis import compute_compactness, compute_elongation
from .quality import compute_confidence, compute_data_completeness
from .validator import validate_feature_cube, validate_hotspot
from .statistics import compute_uhi_statistics
from .metadata import build_uhi_metadata
from .visualization import render_hotspot_map, render_severity_heatmap, render_boundary_overlay
from .engine import UHIDetectionEngine, run_detection

__all__ = [
    "UHIError", "DetectionError", "MissingFeatureError", "GeometryError",
    "ClusteringError", "SegmentationError", "ConfigurationError",
    "UHIDetectionConfig",
    "Hotspot", "UHIResult",
    "DETECTORS", "DetectionMethodDef",
    "detect_adaptive_threshold", "detect_zscore", "detect_percentile",
    "detect_morans_i", "detect_dbscan", "detect_connected_components",
    "detect_hybrid_ensemble",
    "label_connected_components", "mask_to_polygons",
    "cluster_dbscan", "merge_clusters_by_overlap", "filter_small_clusters",
    "apply_morphology",
    "classify_severity", "classify_severity_map",
    "SEVERITY_COLORS", "SEVERITY_RECOMMENDATIONS", "SEVERITY_ORDER",
    "compute_compactness", "compute_elongation",
    "compute_confidence", "compute_data_completeness",
    "validate_feature_cube", "validate_hotspot",
    "compute_uhi_statistics",
    "build_uhi_metadata",
    "render_hotspot_map", "render_severity_heatmap", "render_boundary_overlay",
    "UHIDetectionEngine", "run_detection",
]
