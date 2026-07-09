import logging
from typing import Any

import numpy as np
import rasterio
from pathlib import Path

from .exceptions import ClassificationError

logger = logging.getLogger("app.indices.classification")


NDVI_THRESHOLDS: list[dict[str, Any]] = [
    {"class": "Water", "min": -1.0, "max": 0.0, "code": 1, "color": [0, 0, 255]},
    {"class": "Bare Soil", "min": 0.0, "max": 0.15, "code": 2, "color": [210, 180, 140]},
    {"class": "Sparse Vegetation", "min": 0.15, "max": 0.30, "code": 3, "color": [240, 230, 140]},
    {"class": "Moderate Vegetation", "min": 0.30, "max": 0.50, "code": 4, "color": [144, 238, 144]},
    {"class": "Dense Vegetation", "min": 0.50, "max": 1.0, "code": 5, "color": [34, 139, 34]},
]

NDBI_THRESHOLDS: list[dict[str, Any]] = [
    {"class": "Non-Built-Up", "min": -1.0, "max": 0.0, "code": 1, "color": [34, 139, 34]},
    {"class": "Low Density Built-Up", "min": 0.0, "max": 0.15, "code": 2, "color": [255, 165, 0]},
    {"class": "Medium Density Built-Up", "min": 0.15, "max": 0.30, "code": 3, "color": [255, 69, 0]},
    {"class": "High Density Built-Up", "min": 0.30, "max": 1.0, "code": 4, "color": [139, 0, 0]},
]

NDWI_THRESHOLDS: list[dict[str, Any]] = [
    {"class": "Non-Water", "min": -1.0, "max": 0.0, "code": 1, "color": [139, 90, 43]},
    {"class": "Low Water", "min": 0.0, "max": 0.2, "code": 2, "color": [135, 206, 250]},
    {"class": "Moderate Water", "min": 0.2, "max": 0.4, "code": 3, "color": [70, 130, 180]},
    {"class": "High Water", "min": 0.4, "max": 1.0, "code": 4, "color": [0, 0, 139]},
]

DEFAULT_SCHEMES: dict[str, list[dict[str, Any]]] = {
    "ndvi": NDVI_THRESHOLDS,
    "ndbi": NDBI_THRESHOLDS,
    "ndwi": NDWI_THRESHOLDS,
}


def get_scheme(index_name: str) -> list[dict[str, Any]]:
    key = index_name.lower()
    if key in DEFAULT_SCHEMES:
        return DEFAULT_SCHEMES[key]
    raise ClassificationError(f"No default classification scheme for '{index_name}'")


def classify(
    array: np.ndarray,
    thresholds: list[dict[str, Any]],
    nodata: float | None = None,
) -> np.ndarray:
    result = np.zeros(array.shape[-2:], dtype=np.uint8)
    valid_mask = np.ones(array.shape[-2:], dtype=bool)

    if nodata is not None:
        if np.isnan(nodata):
            valid_mask &= ~np.isnan(array) if array.ndim == 2 else ~np.isnan(array[0])
        else:
            if array.ndim == 2:
                valid_mask &= np.abs(array.astype(np.float64) - nodata) > 1e-8
            else:
                valid_mask &= np.abs(array[0].astype(np.float64) - nodata) > 1e-8
    if array.ndim == 2:
        valid_mask &= ~np.isnan(array) & ~np.isinf(array)
        source = array
    else:
        valid_mask &= ~np.isnan(array[0]) & ~np.isinf(array[0])
        source = array[0]

    for thresh in thresholds:
        mask = valid_mask & (source >= thresh["min"]) & (source < thresh["max"])
        result[mask] = thresh["code"]

    return result


def write_classification(
    classified: np.ndarray,
    path: str | Path,
    profile: dict,
    thresholds: list[dict[str, Any]],
) -> str:
    path = Path(path)
    out_profile = profile.copy()
    out_profile.update(
        dtype="uint8",
        count=1,
        compress="lzw",
        nodata=0,
    )
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(classified, 1)

    return str(path)


def classification_report(
    classified: np.ndarray,
    thresholds: list[dict[str, Any]],
) -> dict[str, Any]:
    total = classified.size
    report: dict[str, Any] = {"total_pixels": int(total)}
    class_pixels = {}
    for thresh in thresholds:
        count = int((classified == thresh["code"]).sum())
        pct = float(count) / float(total) * 100.0 if total > 0 else 0.0
        class_pixels[thresh["class"]] = {
            "code": thresh["code"],
            "pixel_count": count,
            "percentage": round(pct, 2),
            "color": thresh["color"],
        }
    report["classes"] = class_pixels
    return report
