import logging
import numpy as np

logger = logging.getLogger("app.features.quality")

CLOUD = 1 << 0
WATER = 1 << 1
SNOW = 1 << 2
LOW_EMISSIVITY = 1 << 3
MISSING_BAND = 1 << 4
INTERPOLATED = 1 << 5
HIGH_UNCERTAINTY = 1 << 6
URBAN_HOTSPOT = 1 << 7


def compute_quality_features(
    quality_mask: np.ndarray | None = None,
    uncertainty: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    result = {}
    if quality_mask is not None:
        cloud_pct = float(np.sum((quality_mask & CLOUD) > 0)) / quality_mask.size * 100.0
        result["cloud_pct"] = np.array([cloud_pct], dtype=np.float32)

        missing = int(np.sum((quality_mask & MISSING_BAND) > 0))
        missing_pct = missing / quality_mask.size * 100.0
        result["missing_pixel_pct"] = np.array([missing_pct], dtype=np.float32)

        result["quality_flags"] = quality_mask.astype(np.uint8)

    if uncertainty is not None:
        mean_uncert = float(np.nanmean(uncertainty))
        score = 100.0 - 15.0 * (mean_uncert / 2.0)
        score = max(0.0, min(100.0, score))
        result["confidence_score"] = np.full(uncertainty.shape, score, dtype=np.float32)

    return result


def dataset_quality_report(feature_cube: "GeoFeatureCube") -> dict:
    from .registry import list_feature_names
    total_pixels = feature_cube.n_pixels
    missing_values = {}
    for name in feature_cube.feature_names:
        arr = feature_cube.features[name]
        missing = int(np.sum(~np.isfinite(arr))) if np.issubdtype(arr.dtype, np.floating) else 0
        missing_values[name] = missing

    total_missing = sum(missing_values.values())
    completeness = 1.0 - (total_missing / (total_pixels * len(feature_cube.feature_names) + 1e-10))

    return {
        "total_pixels": total_pixels,
        "total_features": len(feature_cube.feature_names),
        "total_values": total_pixels * len(feature_cube.feature_names),
        "missing_values": total_missing,
        "completeness": round(completeness * 100, 2),
        "missing_by_feature": missing_values,
        "crs": feature_cube.crs,
    }
